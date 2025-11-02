# Trading Agent Backtesting Framework

The backtesting subsystem provides an event-driven engine for validating strategies against
historical market data before deploying to production. It combines data loading utilities,
execution simulation, and comprehensive performance analytics.

## Key Components

- **`trading_agent.backtesting.backtest_engine`** – event-driven execution loop with
  configurable risk controls, slippage, spread limits, and equity tracking.
- **`trading_agent.backtesting.historical_data`** – MT5 CSV loader, data cleaning utilities,
  timeframe resampling, and synthetic data generation for quick experiments.
- **`trading_agent.backtesting.performance_metrics`** – risk/return analytics including
  Sharpe, Sortino, drawdown analysis, and trade statistics.
- **`trading_agent.backtesting.strategies`** – example strategies (RSI, MACD, hybrid, and
  adaptive risk sizing) that illustrate how to interact with the engine.

## Quick Start

```python
from trading_agent.backtesting import (
    BacktestEngine,
    BacktestConfig,
    generate_test_data,
    get_strategy,
    PerformanceCalculator,
)

# Prepare data
bars = generate_test_data(num_bars=10_000)

# Configure and run the engine
engine = BacktestEngine(BacktestConfig(initial_capital=25_000))
engine.add_data(bars)
engine.add_strategy(get_strategy("rsi"))
results = engine.run()

# Analyse performance
calculator = PerformanceCalculator()
metrics = calculator.calculate(engine.closed_trades, engine.equity_curve, engine.config.initial_capital)
calculator.print_report(metrics)
```

## CLI Demo

Run the CLI demo to execute an end-to-end backtest:

```bash
python examples/demo_backtest.py --strategy adaptive --bars 15000
```

Pass `--csv` to load an MT5 export, or adjust `--capital`, `--commission`, and other options
to mirror the desired trading environment.

## Next Steps

1. Integrate real tool calculations by wiring the engine's `call_tool` method to the
   production tool registry under `trading_agent.tools`.
2. Expand strategy coverage with production rules or connect the DSL-powered strategies
   from `trading_agent.strategies`.
3. Plug the backtesting results into reporting dashboards to support model governance and
   compliance reviews.
