"""
Demo: INoT Engine Integration with Trading Agent
Demonstrates end-to-end decision-making with INoT multi-agent reasoning
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from trading_agent.decision import TradingDecisionEngine


def demo_basic_integration():
    """Demo basic INoT integration"""
    print("=" * 60)
    print("BASIC INOT INTEGRATION")
    print("=" * 60)

    # Initialize engine with INoT disabled (tools only)
    config = {
        "inot": {
            "enabled": False  # Start with tools only
        },
        "tools": {
            "rsi_period": 14,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "bb_period": 20,
            "bb_std": 2.0
        }
    }

    engine = TradingDecisionEngine(config)

    # Mock price data (trending up)
    prices = [1.0800 + i * 0.0001 for i in range(100)]

    # Analyze market
    context = engine.analyze_market("EURUSD", prices)

    print("\n📊 MARKET ANALYSIS:")
    print(f"  Symbol: {context.symbol}")
    print(f"  Price: {context.price:.5f}")
    rsi_str = f"{context.rsi:.2f}" if context.rsi else "N/A"
    macd_str = f"{context.macd:.5f}" if context.macd else "N/A"
    bb_pos_str = f"{context.bb_position:.2f}" if context.bb_position else "N/A"
    agree_str = f"{context.agreement_score:.2f}" if context.agreement_score else "N/A"
    conf_str = f"{context.technical_confidence:.2f}" if context.technical_confidence else "N/A"
    print(f"  RSI: {rsi_str} ({context.rsi_signal or 'N/A'})")
    print(f"  MACD: {macd_str} ({context.macd_signal or 'N/A'})")
    print(f"  BB Position: {bb_pos_str} ({context.bb_signal or 'N/A'})")
    print(f"  Technical Signal: {context.technical_signal or 'N/A'}")
    print(f"  Agreement Score: {agree_str}")
    print(f"  Confidence: {conf_str}")


def demo_inot_enabled():
    """Demo with INoT enabled"""
    print("\n" + "=" * 60)
    print("INOT ENGINE ENABLED")
    print("=" * 60)

    # Initialize engine with INoT enabled
    config = {
        "inot": {
            "enabled": True,
            "model_version": "claude-sonnet-4-test",
            "temperature": 0.0,
            "max_tokens": 4000,
            "max_daily_cost": 5.0,
            "calibration_path": "data/inot_calibration.json"
        },
        "tools": {
            "rsi_period": 14,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9
        }
    }

    engine = TradingDecisionEngine(config)

    # Mock price data (oversold)
    prices = [1.0900 - i * 0.0002 for i in range(100)]  # Declining

    # Analyze market
    context = engine.analyze_market("EURUSD", prices)

    print("\n📊 MARKET ANALYSIS:")
    print(f"  Symbol: {context.symbol}")
    print(f"  Price: {context.price:.5f}")
    print(f"  RSI: {context.rsi:.2f} ({context.rsi_signal})")
    print(f"  Technical Signal: {context.technical_signal}")

    # Make decision with INoT
    decision = engine.decide(context)

    print("\n🧠 INOT DECISION:")
    print(f"  Action: {decision.action}")
    print(f"  Lots: {decision.lots}")
    print(f"  Stop Loss: {decision.stop_loss}")
    print(f"  Confidence: {decision.confidence:.2f}")
    print(f"  Vetoed: {decision.vetoed}")
    print(f"  Reasoning: {decision.reasoning[:100]}...")

    if decision.agent_outputs:
        print("\n📋 AGENT OUTPUTS:")
        for agent_output in decision.agent_outputs:
            agent = agent_output.get('agent', 'Unknown')
            confidence = agent_output.get('confidence', 0.0)
            print(f"  - {agent}: confidence={confidence:.2f}")


def demo_fallback_behavior():
    """Demo fallback to rules when INoT fails"""
    print("\n" + "=" * 60)
    print("FALLBACK BEHAVIOR (RULES)")
    print("=" * 60)

    # Initialize engine (INoT disabled for this demo)
    config = {
        "inot": {"enabled": False},
        "tools": {}
    }

    engine = TradingDecisionEngine(config)

    # Mock price data (overbought)
    prices = [1.0800 + i * 0.0003 for i in range(100)]  # Rising fast

    # Analyze market
    context = engine.analyze_market("EURUSD", prices)

    print("\n📊 MARKET ANALYSIS:")
    print(f"  RSI: {context.rsi:.2f} ({context.rsi_signal})")

    # Make decision (fallback to rules)
    decision = engine.decide(context)

    print("\n📐 RULE-BASED DECISION:")
    print(f"  Action: {decision.action}")
    print(f"  Lots: {decision.lots}")
    print(f"  Confidence: {decision.confidence:.2f}")
    print(f"  Reasoning: {decision.reasoning}")


def demo_tool_stack_only():
    """Demo tool stack without INoT"""
    print("\n" + "=" * 60)
    print("TOOL STACK ONLY (NO INOT)")
    print("=" * 60)

    config = {
        "inot": {"enabled": False},
        "tools": {}
    }

    engine = TradingDecisionEngine(config)

    # Test different market conditions
    scenarios = [
        ("Oversold", [1.0900 - i * 0.0002 for i in range(100)]),
        ("Overbought", [1.0800 + i * 0.0003 for i in range(100)]),
        ("Neutral", [1.0850 + (i % 10) * 0.0001 for i in range(100)]),
    ]

    print("\n📊 TESTING SCENARIOS:")
    for name, prices in scenarios:
        context = engine.analyze_market("EURUSD", prices)
        print(f"\n  {name}:")
        print(f"    RSI: {context.rsi:.2f} ({context.rsi_signal})")
        print(f"    MACD: {context.macd_signal}")
        print(f"    BB: {context.bb_signal}")
        print(f"    Technical: {context.technical_signal} (conf: {context.technical_confidence:.2f})")


def main():
    """Run all demos"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 12 + "INOT ENGINE INTEGRATION DEMO" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")

    demo_basic_integration()
    demo_inot_enabled()
    demo_fallback_behavior()
    demo_tool_stack_only()

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\n✅ INoT Engine Integration:")
    print("  - Tool stack analysis: ✅")
    print("  - INoT multi-agent reasoning: ✅")
    print("  - Fallback to rules: ✅")
    print("  - Mock LLM client: ✅")
    print("\n📝 Next Steps:")
    print("  1. Replace mock LLM with real Anthropic/OpenAI client")
    print("  2. Add memory persistence")
    print("  3. Integrate with GenerateOrder for execution")
    print("  4. Add confidence calibration tracking")
    print()


if __name__ == '__main__':
    main()
