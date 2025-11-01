"""
Demo: Strategy Builder (DSL + Compiler)
Demonstrates strategy compilation and evaluation
"""

from datetime import datetime
from pathlib import Path

from src.trading_agent.decision.engine import FusedContext
from src.trading_agent.strategies.compiler import StrategyCompiler


def print_strategy_info(strategy):
    """Print strategy information"""
    print(f"\n{'=' * 60}")
    print(f"STRATEGY: {strategy.name}")
    print(f"{'=' * 60}")
    print("📋 METADATA:")
    print(f"  Author: {strategy.metadata['author']}")
    print(f"  Version: {strategy.metadata['version']}")
    print(f"  Priority: {strategy.metadata.get('priority', 'N/A')}")
    print(f"  Tags: {', '.join(strategy.metadata.get('tags', []))}")
    print(f"  Active Regimes: {', '.join(strategy.metadata.get('active_regimes', ['all']))}")
    print("\n📊 DESCRIPTION:")
    print(f"  {strategy.description}")
    print("\n⚙️ CONDITIONS:")
    for i, cond in enumerate(strategy.conditions, 1):
        print(f"  {i}. {cond['field']} {cond['operator']} {cond['value']}")
    print(f"\n💰 ACTION: {strategy.action}")
    print("\n🛡️ RISK MANAGEMENT:")
    print(f"  Stop Loss: {strategy.risk['stop_loss_percent']}%")
    if "take_profit_percent" in strategy.risk:
        print(f"  Take Profit: {strategy.risk['take_profit_percent']}%")
    print(f"  Max Risk per Trade: {strategy.risk['max_risk_per_trade_percent']}%")


def print_evaluation(context, strategy, is_active, signal=None):
    """Print evaluation results"""
    print(f"\n{'=' * 60}")
    print("EVALUATION")
    print(f"{'=' * 60}")
    print("📊 MARKET CONTEXT:")
    print(f"  Symbol: {context.symbol}")
    print(f"  Price: {context.price:.5f}")
    print(f"  RSI: {context.rsi}")
    print(f"  MACD Histogram: {context.macd_histogram}")
    print(f"  Regime: {context.regime}")
    print("\n🎯 EVALUATION RESULT:")
    print(f"  Strategy Active: {is_active}")

    if is_active and signal:
        print("\n📈 SIGNAL:")
        print(f"  Action: {signal.action}")
        print(f"  Confidence: {signal.confidence:.3f}")
        print(f"  Stop Loss: {signal.stop_loss:.5f}")
        if signal.take_profit:
            print(f"  Take Profit: {signal.take_profit:.5f}")
        print("\n💭 REASONING:")
        print(f"  {signal.reasoning}")
        print("\n📋 METADATA:")
        for key, value in signal.metadata.items():
            print(f"  {key}: {value}")


def main():
    print("\n" + "=" * 60)
    print("STRATEGY BUILDER DEMO (DSL + COMPILER)")
    print("=" * 60)

    # Initialize compiler
    compiler = StrategyCompiler()

    # Scenario 1: Load and compile strategy
    print("\n" + "=" * 60)
    print("SCENARIO 1: COMPILE STRATEGY FROM YAML")
    print("=" * 60)

    strategy_path = Path("data/strategies/rsi_oversold.yaml")
    strategy = compiler.compile_from_file(str(strategy_path))

    print_strategy_info(strategy)

    # Scenario 2: Evaluate with conditions MET
    print("\n" + "=" * 60)
    print("SCENARIO 2: CONDITIONS MET")
    print("=" * 60)

    context_met = FusedContext(
        symbol="EURUSD",
        price=1.0800,
        timestamp=datetime.now(),
        rsi=25.0,  # < 30 ✓
        macd_histogram=0.5,  # > 0 ✓
        regime="ranging",  # == "ranging" ✓
        technical_confidence=0.85,
    )

    is_active = strategy.evaluate(context_met)
    signal = strategy.generate_signal(context_met) if is_active else None

    print_evaluation(context_met, strategy, is_active, signal)

    # Scenario 3: Evaluate with conditions NOT MET
    print("\n" + "=" * 60)
    print("SCENARIO 3: CONDITIONS NOT MET")
    print("=" * 60)

    context_not_met = FusedContext(
        symbol="EURUSD",
        price=1.0800,
        timestamp=datetime.now(),
        rsi=75.0,  # > 30 ✗
        macd_histogram=0.5,
        regime="ranging",
    )

    is_active = strategy.evaluate(context_not_met)
    signal = strategy.generate_signal(context_not_met) if is_active else None

    print_evaluation(context_not_met, strategy, is_active, signal)

    # Scenario 4: Wrong regime
    print("\n" + "=" * 60)
    print("SCENARIO 4: WRONG REGIME (STRATEGY INACTIVE)")
    print("=" * 60)

    context_wrong_regime = FusedContext(
        symbol="EURUSD",
        price=1.0800,
        timestamp=datetime.now(),
        rsi=25.0,  # < 30 ✓
        macd_histogram=0.5,  # > 0 ✓
        regime="trending",  # != "ranging" ✗
    )

    is_active = strategy.evaluate(context_wrong_regime)
    signal = strategy.generate_signal(context_wrong_regime) if is_active else None

    print_evaluation(context_wrong_regime, strategy, is_active, signal)

    # Scenario 5: DSL Validation
    print("\n" + "=" * 60)
    print("SCENARIO 5: DSL VALIDATION")
    print("=" * 60)

    valid_dsl = {
        "name": "test_strategy",
        "description": "Test strategy",
        "metadata": {
            "author": "Test",
            "version": "1.0.0"
        },
        "conditions": [
            {"field": "rsi", "operator": "<", "value": 30}
        ],
        "action": "BUY",
        "risk": {
            "stop_loss_percent": 1.0,
            "max_risk_per_trade_percent": 1.0
        }
    }

    is_valid, error = compiler.validate(valid_dsl)
    print("📋 VALID DSL:")
    print(f"  Valid: {is_valid}")
    print(f"  Error: {error if error else 'None'}")

    invalid_dsl = {"name": "incomplete_strategy"}
    is_valid, error = compiler.validate(invalid_dsl)
    print("\n📋 INVALID DSL:")
    print(f"  Valid: {is_valid}")
    print(f"  Error: {error[:100]}...")  # Truncate long error

    print(f"\n{'=' * 60}")
    print("DEMO COMPLETE")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
