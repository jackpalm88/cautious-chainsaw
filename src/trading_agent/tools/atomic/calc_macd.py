"""
CalcMACD - Atomic Tool
Calculates MACD (Moving Average Convergence Divergence) with confidence
"""

import time
from typing import Any

import numpy as np

from ..base_tool import BaseTool, ConfidenceCalculator, ConfidenceComponents, ToolResult, ToolTier


class CalcMACD(BaseTool):
    """
    Calculate MACD (Moving Average Convergence Divergence) indicator.

    MACD = EMA(12) - EMA(26)
    Signal Line = EMA(9) of MACD
    Histogram = MACD - Signal Line

    Interpretation:
    - MACD > Signal: Bullish
    - MACD < Signal: Bearish
    - Histogram increasing: Strengthening trend
    """

    name = "calc_macd"
    version = "1.0.0"
    tier = ToolTier.ATOMIC
    description = "Calculate MACD indicator with signal line and histogram"

    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """
        Initialize MACD calculator.

        Args:
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line EMA period (default: 9)
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    def execute(self, prices: list[float], **kwargs) -> ToolResult:
        """
        Calculate MACD for given price series.

        Args:
            prices: List of closing prices (oldest to newest)
            **kwargs: Additional parameters

        Returns:
            ToolResult with MACD values and confidence
        """
        start_time = time.perf_counter()

        try:
            # Validate inputs
            self.validate_inputs(prices=prices)

            # Calculate MACD
            macd, signal, histogram = self._calculate_macd(prices)

            # Calculate confidence
            confidence_components = self._calculate_confidence(prices)
            confidence = confidence_components.calculate_confidence()

            # Determine signal
            trading_signal = self._interpret_macd(macd, signal, histogram)

            # Calculate latency
            latency_ms = (time.perf_counter() - start_time) * 1000

            return ToolResult(
                value={
                    'macd': round(macd, 5),
                    'signal': round(signal, 5),
                    'histogram': round(histogram, 5),
                    'trading_signal': trading_signal,
                },
                confidence=confidence,
                latency_ms=round(latency_ms, 2),
                metadata={
                    'confidence_components': confidence_components.to_dict(),
                    'samples_used': len(prices),
                    'required_samples': self.slow_period + self.signal_period,
                },
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                value=None, confidence=0.0, latency_ms=round(latency_ms, 2), error=str(e)
            )

    def validate_inputs(self, prices: list[float]) -> None:
        """Validate input parameters"""
        required_samples = self.slow_period + self.signal_period

        if not prices:
            raise ValueError("Prices list cannot be empty")

        if len(prices) < required_samples:
            raise ValueError(
                f"Insufficient data: need {required_samples} prices, got {len(prices)}"
            )

        if any(p <= 0 for p in prices):
            raise ValueError("All prices must be positive")

    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """
        Calculate Exponential Moving Average.

        Args:
            prices: Price array
            period: EMA period

        Returns:
            Current EMA value
        """
        multiplier = 2 / (period + 1)
        ema = prices[0]  # Start with first price

        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema

        return ema

    def _calculate_macd(self, prices: list[float]) -> tuple[float, float, float]:
        """
        Calculate MACD, signal line, and histogram.

        Args:
            prices: Price series

        Returns:
            Tuple of (macd, signal, histogram)
        """
        prices_array = np.array(prices)

        # Calculate fast and slow EMAs
        fast_ema = self._calculate_ema(prices_array, self.fast_period)
        slow_ema = self._calculate_ema(prices_array, self.slow_period)

        # MACD line
        macd = fast_ema - slow_ema

        # For signal line, we need MACD history
        # Simplified: calculate MACD for each point and then EMA
        macd_history = []
        for i in range(self.slow_period, len(prices_array) + 1):
            subset = prices_array[:i]
            f_ema = self._calculate_ema(subset, self.fast_period)
            s_ema = self._calculate_ema(subset, self.slow_period)
            macd_history.append(f_ema - s_ema)

        # Signal line (EMA of MACD)
        if len(macd_history) >= self.signal_period:
            macd_array = np.array(macd_history[-self.signal_period :])
            signal = self._calculate_ema(macd_array, self.signal_period)
        else:
            signal = macd  # Not enough data for signal

        # Histogram
        histogram = macd - signal

        return macd, signal, histogram

    def _calculate_confidence(self, prices: list[float]) -> ConfidenceComponents:
        """Calculate multi-factor confidence"""
        # Sample sufficiency
        required_samples = self.slow_period + self.signal_period
        actual_samples = len(prices)
        sample_sufficiency = ConfidenceCalculator.sample_sufficiency(
            actual_samples, required_samples
        )

        # Volatility regime
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns) * np.sqrt(252)
        volatility_regime = ConfidenceCalculator.volatility_regime(volatility)

        # Data quality
        gaps = 0
        flat_periods = sum(1 for i in range(1, len(prices)) if prices[i] == prices[i - 1])
        data_quality = ConfidenceCalculator.data_quality(gaps, flat_periods, len(prices))

        # Indicator agreement (single indicator)
        indicator_agreement = 0.8

        return ConfidenceComponents(
            sample_sufficiency=sample_sufficiency,
            volatility_regime=volatility_regime,
            indicator_agreement=indicator_agreement,
            data_quality=data_quality,
        )

    def _interpret_macd(self, macd: float, signal: float, histogram: float) -> str:
        """
        Interpret MACD as trading signal.

        Args:
            macd: MACD value
            signal: Signal line value
            histogram: Histogram value

        Returns:
            Signal: 'bullish', 'bearish', or 'neutral'
        """
        if macd > signal and histogram > 0:
            return 'bullish'
        elif macd < signal and histogram < 0:
            return 'bearish'
        else:
            return 'neutral'

    def get_schema(self) -> dict[str, Any]:
        """Get JSON-Schema for LLM function calling"""
        required_samples = self.slow_period + self.signal_period
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "prices": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": f"List of closing prices (minimum {required_samples} values)",
                    },
                },
                "required": ["prices"],
            },
        }
