"""
INoT + InputFusionEngine Full Integration Demo

Demonstrates INoT's TRUE VALUE: Multi-agent reasoning with ALL data sources:
- Technical indicators (RSI, MACD, ATR, etc.)
- NewsStream (sentiment + relevance scoring)
- Economic Calendar (events + impact + proximity warnings)
- Custom context (regime, correlations, etc.)

This shows why INoT > simple prompts: Sophisticated multi-source integration!

Run with: ANTHROPIC_API_KEY=xxx python examples/demo_inot_full_integration.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trading_agent.inot_engine.orchestrator import INoTOrchestrator
from trading_agent.inot_engine.validator import INoTValidator
from trading_agent.input_fusion.economic_calendar_stream import EconomicCalendarStream
from trading_agent.input_fusion.engine import InputFusionEngine
from trading_agent.input_fusion.news_stream import NewsStream
from trading_agent.input_fusion.price_stream import PriceStream
from trading_agent.llm import create_inot_adapter


class MockMemory:
    """Mock memory for demo"""
    def to_summary(self, max_tokens=600):
        return """Recent Performance (Last 30 days):
- Total trades: 45 (28W/17L = 62% win rate)
- Avg profit: +15 pips, Avg loss: -10 pips
- Best setups: RSI oversold + bullish MACD (75% win rate)
- Worst setups: Low volatility ranges (35% win rate)

Key Learnings:
- Economic calendar HIGH impact events: Avoid trading 1h before/after
- NewsStream sentiment >0.7: Improves win rate by 18%
- ATR < 0.0010: Poor performance, avoid entry
- Risk veto prevented 8 major losses (saved ~320 pips)
- Contrarian plays (RSI extremes): 68% win rate when news supports

Current Streak: 5 wins in a row (+78 pips)
"""


def create_full_fusion_context(symbol="EURUSD"):
    """
    Create FusedSnapshot with ALL 4 data streams.
    This demonstrates INoT's multi-source integration capability.
    """
    print("\n" + "="*70)
    print("CREATING FUSED CONTEXT WITH ALL 4 DATA STREAMS")
    print("="*70)

    # Initialize 3 streams (price includes indicators)
    price_stream = PriceStream(symbol=symbol, mode="mock")
    news_stream = NewsStream(symbols=[symbol], mode="mock")
    calendar_stream = EconomicCalendarStream(symbols=[symbol], mode="mock")

    # Create InputFusionEngine
    fusion = InputFusionEngine()
    fusion.register_stream("price", price_stream)  # Includes indicators (RSI, MACD, ATR)
    fusion.register_stream("news", news_stream)
    fusion.register_stream("calendar", calendar_stream)

    # Fetch fused snapshot
    print(f"\n📊 Fetching fused data for {symbol}...")
    snapshot = fusion.get_fused_snapshot(symbol)

    # Display what we got
    print("\n✅ Fused Snapshot Created!")
    print("\n1️⃣ PRICE DATA:")
    print(f"   Symbol: {snapshot.symbol}")
    print(f"   Price: {snapshot.price:.4f}")
    print(f"   Timestamp: {snapshot.timestamp}")

    print("\n2️⃣ TECHNICAL INDICATORS:")
    print(f"   RSI(14): {snapshot.rsi:.1f}")
    print(f"   MACD: {snapshot.macd:+.4f} (Signal: {snapshot.macd_signal:+.4f})")
    print(f"   ATR: {snapshot.atr:.5f}")
    print(f"   Volume: {snapshot.volume}")

    print("\n3️⃣ NEWS SENTIMENT:")
    print(f"   Latest: \"{snapshot.latest_news[:80]}...\"")
    print(f"   Sentiment: {snapshot.sentiment:+.2f} (-1=bearish, +1=bullish)")

    print("\n4️⃣ ECONOMIC CALENDAR:")
    if hasattr(snapshot, 'upcoming_events') and snapshot.upcoming_events:
        print(f"   Upcoming events: {len(snapshot.upcoming_events)}")
        for event in snapshot.upcoming_events[:3]:
            print(f"   - {event.get('title', 'Unknown')} ({event.get('impact', 'N/A')} impact)")
    else:
        print("   No high-impact events in next 24h")

    print("\n5️⃣ FUSION METADATA:")
    if hasattr(snapshot, 'confidence'):
        print(f"   Confidence: {snapshot.confidence:.2f}")
    if hasattr(snapshot, 'stream_data'):
        print(f"   Streams: {len(snapshot.stream_data)} active")
    if hasattr(snapshot, 'fusion_latency_ms'):
        print(f"   Latency: {snapshot.fusion_latency_ms:.1f}ms")

    return snapshot


def demo_1_full_integration():
    """Demo 1: INoT with full InputFusion integration"""
    print("\n" + "="*70)
    print("DEMO 1: INoT + InputFusion (ALL 4 DATA STREAMS)")
    print("="*70)

    # Create fused context
    snapshot = create_full_fusion_context("EURUSD")

    # Convert to FusedContext for INoT
    from trading_agent.decision.engine import FusedContext
    context = FusedContext(
        symbol=snapshot.symbol,
        price=snapshot.price,
        timestamp=snapshot.timestamp,
        rsi=snapshot.rsi,
        macd=snapshot.macd,
        macd_signal=snapshot.macd_signal,
        atr=snapshot.atr,
        volume=snapshot.volume,
        latest_news=snapshot.latest_news,
        sentiment=snapshot.sentiment,
        current_position=None,
        unrealized_pnl=0.0,
        account_equity=10000.0,
        free_margin=9500.0
    )

    # Add economic calendar data
    if hasattr(snapshot, 'upcoming_events'):
        context.upcoming_events = snapshot.upcoming_events

    # Create INoT orchestrator with Claude
    print("\n🧠 Initializing INoT with Claude API...")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set!")
        return

    adapter = create_inot_adapter(
        api_key=api_key,
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        temperature=0.0
    )

    schema_path = Path(__file__).parent.parent / "src" / "trading_agent" / "inot_engine" / "schemas" / "inot_agents.schema.json"
    validator = INoTValidator(schema_path)

    orchestrator = INoTOrchestrator(
        llm_client=adapter,
        config={
            "model_version": "claude-sonnet-4-20250514",
            "temperature": 0.0,
            "max_tokens": 4000
        },
        validator=validator
    )

    # Get decision
    memory = MockMemory()
    print("\n🎯 Calling INoT with FULL multi-source context...")
    print("   (This will take 10-15 seconds...)")

    decision = orchestrator.reason(context, memory)

    # Display decision
    print("\n" + "="*70)
    print("DECISION FROM INoT (4 AGENTS + FULL DATA)")
    print("="*70)
    print(f"\n🎯 ACTION: {decision.action}")
    print(f"📊 LOTS: {decision.lots:.2f}")
    print(f"💯 CONFIDENCE: {decision.confidence:.2f}")

    if decision.action in ["BUY", "SELL"]:
        print(f"📍 ENTRY: {decision.entry_price:.4f}")
        print(f"🛑 STOP LOSS: {decision.stop_loss:.4f}")
        print(f"🎯 TAKE PROFIT: {decision.take_profit:.4f}")

        # Calculate R:R
        sl_dist = abs(decision.stop_loss - decision.entry_price)
        tp_dist = abs(decision.take_profit - decision.entry_price)
        rr_ratio = tp_dist / sl_dist if sl_dist > 0 else 0
        print(f"⚖️ RISK:REWARD: 1:{rr_ratio:.1f}")

    if decision.vetoed:
        print(f"🚫 VETOED: {decision.veto_reason}")

    print("\n💭 REASONING:")
    print(f"   {decision.reasoning[:300]}...")

    # Show agent breakdown
    if decision.agent_outputs:
        print("\n🤖 AGENT BREAKDOWN:")
        for agent in decision.agent_outputs:
            agent_name = agent.get("agent", "Unknown")
            print(f"\n   [{agent_name}]")

            if agent_name == "Signal":
                print(f"   Action: {agent.get('action')}")
                print(f"   Confidence: {agent.get('confidence'):.2f}")
                print(f"   Factors: {', '.join(agent.get('key_factors', [])[:3])}")

            elif agent_name == "Risk":
                print(f"   Approved: {agent.get('approved')}")
                print(f"   Confidence: {agent.get('confidence'):.2f}")
                if not agent.get('approved'):
                    print(f"   Veto Reason: {agent.get('veto_reason')}")

            elif agent_name == "Context":
                print(f"   Regime: {agent.get('regime')}")
                print(f"   Regime Confidence: {agent.get('regime_confidence'):.2f}")
                print(f"   News Alignment: {agent.get('news_alignment')}")

            elif agent_name == "Synthesis":
                weights = agent.get('agent_weights_applied', {})
                print(f"   Weights: Signal={weights.get('Signal', 1.0):.1f}, "
                      f"Risk={weights.get('Risk', 1.0):.1f}, "
                      f"Context={weights.get('Context', 1.0):.1f}")

    print("\n" + "="*70)
    print("✅ Demo 1 Complete!")
    print("="*70)

    return decision


def demo_2_compare_with_without_fusion():
    """Demo 2: Compare INoT with vs without InputFusion"""
    print("\n" + "="*70)
    print("DEMO 2: INoT VALUE COMPARISON")
    print("="*70)

    print("\n📊 WITHOUT InputFusion:")
    print("   - Single data source (price only)")
    print("   - No news sentiment")
    print("   - No economic calendar awareness")
    print("   - Limited context")
    print("   → Simple trend-following decisions")

    print("\n📊 WITH InputFusion (INoT's TRUE POWER):")
    print("   - 3 data streams (price+indicators + news + calendar)")
    print("   - Real-time sentiment analysis")
    print("   - Economic event proximity warnings")
    print("   - Rich multi-dimensional context")
    print("   → Sophisticated multi-factor decisions")

    print("\n🎯 INoT Advantages:")
    print("   1. Multi-agent specialization (Signal, Risk, Context, Synthesis)")
    print("   2. Full data integration (price+indicators + news + calendar)")
    print("   3. Sophisticated reasoning (contrarian plays, regime detection)")
    print("   4. Memory-based learning (past performance informs future)")
    print("   5. Risk management (veto power, position sizing)")

    print("\n✅ Demo 2 Complete!")


def main():
    """Main demo runner"""
    print("\n" + "="*70)
    print("INoT + InputFusion FULL INTEGRATION DEMO")
    print("="*70)
    print("\nThis demo shows INoT's TRUE VALUE:")
    print("- Multi-agent reasoning with ALL data sources")
    print("- Sophisticated decision-making beyond simple prompts")
    print("- Real-world trading intelligence")

    # Check API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n❌ ERROR: ANTHROPIC_API_KEY not set!")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        return

    # Run demos
    try:
        demo_1_full_integration()

        print("\n" + "-"*70)
        input("\nPress Enter to continue to Demo 2...")

        demo_2_compare_with_without_fusion()

    except KeyboardInterrupt:
        print("\n\n❌ Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70)
    print("ALL DEMOS COMPLETE!")
    print("="*70)
    print("\n💡 Key Takeaway:")
    print("   INoT's value = Multi-agent reasoning + Full data integration")
    print("   This enables sophisticated decisions impossible with simple prompts!")
    print("\n🚀 Next: Add persistent memory (SQLite) for continuous learning!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
