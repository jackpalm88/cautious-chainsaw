"""
Demo: INoT + Claude Integration
Demonstrates INoT multi-agent reasoning with real Claude API
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from trading_agent.inot_engine.orchestrator import INoTOrchestrator
from trading_agent.inot_engine.validator import INoTValidator
from trading_agent.llm import create_inot_adapter
from trading_agent.decision.engine import FusedContext
from datetime import datetime


def create_mock_context(scenario: str) -> FusedContext:
    """Create mock market context for testing"""
    
    if scenario == "bullish":
        return FusedContext(
            symbol="EURUSD",
            price=1.0950,
            timestamp=datetime.now(),
            rsi=68.5,  # Overbought territory
            macd=0.0015,  # Positive
            macd_signal=0.0010,  # Bullish crossover
            atr=0.0012,
            volume=1000,
            latest_news="ECB signals dovish stance, USD weakens",
            sentiment=0.6,  # Positive
            current_position=None,
            unrealized_pnl=0.0,
            account_equity=10000.0,
            free_margin=9500.0
        )
    
    elif scenario == "bearish":
        return FusedContext(
            symbol="EURUSD",
            price=1.0850,
            timestamp=datetime.now(),
            rsi=32.0,  # Oversold
            macd=-0.0018,  # Negative
            macd_signal=-0.0012,  # Bearish crossover
            atr=0.0015,
            volume=1200,
            latest_news="Fed hints at rate hikes, EUR under pressure",
            sentiment=-0.7,  # Negative
            current_position=None,
            unrealized_pnl=0.0,
            account_equity=10000.0,
            free_margin=9500.0
        )
    
    else:  # sideways
        return FusedContext(
            symbol="EURUSD",
            price=1.0900,
            timestamp=datetime.now(),
            rsi=50.0,  # Neutral
            macd=0.0002,  # Near zero
            macd_signal=0.0001,  # Weak signal
            atr=0.0008,  # Low volatility
            volume=800,
            latest_news="Markets await economic data",
            sentiment=0.0,  # Neutral
            current_position=None,
            unrealized_pnl=0.0,
            account_equity=10000.0,
            free_margin=9500.0
        )


class MockMemory:
    """Mock memory snapshot for demo"""
    def to_summary(self, max_tokens=1000):
        return """
Recent Performance:
- Last 5 trades: 3 wins, 2 losses (60% win rate)
- Avg profit: +12 pips per win
- Avg loss: -8 pips per loss
- Best setup: RSI oversold + bullish MACD crossover

Key Learnings:
- Avoid trading during low volatility (ATR < 0.0010)
- Strong news sentiment improves win rate by 15%
- Risk veto prevented 2 major losses last week
"""


def demo_basic_integration():
    """Demo 1: Basic INoT + Claude integration"""
    print("=" * 70)
    print("DEMO 1: BASIC INOT + CLAUDE INTEGRATION")
    print("=" * 70)
    
    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set!")
        print("   Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        return
    
    print("✅ API key found")
    
    # Create adapter
    print("\n1️⃣ Creating INoT adapter...")
    adapter = create_inot_adapter(
        api_key=api_key,
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        temperature=0.0
    )
    print("✅ Adapter created")
    
    # Create validator
    print("\n2️⃣ Creating INoT validator...")
    schema_path = Path(__file__).parent.parent / "src" / "trading_agent" / "inot_engine" / "schemas" / "inot_agents.schema.json"
    validator = INoTValidator(schema_path)
    print("✅ Validator created")
    
    # Create orchestrator
    print("\n3️⃣ Creating INoT orchestrator...")
    orchestrator = INoTOrchestrator(
        llm_client=adapter,  # ← Using real Claude via adapter!
        config={
            "model_version": "claude-sonnet-4-20250514",
            "temperature": 0.0,
            "max_tokens": 4000
        },
        validator=validator
    )
    print("✅ Orchestrator created with real Claude API")
    
    # Test with bullish scenario
    print("\n4️⃣ Testing with BULLISH market scenario...")
    context = create_mock_context("bullish")
    memory = MockMemory()
    
    print(f"\n📊 Market Context:")
    print(f"   Symbol: {context.symbol}")
    print(f"   Price: {context.price:.4f}")
    print(f"   RSI: {context.rsi:.1f} (overbought)")
    print(f"   MACD: {context.macd:.4f} (bullish crossover)")
    print(f"   Sentiment: {context.sentiment:+.1f} (positive)")
    print(f"   News: {context.latest_news}")
    
    print("\n🧠 Calling INoT with Claude API...")
    print("   (This will take 5-10 seconds...)")
    
    try:
        decision = orchestrator.reason(context, memory)
        
        print("\n✅ Decision received!")
        print(f"\n🎯 DECISION:")
        print(f"   Action: {decision.action}")
        print(f"   Lots: {decision.lots:.2f}")
        print(f"   Confidence: {decision.confidence:.2f}")
        print(f"   Entry: {decision.entry_price or 'N/A'}")
        print(f"   Stop Loss: {decision.stop_loss or 'N/A'}")
        print(f"   Take Profit: {decision.take_profit or 'N/A'}")
        print(f"   Vetoed: {decision.vetoed}")
        
        print(f"\n💭 Reasoning:")
        print(f"   {decision.reasoning[:200]}...")
        
        if decision.agent_outputs:
            print(f"\n🤖 Agent Outputs:")
            for agent in decision.agent_outputs:
                print(f"   - {agent.get('agent', 'Unknown')}: {agent.get('action', agent.get('regime', 'N/A'))}")
        
        print(f"\n✅ Demo 1 Complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def demo_multi_scenario():
    """Demo 2: Test multiple market scenarios"""
    print("\n" + "=" * 70)
    print("DEMO 2: MULTI-SCENARIO TESTING")
    print("=" * 70)
    
    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set!")
        return
    
    # Setup
    adapter = create_inot_adapter(api_key=api_key)
    schema_path = Path(__file__).parent.parent / "src" / "trading_agent" / "inot_engine" / "schemas" / "inot_agents.schema.json"
    validator = INoTValidator(schema_path)
    orchestrator = INoTOrchestrator(
        llm_client=adapter,
        config={"model_version": "claude-sonnet-4-20250514", "temperature": 0.0},
        validator=validator
    )
    
    scenarios = ["bullish", "bearish", "sideways"]
    results = []
    
    for scenario in scenarios:
        print(f"\n{'='*50}")
        print(f"Testing {scenario.upper()} scenario...")
        print('='*50)
        
        context = create_mock_context(scenario)
        memory = MockMemory()
        
        print(f"📊 RSI: {context.rsi:.1f}, MACD: {context.macd:+.4f}, Sentiment: {context.sentiment:+.1f}")
        print("🧠 Calling INoT...")
        
        try:
            decision = orchestrator.reason(context, memory)
            
            results.append({
                "scenario": scenario,
                "action": decision.action,
                "confidence": decision.confidence,
                "vetoed": decision.vetoed
            })
            
            print(f"✅ Action: {decision.action}, Confidence: {decision.confidence:.2f}, Vetoed: {decision.vetoed}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                "scenario": scenario,
                "action": "ERROR",
                "confidence": 0.0,
                "vetoed": False
            })
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print('='*70)
    print(f"\n{'Scenario':<15} {'Action':<10} {'Confidence':<12} {'Vetoed':<10}")
    print("-" * 50)
    for r in results:
        print(f"{r['scenario']:<15} {r['action']:<10} {r['confidence']:<12.2f} {r['vetoed']}")
    
    print(f"\n✅ Demo 2 Complete!")


def demo_risk_veto():
    """Demo 3: Risk veto scenario"""
    print("\n" + "=" * 70)
    print("DEMO 3: RISK VETO DEMONSTRATION")
    print("=" * 70)
    
    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set!")
        return
    
    # Setup
    adapter = create_inot_adapter(api_key=api_key)
    schema_path = Path(__file__).parent.parent / "src" / "trading_agent" / "inot_engine" / "schemas" / "inot_agents.schema.json"
    validator = INoTValidator(schema_path)
    orchestrator = INoTOrchestrator(
        llm_client=adapter,
        config={"model_version": "claude-sonnet-4-20250514", "temperature": 0.0},
        validator=validator
    )
    
    # Create high-risk scenario
    print("\n📊 Creating HIGH-RISK scenario...")
    context = FusedContext(
        symbol="EURUSD",
        price=1.0900,
        timestamp=datetime.now(),
        rsi=75.0,  # Extremely overbought
        macd=0.0025,  # Strong bullish
        macd_signal=0.0015,
        atr=0.0035,  # Very high volatility
        volume=2000,
        latest_news="BREAKING: Unexpected central bank announcement",
        sentiment=0.8,  # Very positive
        current_position="LONG 0.5 lots",  # Already in position
        unrealized_pnl=-50.0,  # Losing position
        account_equity=9500.0,  # Reduced equity
        free_margin=4000.0  # Low free margin
    )
    
    memory = MockMemory()
    
    print(f"   RSI: {context.rsi:.1f} (EXTREME overbought)")
    print(f"   ATR: {context.atr:.4f} (VERY HIGH volatility)")
    print(f"   Position: {context.current_position} (P&L: {context.unrealized_pnl:+.0f})")
    print(f"   Free Margin: ${context.free_margin:.0f} (LOW)")
    print(f"   News: {context.latest_news}")
    
    print("\n🧠 Calling INoT (expecting Risk veto)...")
    
    try:
        decision = orchestrator.reason(context, memory)
        
        print(f"\n🎯 DECISION:")
        print(f"   Action: {decision.action}")
        print(f"   Vetoed: {decision.vetoed}")
        if decision.vetoed:
            print(f"   Veto Reason: {decision.veto_reason}")
        print(f"   Reasoning: {decision.reasoning[:150]}...")
        
        if decision.vetoed:
            print(f"\n✅ Risk veto worked correctly!")
        else:
            print(f"\n⚠️ Expected veto but got: {decision.action}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print(f"\n✅ Demo 3 Complete!")


def main():
    """Run all demos"""
    print("\n" + "🚀" * 35)
    print("INoT + CLAUDE INTEGRATION DEMO")
    print("🚀" * 35)
    
    # Demo 1: Basic integration
    demo_basic_integration()
    
    # Demo 2: Multi-scenario
    if input("\n\nRun Demo 2 (Multi-Scenario)? [y/N]: ").lower() == 'y':
        demo_multi_scenario()
    
    # Demo 3: Risk veto
    if input("\n\nRun Demo 3 (Risk Veto)? [y/N]: ").lower() == 'y':
        demo_risk_veto()
    
    print("\n" + "=" * 70)
    print("ALL DEMOS COMPLETE!")
    print("=" * 70)
    print("\n💡 Next steps:")
    print("   1. Review decision quality and consistency")
    print("   2. Optimize prompts if needed (Phase 3)")
    print("   3. Run comprehensive tests (Phase 4)")
    print("   4. Deploy to production!")


if __name__ == "__main__":
    main()
