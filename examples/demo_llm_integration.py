"""
Demo: LLM Integration with Anthropic Claude
Demonstrates real LLM integration for trading decisions
"""

import os

from src.trading_agent.llm import AnthropicLLMClient, LLMConfig


def demo_basic_completion():
    """Demo: Basic LLM completion"""
    print("\n" + "=" * 70)
    print("1️⃣  BASIC LLM COMPLETION DEMO")
    print("=" * 70)

    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n⚠️  ANTHROPIC_API_KEY not set. Skipping demo.")
        print("   Set it with: export ANTHROPIC_API_KEY='your_key_here'")
        return False

    try:
        # Create client
        client = AnthropicLLMClient(api_key=api_key)

        print(f"\n✅ Client initialized with model: {client.model}")

        # Simple completion
        prompt = "Hello Claude! Please confirm you're ready to help with trading analysis."

        print(f"\n📤 Sending prompt: {prompt[:50]}...")

        response = client.complete(prompt)

        print("\n📥 Response received:")
        print(f"  Content: {response.content[:200]}...")
        print(f"  Latency: {response.latency_ms:.1f}ms")
        print(f"  Tokens: {response.tokens_used}")
        print(f"  Model: {response.model_used}")
        print(f"  Confidence: {response.confidence:.2f}")

        return True

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


def demo_trading_decision():
    """Demo: Trading decision with LLM"""
    print("\n" + "=" * 70)
    print("2️⃣  TRADING DECISION DEMO")
    print("=" * 70)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n⚠️  ANTHROPIC_API_KEY not set. Skipping demo.")
        return False

    try:
        client = AnthropicLLMClient(api_key=api_key)

        # Create trading context
        context = {
            "symbol": "EURUSD",
            "prices": [1.0900, 1.0905, 1.0910, 1.0915, 1.0920, 1.0925, 1.0930],
            "indicators": {
                "RSI": 65.5,
                "MACD": 0.0012,
                "MACD_signal": 0.0008,
                "signal": "BULLISH",
            },
            "account_info": {
                "balance": 10000.0,
                "equity": 10000.0,
                "free_margin": 9000.0,
            },
        }

        # Available tools (empty for now)
        tools = []

        print("\n📊 MARKET CONTEXT:")
        print(f"  Symbol: {context['symbol']}")
        print(f"  Current Price: {context['prices'][-1]}")
        print("  Price Trend: Rising")
        print(f"  RSI: {context['indicators']['RSI']} (slightly overbought)")
        print(f"  MACD: {context['indicators']['MACD']} (bullish)")
        print(f"  Account Balance: ${context['account_info']['balance']}")

        print("\n🤖 Requesting trading decision from Claude...")

        decision = client.reason_with_tools(context, tools, "trading")

        print("\n💡 TRADING DECISION:")
        print(f"  Action: {decision.get('action', 'N/A')}")
        print(f"  Confidence: {decision.get('confidence', 0):.2f}")
        print(f"  Lots: {decision.get('lots', 0):.2f}")
        print(f"  Stop Loss: {decision.get('stop_loss', 'N/A')}")
        print(f"  Take Profit: {decision.get('take_profit', 'N/A')}")

        print("\n📝 REASONING:")
        reasoning = decision.get("reasoning", "No reasoning provided")
        # Wrap reasoning text
        for i in range(0, len(reasoning), 60):
            print(f"  {reasoning[i:i+60]}")

        if "llm_metadata" in decision:
            metadata = decision["llm_metadata"]
            print("\n📈 LLM METADATA:")
            print(f"  Model: {metadata.get('model', 'N/A')}")
            print(f"  Latency: {metadata.get('latency_ms', 0):.1f}ms")
            print(f"  Tokens: {metadata.get('tokens_used', 0)}")
            print(f"  LLM Confidence: {metadata.get('llm_confidence', 0):.2f}")

        return True

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


def demo_multiple_scenarios():
    """Demo: Multiple trading scenarios"""
    print("\n" + "=" * 70)
    print("3️⃣  MULTIPLE SCENARIOS DEMO")
    print("=" * 70)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n⚠️  ANTHROPIC_API_KEY not set. Skipping demo.")
        return False

    try:
        client = AnthropicLLMClient(api_key=api_key)

        scenarios = [
            {
                "name": "Trending Up",
                "context": {
                    "symbol": "GBPUSD",
                    "prices": [1.2500, 1.2510, 1.2520, 1.2530, 1.2540],
                    "indicators": {"RSI": 55, "MACD": 0.0020},
                    "account_info": {"balance": 10000.0},
                },
            },
            {
                "name": "Trending Down",
                "context": {
                    "symbol": "USDJPY",
                    "prices": [150.00, 149.80, 149.60, 149.40, 149.20],
                    "indicators": {"RSI": 35, "MACD": -0.0030},
                    "account_info": {"balance": 10000.0},
                },
            },
            {
                "name": "Sideways",
                "context": {
                    "symbol": "EURUSD",
                    "prices": [1.0900, 1.0905, 1.0900, 1.0895, 1.0900],
                    "indicators": {"RSI": 50, "MACD": 0.0001},
                    "account_info": {"balance": 10000.0},
                },
            },
        ]

        print(f"\n🎯 Testing {len(scenarios)} market scenarios...")

        results = []

        for i, scenario in enumerate(scenarios, 1):
            print(f"\n  Scenario {i}: {scenario['name']}")
            print(f"  Symbol: {scenario['context']['symbol']}")
            print(f"  Prices: {scenario['context']['prices']}")

            decision = client.reason_with_tools(scenario["context"], [], "trading")

            action = decision.get("action", "HOLD")
            confidence = decision.get("confidence", 0)

            print(f"  → Decision: {action} (confidence: {confidence:.2f})")

            results.append(
                {
                    "scenario": scenario["name"],
                    "action": action,
                    "confidence": confidence,
                }
            )

        print("\n📊 SUMMARY:")
        print(f"{'Scenario':<20} {'Action':<10} {'Confidence':<12}")
        print("-" * 42)
        for result in results:
            print(
                f"{result['scenario']:<20} {result['action']:<10} {result['confidence']:<12.2f}"
            )

        return True

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


def demo_configuration():
    """Demo: LLM configuration options"""
    print("\n" + "=" * 70)
    print("4️⃣  CONFIGURATION DEMO")
    print("=" * 70)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n⚠️  ANTHROPIC_API_KEY not set. Skipping demo.")
        return False

    try:
        # Create custom configuration
        config = LLMConfig(
            api_key=api_key,
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            temperature=0.0,  # Deterministic for trading
            timeout_seconds=30,
        )

        print("\n⚙️  CONFIGURATION:")
        print(f"  Model: {config.model}")
        print(f"  Max Tokens: {config.max_tokens}")
        print(f"  Temperature: {config.temperature}")
        print(f"  Timeout: {config.timeout_seconds}s")

        # Create client with custom config
        client = AnthropicLLMClient(
            api_key=config.api_key,
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        )

        print("\n✅ Client created with custom configuration")

        # Test with simple prompt
        response = client.complete("Quick test: Is EURUSD at 1.0950 a good buy?")

        print("\n📥 Response:")
        print(f"  Content: {response.content[:100]}...")
        print(f"  Tokens: {response.tokens_used}")
        print(f"  Latency: {response.latency_ms:.1f}ms")

        return True

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print("🤖 LLM INTEGRATION DEMO")
    print("=" * 70)

    # Check API key first
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n⚠️  ANTHROPIC_API_KEY environment variable not set!")
        print("\n📝 To run this demo:")
        print("  1. Get API key from: https://console.anthropic.com/")
        print("  2. Set environment variable:")
        print("     export ANTHROPIC_API_KEY='your_key_here'")
        print("  3. Run demo again")
        print("\n" + "=" * 70)
        return

    print(f"\n✅ API key found: {api_key[:10]}...{api_key[-4:]}")

    # Run demos
    results = []

    results.append(("Basic Completion", demo_basic_completion()))
    results.append(("Trading Decision", demo_trading_decision()))
    results.append(("Multiple Scenarios", demo_multiple_scenarios()))
    results.append(("Configuration", demo_configuration()))

    # Summary
    print("\n" + "=" * 70)
    print("📊 DEMO SUMMARY")
    print("=" * 70)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {name:<25} {status}")

    success_rate = sum(1 for _, s in results if s) / len(results)
    print(f"\n  Success Rate: {success_rate * 100:.0f}%")

    print("\n" + "=" * 70)
    print("✅ Demo Complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
