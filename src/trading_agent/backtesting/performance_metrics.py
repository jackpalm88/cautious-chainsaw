"""
Performance Metrics Calculator for Backtest Results

Calculates:
1. Return metrics (total return, CAGR, volatility)
2. Risk-adjusted returns (Sharpe, Sortino, Calmar)
3. Drawdown analysis (max DD, recovery time)
4. Trade statistics (win rate, profit factor, expectancy)
5. Benchmarking (vs buy-and-hold)
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from .backtest_engine import BacktestTrade


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics."""

    # Return metrics
    total_return_pct: float
    cagr: float  # Compound Annual Growth Rate
    daily_return_mean: float
    daily_return_std: float

    # Risk-adjusted returns
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float

    # Drawdown metrics
    max_drawdown_pct: float
    max_drawdown_duration_days: int
    recovery_factor: float  # Total return / Max DD

    # Trade statistics
    total_trades: int
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    expectancy: float  # Expected profit per trade

    # Consistency metrics
    win_streak_max: int
    loss_streak_max: int
    monthly_win_rate: float

    # Additional stats
    total_fees: float
    trades_per_day: float


class PerformanceCalculator:
    """Calculate comprehensive performance metrics from backtest results."""

    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize calculator.

        Args:
            risk_free_rate: Annual risk-free rate for Sharpe calculation (default 2%)
        """
        self.risk_free_rate = risk_free_rate

    def calculate(
        self,
        trades: List[BacktestTrade],
        equity_curve: List[Dict[str, Any]],
        initial_capital: float
    ) -> PerformanceMetrics:
        """
        Calculate all performance metrics.

        Args:
            trades: List of completed trades
            equity_curve: Equity history from backtest
            initial_capital: Starting capital

        Returns:
            PerformanceMetrics object with all statistics
        """
        if not trades:
            raise ValueError("No trades to analyze")

        # Extract data
        equity_series = pd.Series([e["total_equity"] for e in equity_curve])
        timestamps = pd.Series([e["timestamp"] for e in equity_curve])

        # Calculate returns
        returns = equity_series.pct_change().dropna()

        # Final capital
        final_capital = equity_series.iloc[-1]
        total_return = (final_capital - initial_capital) / initial_capital

        # CAGR
        days = (timestamps.iloc[-1] - timestamps.iloc[0]).days
        years = days / 365.25
        cagr = (final_capital / initial_capital) ** (1 / years) - 1 if years > 0 else 0

        # Daily statistics
        daily_return_mean = returns.mean()
        daily_return_std = returns.std()

        # Risk-adjusted returns
        sharpe = self._calculate_sharpe(returns, daily_return_std)
        sortino = self._calculate_sortino(returns)

        # Drawdown analysis
        max_dd, max_dd_duration = self._calculate_drawdown(equity_series, timestamps)
        calmar = cagr / abs(max_dd) if max_dd != 0 else 0
        recovery_factor = total_return / abs(max_dd) if max_dd != 0 else 0

        # Trade statistics
        winners = [t for t in trades if t.pnl > 0]
        losers = [t for t in trades if t.pnl <= 0]

        win_rate = len(winners) / len(trades) if trades else 0

        total_wins = sum(t.pnl for t in winners)
        total_losses = sum(abs(t.pnl) for t in losers)
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        avg_win = np.mean([t.pnl for t in winners]) if winners else 0
        avg_loss = np.mean([t.pnl for t in losers]) if losers else 0

        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

        # Streaks
        win_streak, loss_streak = self._calculate_streaks(trades)

        # Monthly consistency
        monthly_win_rate = self._calculate_monthly_win_rate(trades)

        # Fees
        total_fees = sum(t.commission for t in trades)

        # Trade frequency
        trades_per_day = len(trades) / days if days > 0 else 0

        return PerformanceMetrics(
            total_return_pct=total_return * 100,
            cagr=cagr * 100,
            daily_return_mean=daily_return_mean * 100,
            daily_return_std=daily_return_std * 100,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown_pct=max_dd * 100,
            max_drawdown_duration_days=max_dd_duration,
            recovery_factor=recovery_factor,
            total_trades=len(trades),
            win_rate=win_rate * 100,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            expectancy=expectancy,
            win_streak_max=win_streak,
            loss_streak_max=loss_streak,
            monthly_win_rate=monthly_win_rate * 100,
            total_fees=total_fees,
            trades_per_day=trades_per_day
        )

    def _calculate_sharpe(self, returns: pd.Series, std: float) -> float:
        """Calculate Sharpe ratio."""
        if std == 0:
            return 0

        # Annualize
        daily_rf = (1 + self.risk_free_rate) ** (1/252) - 1
        excess_return = returns.mean() - daily_rf

        sharpe = (excess_return / std) * np.sqrt(252) if std > 0 else 0
        return sharpe

    def _calculate_sortino(self, returns: pd.Series) -> float:
        """Calculate Sortino ratio (penalizes only downside volatility)."""
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0:
            return float('inf')

        downside_std = downside_returns.std()
        if downside_std == 0:
            return 0

        daily_rf = (1 + self.risk_free_rate) ** (1/252) - 1
        excess_return = returns.mean() - daily_rf

        sortino = (excess_return / downside_std) * np.sqrt(252)
        return sortino

    def _calculate_drawdown(
        self,
        equity_series: pd.Series,
        timestamps: pd.Series
    ) -> tuple[float, int]:
        """Calculate maximum drawdown and duration."""
        running_max = equity_series.expanding().max()
        drawdowns = (equity_series - running_max) / running_max

        max_dd = drawdowns.min()

        # Find duration
        dd_duration_days = 0
        in_drawdown = False
        dd_start = None

        for i, dd in enumerate(drawdowns):
            if dd < -0.01 and not in_drawdown:  # Start of drawdown
                in_drawdown = True
                dd_start = timestamps.iloc[i]
            elif dd >= -0.001 and in_drawdown:  # Recovery
                if dd_start:
                    duration = (timestamps.iloc[i] - dd_start).days
                    dd_duration_days = max(dd_duration_days, duration)
                in_drawdown = False

        return max_dd, dd_duration_days

    def _calculate_streaks(self, trades: List[BacktestTrade]) -> tuple[int, int]:
        """Calculate maximum winning/losing streaks."""
        win_streak = 0
        loss_streak = 0
        current_win_streak = 0
        current_loss_streak = 0

        for trade in trades:
            if trade.pnl > 0:
                current_win_streak += 1
                current_loss_streak = 0
                win_streak = max(win_streak, current_win_streak)
            else:
                current_loss_streak += 1
                current_win_streak = 0
                loss_streak = max(loss_streak, current_loss_streak)

        return win_streak, loss_streak

    def _calculate_monthly_win_rate(self, trades: List[BacktestTrade]) -> float:
        """Calculate percentage of profitable months."""
        if not trades:
            return 0

        # Group trades by month
        monthly_pnl = {}
        for trade in trades:
            month_key = trade.exit_time.strftime("%Y-%m")
            monthly_pnl[month_key] = monthly_pnl.get(month_key, 0) + trade.pnl

        winning_months = sum(1 for pnl in monthly_pnl.values() if pnl > 0)
        total_months = len(monthly_pnl)

        return winning_months / total_months if total_months > 0 else 0

    def print_report(self, metrics: PerformanceMetrics) -> None:
        """Print formatted performance report."""
        print("\n" + "="*60)
        print("📊 BACKTEST PERFORMANCE REPORT")
        print("="*60)

        print("\n🎯 RETURN METRICS")
        print(f"  Total Return:        {metrics.total_return_pct:>8.2f}%")
        print(f"  CAGR:                {metrics.cagr:>8.2f}%")
        print(f"  Daily Return (avg):  {metrics.daily_return_mean:>8.4f}%")
        print(f"  Daily Return (std):  {metrics.daily_return_std:>8.4f}%")

        print("\n⚖️  RISK-ADJUSTED RETURNS")
        print(f"  Sharpe Ratio:        {metrics.sharpe_ratio:>8.2f}")
        print(f"  Sortino Ratio:       {metrics.sortino_ratio:>8.2f}")
        print(f"  Calmar Ratio:        {metrics.calmar_ratio:>8.2f}")

        print("\n📉 DRAWDOWN ANALYSIS")
        print(f"  Max Drawdown:        {metrics.max_drawdown_pct:>8.2f}%")
        print(f"  Max DD Duration:     {metrics.max_drawdown_duration_days:>8} days")
        print(f"  Recovery Factor:     {metrics.recovery_factor:>8.2f}")

        print("\n📊 TRADE STATISTICS")
        print(f"  Total Trades:        {metrics.total_trades:>8}")
        print(f"  Win Rate:            {metrics.win_rate:>8.2f}%")
        print(f"  Profit Factor:       {metrics.profit_factor:>8.2f}")
        print(f"  Avg Win:             ${metrics.avg_win:>8.2f}")
        print(f"  Avg Loss:            ${metrics.avg_loss:>8.2f}")
        print(f"  Expectancy:          ${metrics.expectancy:>8.2f}")

        print("\n🎲 CONSISTENCY METRICS")
        print(f"  Max Win Streak:      {metrics.win_streak_max:>8}")
        print(f"  Max Loss Streak:     {metrics.loss_streak_max:>8}")
        print(f"  Monthly Win Rate:    {metrics.monthly_win_rate:>8.2f}%")

        print("\n💰 ADDITIONAL STATS")
        print(f"  Total Fees:          ${metrics.total_fees:>8.2f}")
        print(f"  Trades/Day:          {metrics.trades_per_day:>8.2f}")

        print("\n" + "="*60)

        # Performance rating
        score = self._calculate_score(metrics)
        rating = self._get_rating(score)
        print(f"🏆 OVERALL RATING: {rating} (Score: {score:.1f}/100)")
        print("="*60 + "\n")

    def _calculate_score(self, m: PerformanceMetrics) -> float:
        """Calculate overall performance score (0-100)."""
        score = 0

        # Return component (30 points)
        if m.cagr > 50:
            score += 30
        elif m.cagr > 30:
            score += 25
        elif m.cagr > 15:
            score += 20
        elif m.cagr > 0:
            score += 10

        # Risk-adjusted (30 points)
        if m.sharpe_ratio > 2:
            score += 30
        elif m.sharpe_ratio > 1.5:
            score += 25
        elif m.sharpe_ratio > 1:
            score += 20
        elif m.sharpe_ratio > 0.5:
            score += 10

        # Drawdown (20 points)
        if abs(m.max_drawdown_pct) < 5:
            score += 20
        elif abs(m.max_drawdown_pct) < 10:
            score += 15
        elif abs(m.max_drawdown_pct) < 20:
            score += 10
        elif abs(m.max_drawdown_pct) < 30:
            score += 5

        # Win rate (20 points)
        if m.win_rate > 70:
            score += 20
        elif m.win_rate > 60:
            score += 15
        elif m.win_rate > 50:
            score += 10
        elif m.win_rate > 40:
            score += 5

        return min(score, 100)

    def _get_rating(self, score: float) -> str:
        """Convert score to rating."""
        if score >= 90:
            return "EXCEPTIONAL ⭐⭐⭐⭐⭐"
        elif score >= 75:
            return "EXCELLENT ⭐⭐⭐⭐"
        elif score >= 60:
            return "GOOD ⭐⭐⭐"
        elif score >= 40:
            return "FAIR ⭐⭐"
        else:
            return "POOR ⭐"
