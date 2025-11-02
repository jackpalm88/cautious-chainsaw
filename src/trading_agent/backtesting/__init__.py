"""Trading Agent Backtesting Framework."""

from .backtest_engine import (
    BacktestBar,
    BacktestConfig,
    BacktestEngine,
    BacktestPosition,
    BacktestTrade,
    EventType,
    quick_backtest,
)
from .historical_data import (
    MT5DataLoader,
    generate_test_data,
    load_mt5_csv,
)
from .performance_metrics import PerformanceCalculator, PerformanceMetrics
from .strategies import (
    STRATEGIES,
    adaptive_risk_strategy,
    combined_rsi_macd_strategy,
    get_strategy,
    macd_strategy,
    rsi_strategy,
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
