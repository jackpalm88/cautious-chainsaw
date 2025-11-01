"""
Demo: MarketContext Tool
Demonstrates market regime detection and volatility analysis
"""

import numpy as np

from src.trading_agent.tools import MarketContext


def generate_trending_market():
    """Generate uptrend data"""
    return [100 + i * 1.0 for i in range(100)]


def generate_ranging_market():
    """Generate sideways movement"""
    return [100 + np.sin(i * 0.1) * 2 for i in range(100)]


def generate_volatile_market():
    """Generate high volatility"""
    np.random.seed(42)
    return [100 + np.random.randn() * 5 for i in range(100)]


def print_result(scenario, result):
    """Print formatted result"""
    print(f"\n{'=' * 60}")
    print(f"{scenario}")
    print(f"{'=' * 60}")
    print("📊 MARKET ANALYSIS:")
    print(f"  Regime: {result.value['regime'].upper()}")
    print(f"  Volatility (ATR): {result.value['volatility']:.4f}")
    print(f"  Volatility (Normalized): {result.value['volatility_normalized']:.4f}")
    print(f"  Trend Strength: {result.value['trend_strength']:.2f}")
    print("\n📈 METADATA:")
    print(f"  Confidence: {result.confidence:.3f}")
    print(f"  Latency: {result.latency_ms:.2f}ms")
    print(f"  Sample Size: {result.metadata['sample_size']}")
    print(f"  ATR Period: {result.metadata['atr_period']}")
    print(f"  Regime Lookback: {result.metadata['regime_lookback']}")


def main():
    print("\n" + "=" * 60)
    print("MARKETCONTEXT TOOL DEMO")
    print("=" * 60)

    tool = MarketContext()

    # Scenario 1: Trending Market
    trending_prices = generate_trending_market()
    result = tool.execute(prices=trending_prices)
    print_result("SCENARIO 1: TRENDING MARKET (UPTREND)", result)

    # Scenario 2: Ranging Market
    ranging_prices = generate_ranging_market()
    result = tool.execute(prices=ranging_prices)
    print_result("SCENARIO 2: RANGING MARKET (SIDEWAYS)", result)

    # Scenario 3: Volatile Market
    volatile_prices = generate_volatile_market()
    result = tool.execute(prices=volatile_prices)
    print_result("SCENARIO 3: VOLATILE MARKET (HIGH NOISE)", result)

    # Scenario 4: Custom Parameters
    print(f"\n{'=' * 60}")
    print("SCENARIO 4: CUSTOM PARAMETERS")
    print(f"{'=' * 60}")
    custom_tool = MarketContext(atr_period=20, regime_lookback=30)
    result = custom_tool.execute(prices=trending_prices)
    print("📊 CUSTOM CONFIG:")
    print("  ATR Period: 20 (vs default 14)")
    print("  Regime Lookback: 30 (vs default 50)")
    print("\n📈 RESULT:")
    print(f"  Regime: {result.value['regime'].upper()}")
    print(f"  Confidence: {result.confidence:.3f}")
    print(f"  Latency: {result.latency_ms:.2f}ms")

    # Scenario 5: LLM Function Schema
    print(f"\n{'=' * 60}")
    print("SCENARIO 5: LLM FUNCTION CALLING SCHEMA")
    print(f"{'=' * 60}")
    schema = tool.get_schema()
    print("📋 SCHEMA:")
    print(f"  Name: {schema['name']}")
    print(f"  Description: {schema['description']}")
    print("  Parameters:")
    for param, details in schema['parameters']['properties'].items():
        print(f"    - {param}: {details['type']} ({details['description']})")

    print(f"\n{'=' * 60}")
    print("DEMO COMPLETE")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
