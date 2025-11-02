"""Utilities for loading and preparing historical data."""

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest_engine import BacktestBar


class MT5DataLoader:
    """
    Load and preprocess MT5 historical data for backtesting.

    Usage:
        loader = MT5DataLoader()
        bars = loader.load_csv("EURUSD_M5_2023.csv", symbol="EURUSD", timeframe="M5")
        cleaned_bars = loader.clean_data(bars)
    """

    def __init__(self, default_spread_pips: float = 1.5):
        """
        Initialize loader.

        Args:
            default_spread_pips: Default spread to use if not in data
        """
        self.default_spread_pips = default_spread_pips

    def load_csv(
        self,
        filepath: str,
        symbol: str,
        timeframe: str,
        date_format: str = "%Y.%m.%d",
        time_format: str = "%H:%M"
    ) -> list[BacktestBar]:
        """
        Load MT5 CSV export file.

        Args:
            filepath: Path to CSV file
            symbol: Trading symbol (e.g., "EURUSD")
            timeframe: Timeframe (e.g., "M5", "H1", "D1")
            date_format: Date parsing format
            time_format: Time parsing format

        Returns:
            List of BacktestBar objects
        """
        if not Path(filepath).exists():
            raise FileNotFoundError(f"CSV file not found: {filepath}")

        # Read CSV
        df = pd.read_csv(filepath)

        # Validate columns
        required_cols = ["Date", "Time", "Open", "High", "Low", "Close", "Volume"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

        # Parse timestamps
        df["Timestamp"] = pd.to_datetime(
            df["Date"] + " " + df["Time"],
            format=f"{date_format} {time_format}"
        )

        # Estimate spread if not provided
        if "Spread" not in df.columns:
            df["Spread"] = self.default_spread_pips

        # Convert to BacktestBar objects
        bars = []
        for _, row in df.iterrows():
            bar = BacktestBar(
                timestamp=row["Timestamp"],
                symbol=symbol,
                timeframe=timeframe,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row["Volume"]),
                spread=float(row.get("Spread", self.default_spread_pips))
            )
            bars.append(bar)

        print(f"✅ Loaded {len(bars)} bars from {filepath}")
        return bars

    def clean_data(
        self,
        bars: list[BacktestBar],
        remove_gaps: bool = True,
        remove_outliers: bool = True,
        max_gap_hours: int = 24
    ) -> list[BacktestBar]:
        """
        Clean and validate historical data.

        Args:
            bars: Raw bars from CSV
            remove_gaps: Remove large time gaps (weekends, holidays)
            remove_outliers: Remove price spikes (likely errors)
            max_gap_hours: Maximum acceptable gap between bars

        Returns:
            Cleaned bars
        """
        if not bars:
            return []

        cleaned = []
        prev_bar = None

        for bar in bars:
            # Validate OHLC relationships
            if not self._validate_ohlc(bar):
                print(f"⚠️  Skipping invalid bar: {bar.timestamp}")
                continue

            # Check for large gaps
            if prev_bar and remove_gaps:
                gap = bar.timestamp - prev_bar.timestamp
                if gap > timedelta(hours=max_gap_hours):
                    print(f"⚠️  Large gap detected: {gap} at {bar.timestamp}")
                    # Keep bar but flag it

            # Check for outliers
            if prev_bar and remove_outliers:
                price_change = abs(bar.close - prev_bar.close) / prev_bar.close
                if price_change > 0.05:  # 5% move
                    print(f"⚠️  Outlier detected: {price_change*100:.1f}% move at {bar.timestamp}")
                    # Optionally skip or adjust

            cleaned.append(bar)
            prev_bar = bar

        removed = len(bars) - len(cleaned)
        if removed > 0:
            print(f"🧹 Cleaned data: {removed} bars removed, {len(cleaned)} remaining")

        return cleaned

    def _validate_ohlc(self, bar: BacktestBar) -> bool:
        """Validate OHLC relationships."""
        if bar.high < bar.low:
            return False
        if bar.high < bar.open or bar.high < bar.close:
            return False
        if bar.low > bar.open or bar.low > bar.close:
            return False
        if bar.open <= 0 or bar.close <= 0:
            return False
        return True

    def resample_timeframe(
        self,
        bars: list[BacktestBar],
        target_timeframe: str
    ) -> list[BacktestBar]:
        """
        Resample bars to a different timeframe.

        Args:
            bars: Source bars
            target_timeframe: Target timeframe (e.g., "H1", "H4", "D1")

        Returns:
            Resampled bars
        """
        if not bars:
            return []

        # Convert to pandas for easy resampling
        df = pd.DataFrame([
            {
                "timestamp": b.timestamp,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
                "spread": b.spread
            }
            for b in bars
        ])

        df.set_index("timestamp", inplace=True)

        # Map timeframe to pandas frequency
        freq_map = {
            "M5": "5T",
            "M15": "15T",
            "M30": "30T",
            "H1": "1H",
            "H4": "4H",
            "D1": "1D"
        }

        freq = freq_map.get(target_timeframe)
        if not freq:
            raise ValueError(f"Unsupported timeframe: {target_timeframe}")

        # Resample
        resampled = df.resample(freq).agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
            "spread": "mean"
        }).dropna()

        # Convert back to BacktestBar
        resampled_bars = []
        for timestamp, row in resampled.iterrows():
            bar = BacktestBar(
                timestamp=timestamp,
                symbol=bars[0].symbol,
                timeframe=target_timeframe,
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
                spread=row["spread"]
            )
            resampled_bars.append(bar)

        print(f"🔄 Resampled {len(bars)} bars to {len(resampled_bars)} {target_timeframe} bars")
        return resampled_bars

    def split_train_test(
        self,
        bars: list[BacktestBar],
        train_ratio: float = 0.7
    ) -> tuple[list[BacktestBar], list[BacktestBar]]:
        """
        Split data into training and testing sets.

        Args:
            bars: All bars
            train_ratio: Fraction of data for training (0.7 = 70%)

        Returns:
            (train_bars, test_bars)
        """
        split_idx = int(len(bars) * train_ratio)
        train_bars = bars[:split_idx]
        test_bars = bars[split_idx:]

        print(f"📊 Train: {len(train_bars)} bars | Test: {len(test_bars)} bars")
        return train_bars, test_bars

    def generate_mock_data(
        self,
        symbol: str = "EURUSD",
        timeframe: str = "M5",
        num_bars: int = 10000,
        initial_price: float = 1.0950,
        volatility: float = 0.0002,
        trend: float = 0.00001
    ) -> list[BacktestBar]:
        """
        Generate realistic mock data using Geometric Brownian Motion.

        Useful for testing strategies without downloading real data.

        Args:
            symbol: Symbol name
            timeframe: Timeframe
            num_bars: Number of bars to generate
            initial_price: Starting price
            volatility: Price volatility (sigma)
            trend: Drift parameter (mu)

        Returns:
            Generated bars
        """
        np.random.seed(42)  # Reproducible

        # Generate price path using GBM
        prices = [initial_price]

        for _ in range(num_bars - 1):
            price = prices[-1]
            shock = np.random.normal(trend, volatility)
            new_price = price * (1 + shock)
            prices.append(new_price)

        # Generate OHLC bars
        bars = []
        start_time = datetime(2023, 1, 1)

        for i in range(num_bars):
            timestamp = start_time + timedelta(minutes=5 * i)

            # Create realistic OHLC
            close_price = prices[i]
            noise = volatility * np.random.randn()

            open_price = close_price * (1 + noise * 0.5)
            high_price = max(open_price, close_price) * (1 + abs(noise))
            low_price = min(open_price, close_price) * (1 - abs(noise))

            bar = BacktestBar(
                timestamp=timestamp,
                symbol=symbol,
                timeframe=timeframe,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=np.random.randint(50, 200),
                spread=np.random.uniform(0.8, 2.0)
            )
            bars.append(bar)

        print(f"🎲 Generated {len(bars)} mock bars for {symbol}")
        return bars

    def export_to_csv(
        self,
        bars: list[BacktestBar],
        filepath: str
    ) -> None:
        """Export bars to CSV format."""
        df = pd.DataFrame([
            {
                "Date": b.timestamp.strftime("%Y.%m.%d"),
                "Time": b.timestamp.strftime("%H:%M"),
                "Open": b.open,
                "High": b.high,
                "Low": b.low,
                "Close": b.close,
                "Volume": b.volume,
                "Spread": b.spread
            }
            for b in bars
        ])

        df.to_csv(filepath, index=False)
        print(f"💾 Exported {len(bars)} bars to {filepath}")


# Convenience functions
def load_mt5_csv(filepath: str, symbol: str, timeframe: str) -> list[BacktestBar]:
    """Quick load MT5 CSV file."""
    loader = MT5DataLoader()
    bars = loader.load_csv(filepath, symbol, timeframe)
    return loader.clean_data(bars)


def generate_test_data(num_bars: int = 10000) -> list[BacktestBar]:
    """Quick generate test data."""
    loader = MT5DataLoader()
    return loader.generate_mock_data(num_bars=num_bars)
