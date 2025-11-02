"""
Strategy Tester - Backtesting Framework
Evaluates strategy performance using historical data
"""

import time
from dataclasses import dataclass
from typing import Any

from ..decision.engine import FusedContext
from .base_strategy import BaseStrategy, StrategySignal


@dataclass
class BacktestResult:
    """Results from strategy backtest"""

    strategy_name: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_profit: float
    total_loss: float
    net_profit: float
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    avg_trade_duration_ms: float
    backtest_duration_ms: float
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "strategy_name": self.strategy_name,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "total_profit": self.total_profit,
            "total_loss": self.total_loss,
            "net_profit": self.net_profit,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "avg_trade_duration_ms": self.avg_trade_duration_ms,
            "backtest_duration_ms": self.backtest_duration_ms,
            "metadata": self.metadata,
        }


class StrategyTester:
    """Backtesting framework for strategies"""

    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.trades: list[dict[str, Any]] = []
        self.equity_curve: list[float] = []

    def backtest(self, strategy: BaseStrategy, contexts: list[FusedContext]) -> BacktestResult:
        """
        Run backtest on strategy with historical contexts

        Args:
            strategy: Strategy to test
            contexts: List of historical FusedContext objects

        Returns:
            BacktestResult with performance metrics
        """
        start_time = time.perf_counter()

        # Reset state
        self.balance = self.initial_balance
        self.trades = []
        self.equity_curve = [self.initial_balance]

        # Track open position
        open_position: dict[str, Any] | None = None

        # Simulate trading
        for context in contexts:
            # Check if strategy is active
            if not strategy.evaluate(context):
                continue

            # Generate signal
            signal = strategy.generate_signal(context)

            # Handle position
            if open_position is None:
                # Open new position
                open_position = self._open_position(signal, context)
            else:
                # Check if position should be closed
                if self._should_close_position(open_position, signal, context):
                    self._close_position(open_position, context)
                    open_position = None

            # Update equity curve
            current_equity = self._calculate_equity(open_position, context)
            self.equity_curve.append(current_equity)

        # Close any remaining position
        if open_position is not None:
            self._close_position(open_position, contexts[-1])

        # Calculate metrics
        end_time = time.perf_counter()
        backtest_duration_ms = (end_time - start_time) * 1000
        # Ensure non-zero duration for safety
        if backtest_duration_ms == 0.0:
            backtest_duration_ms = 0.001
        result = self._calculate_metrics(strategy.name, backtest_duration_ms)

        return result

    def _open_position(self, signal: StrategySignal, context: FusedContext) -> dict[str, Any]:
        """Open new position"""
        # Calculate position size (simplified - use 10% of balance)
        position_size = self.balance * 0.1 / context.price

        return {
            "action": signal.action,
            "entry_price": context.price,
            "entry_time": context.timestamp,
            "size": position_size,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
        }

    def _should_close_position(
        self,
        position: dict[str, Any],
        signal: StrategySignal,
        context: FusedContext,
    ) -> bool:
        """Check if position should be closed"""
        # Close if signal reverses
        if signal.action != position["action"]:
            return True

        # Close if stop loss hit
        if position["action"] == "BUY":
            if context.price <= position["stop_loss"]:
                return True
            if position["take_profit"] and context.price >= position["take_profit"]:
                return True
        elif position["action"] == "SELL":
            if context.price >= position["stop_loss"]:
                return True
            if position["take_profit"] and context.price <= position["take_profit"]:
                return True

        return False

    def _close_position(self, position: dict[str, Any], context: FusedContext) -> None:
        """Close position and record trade"""
        # Calculate P&L
        if position["action"] == "BUY":
            pnl = (context.price - position["entry_price"]) * position["size"]
        else:  # SELL
            pnl = (position["entry_price"] - context.price) * position["size"]

        # Update balance
        self.balance += pnl

        # Record trade
        trade_duration_ms = (context.timestamp - position["entry_time"]).total_seconds() * 1000

        self.trades.append(
            {
                "action": position["action"],
                "entry_price": position["entry_price"],
                "exit_price": context.price,
                "entry_time": position["entry_time"],
                "exit_time": context.timestamp,
                "size": position["size"],
                "pnl": pnl,
                "duration_ms": trade_duration_ms,
            }
        )

    def _calculate_equity(self, position: dict[str, Any] | None, context: FusedContext) -> float:
        """Calculate current equity"""
        if position is None:
            return self.balance

        # Calculate unrealized P&L
        if position["action"] == "BUY":
            unrealized_pnl = (context.price - position["entry_price"]) * position["size"]
        else:  # SELL
            unrealized_pnl = (position["entry_price"] - context.price) * position["size"]

        return self.balance + unrealized_pnl

    def _calculate_metrics(self, strategy_name: str, backtest_duration_ms: float) -> BacktestResult:
        """Calculate performance metrics"""
        if not self.trades:
            return BacktestResult(
                strategy_name=strategy_name,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                total_profit=0.0,
                total_loss=0.0,
                net_profit=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                avg_trade_duration_ms=0.0,
                backtest_duration_ms=backtest_duration_ms,
                metadata={},
            )

        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t["pnl"] > 0)
        losing_trades = sum(1 for t in self.trades if t["pnl"] < 0)

        total_profit = sum(t["pnl"] for t in self.trades if t["pnl"] > 0)
        total_loss = abs(sum(t["pnl"] for t in self.trades if t["pnl"] < 0))
        net_profit = self.balance - self.initial_balance

        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        profit_factor = total_profit / total_loss if total_loss > 0 else 0.0

        # Sharpe ratio (simplified)
        returns = [t["pnl"] / self.initial_balance for t in self.trades]
        avg_return = sum(returns) / len(returns) if returns else 0.0
        std_return = (
            (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if returns else 0.0
        )
        sharpe_ratio = avg_return / std_return if std_return > 0 else 0.0

        # Max drawdown
        peak = self.initial_balance
        max_drawdown = 0.0
        for equity in self.equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak if peak > 0 else 0.0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Average trade duration
        avg_trade_duration_ms = (
            sum(t["duration_ms"] for t in self.trades) / total_trades if total_trades > 0 else 0.0
        )

        return BacktestResult(
            strategy_name=strategy_name,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            total_profit=total_profit,
            total_loss=total_loss,
            net_profit=net_profit,
            win_rate=win_rate,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            avg_trade_duration_ms=avg_trade_duration_ms,
            backtest_duration_ms=backtest_duration_ms,
            metadata={
                "initial_balance": self.initial_balance,
                "final_balance": self.balance,
                "total_contexts": 0,  # Will be set by caller
            },
        )
