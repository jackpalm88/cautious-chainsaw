"""
Demo: Trading Agent Tools
Demonstrates basic tool usage and registry
"""

import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.trading_agent.tools import (
    CalcRSI,
    CalcMACD,
    ToolRegistry,
    get_registry,
)


def demo_rsi():
    """Demonstrate RSI calculation"""
    print("=" * 60)
    print("RSI CALCULATION DEMO")
    print("=" * 60)

    # Sample price data (uptrend)
    prices = [100 + i * 0.5 for i in range(30)]

    # Create RSI tool
    rsi_tool = CalcRSI(period=14)

    # Execute
    result = rsi_tool.execute(prices=prices)

    print(f"\nTool: {rsi_tool}")
    print(f"Prices: {len(prices)} samples")
    print(f"\nResult:")
    print(f"  RSI: {result.value['rsi']:.2f}")
    print(f"  Signal: {result.value['signal']}")
    print(f"  Confidence: {result.confidence:.3f}")
    print(f"  Latency: {result.latency_ms:.2f}ms")

    print(f"\nConfidence Components:")
    for key, value in result.metadata['confidence_components'].items():
        print(f"  {key}: {value:.3f}")

    print(f"\nHigh Confidence: {result.is_high_confidence}")


def demo_macd():
    """Demonstrate MACD calculation"""
    print("\n" + "=" * 60)
    print("MACD CALCULATION DEMO")
    print("=" * 60)

    # Sample price data
    prices = [100 + i * 0.3 for i in range(50)]

    # Create MACD tool
    macd_tool = CalcMACD()

    # Execute
    result = macd_tool.execute(prices=prices)

    print(f"\nTool: {macd_tool}")
    print(f"Prices: {len(prices)} samples")
    print(f"\nResult:")
    print(f"  MACD: {result.value['macd']:.5f}")
    print(f"  Signal: {result.value['signal']:.5f}")
    print(f"  Histogram: {result.value['histogram']:.5f}")
    print(f"  Trading Signal: {result.value['trading_signal']}")
    print(f"  Confidence: {result.confidence:.3f}")
    print(f"  Latency: {result.latency_ms:.2f}ms")


def demo_registry():
    """Demonstrate Tool Registry"""
    print("\n" + "=" * 60)
    print("TOOL REGISTRY DEMO")
    print("=" * 60)

    # Create registry
    registry = ToolRegistry()

    # Register tools
    rsi_tool = CalcRSI()
    macd_tool = CalcMACD()

    registry.register(rsi_tool)
    registry.register(macd_tool)

    print(f"\nRegistry: {registry}")
    print(f"Total tools: {len(registry)}")

    # Get catalog
    catalog = registry.catalog()

    print(f"\nCatalog:")
    print(f"  Version: {catalog['version']}")
    print(f"  Total Tools: {catalog['total_tools']}")
    print(f"  By Tier: {catalog['tools_by_tier']}")

    print(f"\nRegistered Tools:")
    for tool_schema in catalog['tools']:
        print(f"  - {tool_schema['name']} (v{tool_schema['version']}, {tool_schema['tier']})")

    # Export for LLM
    print(f"\n" + "-" * 60)
    print("LLM Function Calling Schema:")
    print("-" * 60)

    llm_functions = registry.get_llm_functions()
    print(json.dumps(llm_functions, indent=2))


def demo_confidence_threshold():
    """Demonstrate confidence threshold checking"""
    print("\n" + "=" * 60)
    print("CONFIDENCE THRESHOLD DEMO")
    print("=" * 60)

    # Scenario 1: Sufficient data (high confidence)
    print("\nScenario 1: Sufficient data")
    prices_good = [100 + i * 0.5 for i in range(50)]
    rsi_tool = CalcRSI(period=14)
    result = rsi_tool.execute(prices=prices_good)

    print(f"  Confidence: {result.confidence:.3f}")
    print(f"  High Confidence (≥0.7): {result.is_high_confidence}")
    print(f"  Decision: {'PROCEED' if result.is_high_confidence else 'ABORT'}")

    # Scenario 2: Minimal data (lower confidence)
    print("\nScenario 2: Minimal data")
    prices_minimal = [100 + i * 0.5 for i in range(15)]  # Just enough
    result = rsi_tool.execute(prices=prices_minimal)

    print(f"  Confidence: {result.confidence:.3f}")
    print(f"  High Confidence (≥0.7): {result.is_high_confidence}")
    print(f"  Decision: {'PROCEED' if result.is_high_confidence else 'ABORT'}")


def main():
    """Run all demos"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "TRADING AGENT TOOLS - DEMO" + " " * 22 + "║")
    print("╚" + "=" * 58 + "╝")

    demo_rsi()
    demo_macd()
    demo_registry()
    demo_confidence_threshold()

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Add more atomic tools (Bollinger Bands, ATR, etc.)")
    print("  2. Create composite tools (TechnicalOverview)")
    print("  3. Implement execution tools (GenerateOrder)")
    print("  4. Integrate with MT5 Bridge")
    print()


if __name__ == '__main__':
    main()
