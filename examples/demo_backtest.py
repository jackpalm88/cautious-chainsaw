#!/usr/bin/env python3
"""Utility script demonstrating the backtesting framework workflow."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Ensure the project src directory is on the Python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

def main():
    from trading_agent.backtesting import (
        BacktestConfig,
        BacktestEngine,
        PerformanceCalculator,
        generate_test_data,
        get_strategy,
        load_mt5_csv,
    )

    parser = argparse.ArgumentParser(description="Run strategy backtest")
    parser.add_argument(
        "--strategy",
        type=str,
        default="rsi",
        choices=["rsi", "macd", "combined", "adaptive"],
        help="Strategy to test"
    )
    parser.add_argument(
        "--bars",
        type=int,
        default=10000,
        help="Number of bars to generate (if not using CSV)"
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="Path to MT5 CSV file (optional)"
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=10000.0,
        help="Initial capital"
    )
    parser.add_argument(
        "--commission",
        type=float,
        default=0.0002,
        help="Commission per trade (0.0002 = 0.02%)"
    )

    args = parser.parse_args()

    print("\n" + "="*60)
    print("🚀 TRADING AGENT BACKTESTING FRAMEWORK")
    print("="*60)

    # Step 1: Load or generate data
    print("\n📊 Step 1: Loading Data...")

    if args.csv:
        print(f"Loading CSV: {args.csv}")
        # Note: User needs to provide symbol and timeframe
        bars = load_mt5_csv(args.csv, symbol="EURUSD", timeframe="M5")
    else:
        print(f"Generating {args.bars} test bars...")
        bars = generate_test_data(num_bars=args.bars)

    print(f"✅ Loaded {len(bars)} bars")
    print(f"   Period: {bars[0].timestamp} to {bars[-1].timestamp}")
    print(f"   Symbol: {bars[0].symbol}")
    print(f"   Timeframe: {bars[0].timeframe}")

    # Step 2: Configure backtest
    print("\n⚙️  Step 2: Configuring Backtest...")

    config = BacktestConfig(
        initial_capital=args.capital,
        commission=args.commission,
        slippage_pips=0.5,
        max_spread_pips=3.0,
        max_position_size=0.02,  # 2% risk per trade
        use_realistic_fills=True
    )

    print(f"   Initial Capital: ${config.initial_capital:,.2f}")
    print(f"   Commission: {config.commission*100:.2f}%")
    print(f"   Slippage: {config.slippage_pips} pips")
    print(f"   Max Risk/Trade: {config.max_position_size*100:.1f}%")

    # Step 3: Select strategy
    print(f"\n🎯 Step 3: Loading Strategy '{args.strategy}'...")

    strategy_func = get_strategy(args.strategy)

    # Step 4: Run backtest
    print("\n🏃 Step 4: Running Backtest...")
    print("   (This may take a few moments...)")

    start_time = datetime.now()

    engine = BacktestEngine(config=config)
    engine.add_data(bars)
    engine.add_strategy(strategy_func)

    # Optional: Add event handlers for live updates
    def on_fill(trade):
        """Print trade notifications."""
        pass  # Suppress for demo

    engine.on_event("fill", on_fill)

    results = engine.run()

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"✅ Backtest Complete in {duration:.2f}s")

    # Step 5: Calculate metrics
    if results["status"] == "success":
        print("\n📈 Step 5: Calculating Performance Metrics...")

        calculator = PerformanceCalculator(risk_free_rate=0.02)
        metrics = calculator.calculate(
            trades=engine.closed_trades,
            equity_curve=engine.equity_curve,
            initial_capital=config.initial_capital
        )

        # Print detailed report
        calculator.print_report(metrics)

        # Additional insights
        print("\n💡 KEY INSIGHTS")
        print("="*60)

        if metrics.win_rate > 60 and metrics.profit_factor > 1.5:
            print("✅ STRONG STRATEGY: High win rate + good profit factor")
        elif metrics.win_rate > 50 and metrics.sharpe_ratio > 1.0:
            print("✅ VIABLE STRATEGY: Positive expectancy + risk-adjusted returns")
        elif metrics.win_rate < 40:
            print("⚠️  LOW WIN RATE: Consider refining entry criteria")

        if abs(metrics.max_drawdown_pct) > 30:
            print("⚠️  HIGH DRAWDOWN: Risk management needs improvement")
        elif abs(metrics.max_drawdown_pct) < 10:
            print("✅ EXCELLENT DRAWDOWN CONTROL")

        if metrics.profit_factor < 1.0:
            print("❌ LOSING STRATEGY: Profit factor < 1.0")
        elif metrics.profit_factor > 2.0:
            print("✅ HIGHLY PROFITABLE: Profit factor > 2.0")

        print("\n📋 NEXT STEPS")
        print("="*60)
        print("1. Review equity curve for consistency")
        print("2. Test on different time periods (walk-forward)")
        print("3. Optimize parameters (but avoid overfitting)")
        print("4. Paper trade before live deployment")
        print("5. Implement proper risk management")

    else:
        print(f"\n❌ Backtest Failed: {results.get('message', 'Unknown error')}")

    print("\n" + "="*60)
    print("Demo complete! Check the results above.")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
