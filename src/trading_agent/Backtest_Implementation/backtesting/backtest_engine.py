"""
Core Backtesting Engine for Trading Agent v2.0+

Event-driven backtesting framework that:
1. Loads historical MT5 data
2. Executes trading tools (RSI, MACD, etc.) bar-by-bar
3. Simulates order execution with realistic slippage
4. Tracks performance metrics (win rate, Sharpe, drawdown)

Architecture inspired by FinAgent + Backtrader patterns.
"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np


class EventType(Enum):
    """Backtest event types."""
    MARKET = "market"  # New bar received
    SIGNAL = "signal"  # Tool generated signal
    ORDER = "order"    # Order placed
    FILL = "fill"      # Order executed
    

@dataclass
class BacktestConfig:
    """Backtesting configuration."""
    initial_capital: float = 10000.0
    commission: float = 0.0002  # 0.02% per trade
    slippage_pips: float = 0.5  # Average slippage in pips
    max_spread_pips: float = 3.0  # Max allowable spread
    
    # Risk parameters
    max_position_size: float = 0.02  # 2% of capital per trade
    max_daily_loss: float = 0.05  # 5% daily loss limit
    
    # Performance tracking
    benchmark: Optional[str] = None  # Compare to buy-and-hold
    
    # Execution realism
    use_realistic_fills: bool = True  # Simulate partial fills
    timeout_bars: int = 5  # Cancel unfilled orders after N bars


@dataclass
class BacktestBar:
    """Single bar of historical data."""
    timestamp: datetime
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    spread: float = 0.0  # In pips
    

@dataclass
class BacktestPosition:
    """Open position tracking."""
    symbol: str
    direction: str  # "buy" or "sell"
    entry_price: float
    size: float  # Lot size
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    entry_time: datetime = field(default_factory=datetime.now)
    unrealized_pnl: float = 0.0
    

@dataclass
class BacktestTrade:
    """Completed trade record."""
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    size: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    return_pct: float
    commission: float
    slippage: float
    bars_held: int
    exit_reason: str  # "tp", "sl", "signal", "timeout"
    

class BacktestEngine:
    """
    Event-driven backtesting engine.
    
    Usage:
        engine = BacktestEngine(config=BacktestConfig())
        engine.add_data(historical_bars)
        engine.add_strategy(my_strategy_function)
        results = engine.run()
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        
        # Data storage
        self.data: List[BacktestBar] = []
        self.current_bar_idx: int = 0
        
        # Portfolio state
        self.capital: float = self.config.initial_capital
        self.positions: List[BacktestPosition] = []
        self.closed_trades: List[BacktestTrade] = []
        self.equity_curve: List[Dict[str, Any]] = []
        
        # Strategy/tool functions
        self.strategy_func: Optional[Callable] = None
        
        # Event handlers
        self.event_handlers: Dict[EventType, List[Callable]] = {
            EventType.MARKET: [],
            EventType.SIGNAL: [],
            EventType.ORDER: [],
            EventType.FILL: []
        }
        
        # Performance tracking
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
    def add_data(self, bars: List[BacktestBar]) -> None:
        """Load historical data for backtesting."""
        self.data = sorted(bars, key=lambda x: x.timestamp)
        if not self.data:
            raise ValueError("No data provided for backtesting")
            
    def add_strategy(self, strategy_func: Callable) -> None:
        """
        Add strategy function that will be called for each bar.
        
        Function signature:
            def strategy(engine: BacktestEngine, bar: BacktestBar) -> Dict[str, Any]:
                # Use engine.call_tool() to execute RSI, MACD, etc.
                # Return trading signal: {"action": "buy", "sl": ..., "tp": ...}
        """
        self.strategy_func = strategy_func
        
    def on_event(self, event_type, handler: Callable) -> None:
        """Register event handler."""
        # Accept both EventType enum and string
        if isinstance(event_type, str):
            event_type = EventType(event_type)
        self.event_handlers[event_type].append(handler)
        
    def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Execute trading tool (RSI, MACD, etc.) with historical data.
        
        This is a placeholder - in production, integrate with actual tool registry:
            from trading_agent.tools import registry
            tool = registry.get(tool_name)
            return tool.execute(**kwargs)
        """
        # Placeholder for tool execution
        # TODO: Integrate with actual tool registry
        if tool_name == "calc_rsi":
            # Mock RSI calculation
            prices = kwargs.get("prices", [])
            if len(prices) < 14:
                return {"value": None, "confidence": 0.0, "error": "insufficient_data"}
            # Simplified RSI
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains[-14:])
            avg_loss = np.mean(losses[-14:])
            rs = avg_gain / avg_loss if avg_loss != 0 else 100
            rsi = 100 - (100 / (1 + rs))
            return {"value": rsi, "confidence": 0.85, "latency_ms": 1.2}
        
        raise NotImplementedError(f"Tool {tool_name} not implemented in backtest")
        
    def run(self) -> Dict[str, Any]:
        """
        Execute backtest loop.
        
        Returns:
            Performance summary with metrics, trades, equity curve.
        """
        if not self.data:
            raise ValueError("No data loaded. Call add_data() first.")
        if not self.strategy_func:
            raise ValueError("No strategy defined. Call add_strategy() first.")
            
        self.start_time = datetime.now()
        print(f"🚀 Starting backtest: {len(self.data)} bars from {self.data[0].timestamp} to {self.data[-1].timestamp}")
        
        # Main event loop
        for idx, bar in enumerate(self.data):
            self.current_bar_idx = idx
            
            # Update open positions (check SL/TP)
            self._update_positions(bar)
            
            # Emit market event
            for handler in self.event_handlers[EventType.MARKET]:
                handler(bar)
            
            # Execute strategy logic
            signal = self.strategy_func(self, bar)
            
            # Process signal
            if signal and signal.get("action") in ["buy", "sell"]:
                self._process_signal(bar, signal)
            
            # Track equity
            self._record_equity(bar)
        
        self.end_time = datetime.now()
        
        # Calculate final metrics
        return self._generate_report()
        
    def _update_positions(self, bar: BacktestBar) -> None:
        """Check if any positions hit SL/TP or need updating."""
        for position in self.positions[:]:  # Iterate over copy
            if position.symbol != bar.symbol:
                continue
                
            current_price = bar.close
            
            # Update unrealized P&L
            if position.direction == "buy":
                position.unrealized_pnl = (current_price - position.entry_price) * position.size * 100000  # Assuming standard lot
            else:  # sell
                position.unrealized_pnl = (position.entry_price - current_price) * position.size * 100000
            
            # Check stop loss
            if position.stop_loss:
                if (position.direction == "buy" and bar.low <= position.stop_loss) or \
                   (position.direction == "sell" and bar.high >= position.stop_loss):
                    self._close_position(position, position.stop_loss, bar, "sl")
                    continue
            
            # Check take profit
            if position.take_profit:
                if (position.direction == "buy" and bar.high >= position.take_profit) or \
                   (position.direction == "sell" and bar.low <= position.take_profit):
                    self._close_position(position, position.take_profit, bar, "tp")
                    continue
                    
    def _process_signal(self, bar: BacktestBar, signal: Dict[str, Any]) -> None:
        """Execute trade based on signal."""
        action = signal.get("action")
        size = signal.get("size", 0.01)  # Default 0.01 lots
        sl = signal.get("stop_loss")
        tp = signal.get("take_profit")
        
        # Risk checks
        if bar.spread > self.config.max_spread_pips:
            print(f"⚠️  Spread too wide: {bar.spread} pips > {self.config.max_spread_pips}")
            return
            
        # Calculate position size with risk management
        max_size = self.capital * self.config.max_position_size / bar.close
        size = min(size, max_size)
        
        # Simulate slippage
        if action == "buy":
            entry_price = bar.close + (self.config.slippage_pips * 0.0001)  # Add slippage
        else:  # sell
            entry_price = bar.close - (self.config.slippage_pips * 0.0001)
        
        # Create position
        position = BacktestPosition(
            symbol=bar.symbol,
            direction=action,
            entry_price=entry_price,
            size=size,
            stop_loss=sl,
            take_profit=tp,
            entry_time=bar.timestamp
        )
        
        self.positions.append(position)
        
        # Emit order event
        for handler in self.event_handlers[EventType.ORDER]:
            handler(position)
            
        print(f"📊 {action.upper()} {size} lots @ {entry_price:.5f} | SL: {sl} | TP: {tp}")
        
    def _close_position(self, position: BacktestPosition, exit_price: float, bar: BacktestBar, reason: str) -> None:
        """Close an open position."""
        # Calculate P&L
        if position.direction == "buy":
            pnl = (exit_price - position.entry_price) * position.size * 100000
        else:
            pnl = (position.entry_price - exit_price) * position.size * 100000
        
        # Apply commission
        commission = self.config.commission * position.size * 100000 * 2  # Entry + exit
        pnl -= commission
        
        # Update capital
        self.capital += pnl
        
        # Record trade
        bars_held = self.current_bar_idx - self.data.index(next(b for b in self.data if b.timestamp == position.entry_time))
        trade = BacktestTrade(
            symbol=position.symbol,
            direction=position.direction,
            entry_price=position.entry_price,
            exit_price=exit_price,
            size=position.size,
            entry_time=position.entry_time,
            exit_time=bar.timestamp,
            pnl=pnl,
            return_pct=(pnl / (position.entry_price * position.size * 100000)) * 100,
            commission=commission,
            slippage=self.config.slippage_pips,
            bars_held=bars_held,
            exit_reason=reason
        )
        
        self.closed_trades.append(trade)
        self.positions.remove(position)
        
        # Emit fill event
        for handler in self.event_handlers[EventType.FILL]:
            handler(trade)
            
        print(f"✅ Closed {position.direction} @ {exit_price:.5f} | P&L: ${pnl:.2f} | Reason: {reason}")
        
    def _record_equity(self, bar: BacktestBar) -> None:
        """Track equity curve."""
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions)
        total_equity = self.capital + unrealized_pnl
        
        self.equity_curve.append({
            "timestamp": bar.timestamp,
            "capital": self.capital,
            "unrealized_pnl": unrealized_pnl,
            "total_equity": total_equity,
            "open_positions": len(self.positions)
        })
        
    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        if not self.closed_trades:
            return {
                "status": "no_trades",
                "message": "No trades were executed during backtest"
            }
        
        # Basic metrics
        total_trades = len(self.closed_trades)
        winning_trades = [t for t in self.closed_trades if t.pnl > 0]
        losing_trades = [t for t in self.closed_trades if t.pnl <= 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        total_pnl = sum(t.pnl for t in self.closed_trades)
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        
        # Risk metrics
        returns = [t.return_pct for t in self.closed_trades]
        sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        # Drawdown
        equity_series = [e["total_equity"] for e in self.equity_curve]
        running_max = np.maximum.accumulate(equity_series)
        drawdowns = (equity_series - running_max) / running_max
        max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0
        
        # Duration
        duration = self.end_time - self.start_time if self.start_time and self.end_time else timedelta(0)
        
        return {
            "status": "success",
            "summary": {
                "initial_capital": self.config.initial_capital,
                "final_capital": self.capital,
                "total_pnl": total_pnl,
                "return_pct": (total_pnl / self.config.initial_capital) * 100,
                "duration_seconds": duration.total_seconds()
            },
            "trades": {
                "total": total_trades,
                "winners": len(winning_trades),
                "losers": len(losing_trades),
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_factor": abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
            },
            "risk_metrics": {
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown_pct": max_drawdown * 100,
                "avg_bars_per_trade": np.mean([t.bars_held for t in self.closed_trades])
            },
            "equity_curve": self.equity_curve,
            "all_trades": [
                {
                    "entry_time": t.entry_time.isoformat(),
                    "exit_time": t.exit_time.isoformat(),
                    "direction": t.direction,
                    "pnl": t.pnl,
                    "return_pct": t.return_pct,
                    "exit_reason": t.exit_reason
                }
                for t in self.closed_trades
            ]
        }


# Helper function for quick backtests
def quick_backtest(
    data: List[BacktestBar],
    strategy_func: Callable,
    config: Optional[BacktestConfig] = None
) -> Dict[str, Any]:
    """
    Convenience function for running a backtest.
    
    Example:
        results = quick_backtest(
            data=historical_bars,
            strategy_func=my_rsi_strategy,
            config=BacktestConfig(initial_capital=10000)
        )
    """
    engine = BacktestEngine(config=config)
    engine.add_data(data)
    engine.add_strategy(strategy_func)
    return engine.run()
