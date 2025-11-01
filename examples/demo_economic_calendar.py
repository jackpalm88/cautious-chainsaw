"""
Demo: Economic Calendar v2.0
Demonstrates economic event scheduling, impact scoring, and pre-event risk management
"""

import asyncio
from datetime import datetime, timedelta

from src.trading_agent.input_fusion import (
    EconomicCalendarStream,
    EventImpactScorer,
    EventNormalizer,
    InputFusionEngine,
    NormalizedEvent,
    PreEventRiskManager,
    PriceStream,
)


async def demo_event_normalizer():
    """Demo: Event normalization from multiple sources"""
    print("\n" + "=" * 70)
    print("1️⃣  EVENT NORMALIZER DEMO")
    print("=" * 70)

    normalizer = EventNormalizer()

    # ForexFactory format
    raw_ff = {
        "title": "US Non-Farm Payrolls",
        "country": "USD",
        "date": "2025-11-07",
        "time": "13:30",
        "impact": "High",
        "forecast": "150K",
        "previous": "142K",
        "id": "ff_nfp_001",
    }

    normalized_ff = normalizer.normalize_forexfactory(raw_ff)

    print("\n📰 FOREXFACTORY NORMALIZATION:")
    print(f"  Title: {normalized_ff.title}")
    print(f"  Currency: {normalized_ff.currency}")
    print(f"  Impact: {normalized_ff.impact}")
    print(f"  Category: {normalized_ff.category}")
    print(f"  Scheduled: {normalized_ff.scheduled_time}")
    print(f"  Forecast: {normalized_ff.forecast}")
    print(f"  Previous: {normalized_ff.previous}")
    print(f"  Affected Symbols: {', '.join(normalized_ff.affected_symbols[:5])}")

    # TradingEconomics format
    raw_te = {
        "Event": "FOMC Interest Rate Decision",
        "Country": "United States",
        "Date": "2025-11-08T19:00:00",
        "Importance": 3,
        "Forecast": "5.25%",
        "Previous": "5.25%",
    }

    normalized_te = normalizer.normalize_tradingeconomics(raw_te)

    print("\n📊 TRADINGECONOMICS NORMALIZATION:")
    print(f"  Title: {normalized_te.title}")
    print(f"  Currency: {normalized_te.currency}")
    print(f"  Impact: {normalized_te.impact}")
    print(f"  Category: {normalized_te.category}")


async def demo_impact_scorer():
    """Demo: Event impact scoring"""
    print("\n" + "=" * 70)
    print("2️⃣  IMPACT SCORER DEMO")
    print("=" * 70)

    scorer = EventImpactScorer()

    # Create test events
    events = [
        NormalizedEvent(
            title="US Non-Farm Payrolls",
            country="USD",
            currency="USD",
            scheduled_time=datetime.utcnow() + timedelta(hours=2),
            impact="HIGH",
            source="test",
            category="employment",
            forecast="150K",
            previous="142K",
        ),
        NormalizedEvent(
            title="FOMC Interest Rate Decision",
            country="USD",
            currency="USD",
            scheduled_time=datetime.utcnow() + timedelta(hours=4),
            impact="HIGH",
            source="test",
            category="interest_rate",
            forecast="5.25%",
            previous="5.25%",
        ),
        NormalizedEvent(
            title="US Consumer Price Index",
            country="USD",
            currency="USD",
            scheduled_time=datetime.utcnow() + timedelta(hours=6),
            impact="HIGH",
            source="test",
            category="inflation",
            forecast="3.5%",
            previous="3.0%",
        ),
        NormalizedEvent(
            title="US Retail Sales",
            country="USD",
            currency="USD",
            scheduled_time=datetime.utcnow() + timedelta(hours=8),
            impact="MEDIUM",
            source="test",
            category="retail",
            forecast="0.3%",
            previous="0.1%",
        ),
        NormalizedEvent(
            title="US Trade Balance",
            country="USD",
            currency="USD",
            scheduled_time=datetime.utcnow() + timedelta(hours=10),
            impact="LOW",
            source="test",
            category="trade",
        ),
    ]

    # Score events
    scored = scorer.score_multiple_events(events)

    print("\n💯 IMPACT SCORES:")
    print(f"{'Event Title':<40} {'Impact':<10} {'Score':<10} {'Level':<10}")
    print("-" * 70)

    for event, score in scored:
        level = scorer.get_impact_level(score)
        title_short = event.title[:37] + "..." if len(event.title) > 37 else event.title
        print(f"{title_short:<40} {event.impact:<10} {score:<10.3f} {level:<10}")

    # Get high impact events
    high_impact = scorer.get_high_impact_events(events)

    print(f"\n🔴 HIGH IMPACT EVENTS ({len(high_impact)}):")
    for event in high_impact:
        print(f"  - {event.title}")


async def demo_risk_manager():
    """Demo: Pre-event risk management"""
    print("\n" + "=" * 70)
    print("3️⃣  PRE-EVENT RISK MANAGER DEMO")
    print("=" * 70)

    manager = PreEventRiskManager()

    # Create test events at different proximities
    test_scenarios = [
        ("5 minutes before HIGH impact", 5, "HIGH"),
        ("15 minutes before HIGH impact", 15, "HIGH"),
        ("1 hour before HIGH impact", 60, "HIGH"),
        ("4 hours before HIGH impact", 240, "HIGH"),
        ("1 hour before MEDIUM impact", 60, "MEDIUM"),
        ("1 hour before LOW impact", 60, "LOW"),
    ]

    print("\n⚠️  CONFIDENCE ADJUSTMENTS:")
    print(f"{'Scenario':<35} {'Base':<8} {'Adjusted':<10} {'Risk Level':<12}")
    print("-" * 70)

    base_confidence = 0.80

    for scenario, minutes, impact in test_scenarios:
        event = NormalizedEvent(
            title=f"Test {impact} Event",
            country="USD",
            currency="USD",
            scheduled_time=datetime.utcnow() + timedelta(minutes=minutes),
            impact=impact,
            source="test",
            impact_score=0.9 if impact == "HIGH" else 0.5,
            affected_symbols=["EURUSD"],
        )

        adjusted, info = manager.apply_risk_adjustment(base_confidence, [event])

        print(
            f"{scenario:<35} {base_confidence:<8.2f} {adjusted:<10.2f} {info['risk_level']:<12}"
        )

    # Trading halt decision
    print("\n🛑 TRADING HALT DECISIONS:")

    halt_scenarios = [
        ("3 minutes before HIGH impact", 3, "HIGH"),
        ("10 minutes before HIGH impact", 10, "HIGH"),
        ("1 hour before HIGH impact", 60, "HIGH"),
        ("15 minutes before MEDIUM impact", 15, "MEDIUM"),
    ]

    for scenario, minutes, impact in halt_scenarios:
        event = NormalizedEvent(
            title=f"Test {impact} Event",
            country="USD",
            currency="USD",
            scheduled_time=datetime.utcnow() + timedelta(minutes=minutes),
            impact=impact,
            source="test",
        )

        should_halt, reason = manager.should_halt_trading([event])

        status = "🛑 HALT" if should_halt else "✅ CONTINUE"
        print(f"  {scenario:<35} {status}")
        if reason:
            print(f"    Reason: {reason}")

    # Position size adjustment
    print("\n📊 POSITION SIZE ADJUSTMENTS:")

    for scenario, minutes, impact in test_scenarios[:4]:
        event = NormalizedEvent(
            title=f"Test {impact} Event",
            country="USD",
            currency="USD",
            scheduled_time=datetime.utcnow() + timedelta(minutes=minutes),
            impact=impact,
            source="test",
        )

        adjustment = manager.get_position_size_adjustment([event])

        print(f"  {scenario:<35} {adjustment * 100:>5.0f}% of normal size")


async def demo_calendar_stream():
    """Demo: Economic calendar stream with Input Fusion"""
    print("\n" + "=" * 70)
    print("4️⃣  ECONOMIC CALENDAR STREAM + INPUT FUSION DEMO")
    print("=" * 70)

    # Create streams
    symbols = ["EURUSD", "GBPUSD"]

    price_stream1 = PriceStream(symbol="EURUSD", mode="mock", update_interval_ms=500)
    price_stream2 = PriceStream(symbol="GBPUSD", mode="mock", update_interval_ms=500)
    calendar_stream = EconomicCalendarStream(
        symbols=symbols,
        mode="mock",
        check_interval_s=2,  # Check every 2 seconds
        proximity_window_h=12,  # Look 12 hours ahead
    )

    # Create fusion engine
    engine = InputFusionEngine(
        buffer_capacity=1000,
    )

    # Add streams
    engine.add_stream(price_stream1)
    engine.add_stream(price_stream2)
    engine.add_stream(calendar_stream)

    print("\n🔄 Starting Input Fusion with Economic Calendar...")
    print(f"  Symbols: {', '.join(symbols)}")
    print("  Streams: 2 price + 1 calendar")
    print("  Calendar Check Interval: 2s")

    # Start engine
    await engine.start()

    # Fetch calendar
    await calendar_stream._fetch_daily_calendar()

    # Get upcoming events
    upcoming = calendar_stream.get_upcoming_events(hours_ahead=12)

    print(f"\n📅 UPCOMING EVENTS ({len(upcoming)}):")
    for event in upcoming[:5]:  # Show first 5
        time_to_event = (event.scheduled_time - datetime.utcnow()).total_seconds() / 3600
        print(f"  {event.title:<40} {event.impact:<8} in {time_to_event:.1f}h")

    # Run for 3 seconds
    print("\n⏳ Collecting data for 3 seconds...")
    await asyncio.sleep(3)

    # Stop engine
    await engine.stop()

    # Get statistics
    stats = engine.get_stats()

    print("\n📊 FUSION STATISTICS:")
    print(f"  Total Fusions: {stats['fusion_count']}")
    print(f"  Active Streams: {stats['stream_count']}")
    print(f"  Sync Window: {stats['sync_window_ms']}ms")
    print(f"  Memory Usage: {stats['memory']['total_mb']:.2f} MB")

    # Get latest snapshot
    snapshot = engine.get_latest_snapshot()

    if snapshot:
        print("\n📸 LATEST FUSED SNAPSHOT:")
        print(f"  Timestamp: {snapshot.timestamp.strftime('%H:%M:%S.%f')[:-3]}")
        print(f"  Streams: {len(snapshot.data)}")

        # Show prices
        print("\n  💱 PRICES:")
        for stream_id, data in snapshot.data.items():
            if "price" in stream_id:
                symbol = data.get("symbol", "Unknown")
                bid = data.get("bid", 0)
                ask = data.get("ask", 0)
                spread = data.get("spread", 0)
                print(
                    f"    {symbol:<8} Bid: {bid:.5f}  Ask: {ask:.5f}  Spread: {spread:.5f}"
                )

        # Show economic events
        print("\n  📅 ECONOMIC EVENTS:")
        for stream_id, data in snapshot.data.items():
            if "economic" in stream_id:
                title = data.get("title", "No title")
                impact = data.get("impact", "UNKNOWN")
                time_to_event = data.get("time_to_event_minutes", 0)

                print(f"    Title: {title[:50]}...")
                print(f"    Impact: {impact}")
                print(f"    Time to Event: {time_to_event:.1f} minutes")

    # Demo risk management with upcoming events
    if upcoming:
        print("\n⚠️  RISK MANAGEMENT DEMO:")

        manager = PreEventRiskManager()
        scorer = EventImpactScorer()

        # Score events
        for event in upcoming[:3]:
            score = scorer.calculate_impact_score(event)
            event.impact_score = score

        # Apply risk adjustment
        base_confidence = 0.85
        adjusted, info = manager.apply_risk_adjustment(base_confidence, upcoming[:3])

        print(f"  Base Confidence: {base_confidence:.2f}")
        print(f"  Adjusted Confidence: {adjusted:.2f}")
        print(f"  Risk Level: {info['risk_level']}")

        if "nearest_event" in info:
            nearest = info["nearest_event"]
            print("\n  Nearest Event:")
            print(f"    Title: {nearest['title']}")
            print(f"    Impact: {nearest['impact']}")
            print(f"    Time to Event: {nearest['time_to_event_minutes']:.1f} minutes")

    # Close engine
    await engine.close()


async def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print("📅 ECONOMIC CALENDAR v2.0 DEMO")
    print("=" * 70)

    await demo_event_normalizer()
    await demo_impact_scorer()
    await demo_risk_manager()
    await demo_calendar_stream()

    print("\n" + "=" * 70)
    print("✅ Demo Complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
