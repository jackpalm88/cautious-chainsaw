"""
Demo: Strategy Builder Phase 3 (Tester + Registry + Selector)
Demonstrates backtesting, database storage, and strategy selection
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from src.trading_agent.decision.engine import FusedContext
from src.trading_agent.strategies.compiler import StrategyCompiler
from src.trading_agent.strategies.registry import StrategyRegistry
from src.trading_agent.strategies.selector import StrategySelector
from src.trading_agent.strategies.tester import StrategyTester


def generate_test_contexts(count: int = 100) -> list[FusedContext]:
    """Generate test market contexts"""
    base_time = datetime.now()
    contexts = []

    for i in range(count):
        # Simulate price movement
        price = 1.08 + (i % 20) * 0.001

        # Simulate RSI oscillation
        rsi = 30 + (i % 40) * 1.5

        # Simulate regime changes
        regime = "ranging" if i % 30 < 20 else "trending"

        contexts.append(
            FusedContext(
                symbol="EURUSD",
                price=price,
                timestamp=base_time + timedelta(minutes=i),
                rsi=rsi,
                macd_histogram=0.5 if rsi < 50 else -0.5,
                regime=regime,
                technical_confidence=0.8,
            )
        )

    return contexts


def main():
    print("\n" + "=" * 70)
    print("STRATEGY BUILDER PHASE 3 DEMO")
    print("Tester + Registry + Selector")
    print("=" * 70)

    # Setup
    compiler = StrategyCompiler()

    # Use temporary database for demo
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name

    registry = StrategyRegistry(db_path)
    selector = StrategySelector(registry)
    tester = StrategyTester(initial_balance=10000.0)

    # Generate test data
    contexts = generate_test_contexts(100)

    # Scenario 1: Compile and register strategies
    print("\n" + "=" * 70)
    print("SCENARIO 1: COMPILE AND REGISTER STRATEGIES")
    print("=" * 70)

    strategies_dsl = [
        {
            "name": "rsi_oversold",
            "description": "Buy when RSI is oversold",
            "metadata": {
                "author": "Demo",
                "version": "1.0.0",
                "priority": 8,
                "active_regimes": ["ranging"],
            },
            "conditions": [
                {"field": "rsi", "operator": "<", "value": 35},
                {"field": "regime", "operator": "==", "value": "ranging"},
            ],
            "action": "BUY",
            "risk": {
                "stop_loss_percent": 1.5,
                "take_profit_percent": 3.0,
                "max_risk_per_trade_percent": 1.0,
            },
        },
        {
            "name": "rsi_overbought",
            "description": "Sell when RSI is overbought",
            "metadata": {
                "author": "Demo",
                "version": "1.0.0",
                "priority": 7,
                "active_regimes": ["ranging"],
            },
            "conditions": [
                {"field": "rsi", "operator": ">", "value": 65},
                {"field": "regime", "operator": "==", "value": "ranging"},
            ],
            "action": "SELL",
            "risk": {
                "stop_loss_percent": 1.5,
                "take_profit_percent": 3.0,
                "max_risk_per_trade_percent": 1.0,
            },
        },
        {
            "name": "trend_following",
            "description": "Follow the trend",
            "metadata": {
                "author": "Demo",
                "version": "1.0.0",
                "priority": 6,
                "active_regimes": ["trending"],
            },
            "conditions": [
                {"field": "macd_histogram", "operator": ">", "value": 0},
                {"field": "regime", "operator": "==", "value": "trending"},
            ],
            "action": "BUY",
            "risk": {
                "stop_loss_percent": 2.0,
                "take_profit_percent": 4.0,
                "max_risk_per_trade_percent": 1.0,
            },
        },
    ]

    strategies = []
    for dsl in strategies_dsl:
        strategy = compiler.compile(dsl)
        strategies.append(strategy)

        # Register in database
        strategy_id = registry.register_strategy(
            name=dsl["name"],
            dsl_content=dsl,
            description=dsl["description"],
            author=dsl["metadata"]["author"],
            version=dsl["metadata"]["version"],
            priority=dsl["metadata"]["priority"],
        )

        print(f"\n✅ Registered: {dsl['name']} (ID: {strategy_id})")
        print(f"   Priority: {dsl['metadata']['priority']}")
        print(f"   Regimes: {', '.join(dsl['metadata']['active_regimes'])}")

    # Scenario 2: Backtest strategies
    print("\n" + "=" * 70)
    print("SCENARIO 2: BACKTEST STRATEGIES")
    print("=" * 70)

    for strategy in strategies:
        print(f"\n📊 Backtesting: {strategy.name}")

        result = tester.backtest(strategy, contexts)

        # Save result to database
        registry.save_backtest_result(result)

        print(f"   Total Trades: {result.total_trades}")
        print(f"   Win Rate: {result.win_rate:.1%}")
        print(f"   Net Profit: ${result.net_profit:.2f}")
        print(f"   Profit Factor: {result.profit_factor:.2f}")
        print(f"   Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"   Max Drawdown: {result.max_drawdown:.1%}")
        print(f"   Backtest Duration: {result.backtest_duration_ms:.2f}ms")

    # Scenario 3: Query strategies from database
    print("\n" + "=" * 70)
    print("SCENARIO 3: QUERY STRATEGIES FROM DATABASE")
    print("=" * 70)

    all_strategies = registry.list_strategies()
    print(f"\n📋 Total Strategies: {len(all_strategies)}")

    for strat in all_strategies:
        print(f"\n   {strat['name']}")
        print(f"   Priority: {strat['priority']}")
        print(f"   Active: {'Yes' if strat['active'] else 'No'}")

    # Scenario 4: Select best strategy
    print("\n" + "=" * 70)
    print("SCENARIO 4: SELECT BEST STRATEGY")
    print("=" * 70)

    # Ranging market context
    ranging_context = FusedContext(
        symbol="EURUSD",
        price=1.08,
        timestamp=datetime.now(),
        rsi=32.0,
        macd_histogram=0.3,
        regime="ranging",
        technical_confidence=0.85,
    )

    print("\n🎯 Market Context:")
    print(f"   Regime: {ranging_context.regime}")
    print(f"   RSI: {ranging_context.rsi}")
    print(f"   MACD Histogram: {ranging_context.macd_histogram}")

    best = selector.select_best(
        ranging_context, strategies, metric="net_profit", min_trades=5
    )

    if best:
        print(f"\n✅ Best Strategy: {best.name}")
        print(f"   Description: {best.description}")
    else:
        print("\n❌ No suitable strategy found")

    # Scenario 5: Ensemble selection
    print("\n" + "=" * 70)
    print("SCENARIO 5: ENSEMBLE SELECTION")
    print("=" * 70)

    ensemble = selector.select_ensemble(
        ranging_context, strategies, top_n=2, metric="sharpe_ratio"
    )

    print("\n📊 Ensemble (Top 2):")
    for strategy, weight in ensemble:
        print(f"   {strategy.name}: {weight:.1%} weight")

    # Scenario 6: Strategy rankings
    print("\n" + "=" * 70)
    print("SCENARIO 6: STRATEGY RANKINGS")
    print("=" * 70)

    rankings = selector.get_strategy_rankings(strategies, metric="net_profit")

    print("\n🏆 Rankings by Net Profit:")
    print(f"\n{'Rank':<6} {'Strategy':<20} {'Trades':<8} {'Win Rate':<10} {'Net Profit':<12}")
    print("-" * 70)

    for ranking in rankings:
        print(
            f"{ranking['rank']:<6} "
            f"{ranking['strategy_name']:<20} "
            f"{ranking['total_trades']:<8} "
            f"{ranking['win_rate']:<10.1%} "
            f"${ranking['net_profit']:<11.2f}"
        )

    # Scenario 7: Update strategy
    print("\n" + "=" * 70)
    print("SCENARIO 7: UPDATE STRATEGY")
    print("=" * 70)

    print("\n📝 Deactivating 'trend_following' strategy...")
    updated = registry.update_strategy(name="trend_following", active=False)

    if updated:
        print("   ✅ Strategy updated")

        # Verify
        strategy = registry.get_strategy("trend_following")
        print(f"   Active status: {'Yes' if strategy['active'] else 'No'}")

    # Cleanup
    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)

    print(f"\n📁 Database: {db_path}")
    print(f"   Strategies: {len(all_strategies)}")
    print(f"   Backtest Results: {sum(len(registry.get_backtest_results(s.name)) for s in strategies)}")

    # Clean up temp database
    Path(db_path).unlink(missing_ok=True)
    print("\n✅ Temporary database cleaned up\n")


if __name__ == "__main__":
    main()
