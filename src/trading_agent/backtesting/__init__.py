"""
Trading Agent Backtesting Framework

A comprehensive backtesting system for validating trading strategies
against historical data before live deployment.

Features:
- Event-driven backtesting engine
- MT5 CSV data loader with cleaning
- Realistic order execution simulation
- Comprehensive performance metrics
- Pre-built example strategies

Quick Start:
    >>> from trading_agent.backtesting import generate_test_data, quick_backtest, rsi_strategy
    >>> 
    >>> # Generate test data
    >>> bars = generate_test_data(num_bars=10000)
    >>> 
    >>> # Run backtest
    >>> results = quick_backtest(bars, rsi_strategy)
    >>> 
    >>> # View results
    >>> print(f"Win Rate: {results['trades']['win_rate']:.1f}%")
    >>> print(f"Total P&L: ${results['summary']['total_pnl']:.2f}")

For more examples, see:
    examples/demo_backtest.py
"""

from .backtest_engine import (
    BacktestEngine,
    BacktestConfig,
    BacktestBar,
    BacktestPosition,
    BacktestTrade,
    EventType,
    quick_backtest
)

from .historical_data import (
    MT5DataLoader,
    load_mt5_csv,
    generate_test_data
)

from .performance_metrics import (
    PerformanceMetrics,
    PerformanceCalculator
)

from .strategies import (
    rsi_strategy,
    macd_strategy,
    combined_rsi_macd_strategy,
    adaptive_risk_strategy,
    get_strategy,
    STRATEGIES
)

__version__ = "1.0.0"

__all__ = [
    # Core engine
    "BacktestEngine",
    "BacktestConfig",
    "BacktestBar",
    "BacktestPosition",
    "BacktestTrade",
    "EventType",
    "quick_backtest",
    
    # Data loading
    "MT5DataLoader",
    "load_mt5_csv",
    "generate_test_data",
    
    # Performance
    "PerformanceMetrics",
    "PerformanceCalculator",
    
    # Strategies
    "rsi_strategy",
    "macd_strategy",
    "combined_rsi_macd_strategy",
    "adaptive_risk_strategy",
    "get_strategy",
    "STRATEGIES",
]
