"""
Tests for Economic Calendar components
"""

import asyncio
from datetime import datetime, timedelta

import pytest

from src.trading_agent.input_fusion import (
    EconomicCalendarStream,
    EventImpactScorer,
    EventNormalizer,
    NormalizedEvent,
    PreEventRiskManager,
)


class TestEventNormalizer:
    """Test EventNormalizer"""

    def test_normalize_forexfactory(self):
        """Test ForexFactory normalization"""
        normalizer = EventNormalizer()

        raw = {
            "title": "US Non-Farm Payrolls",
            "country": "USD",
            "date": "2025-11-07",
            "time": "13:30",
            "impact": "High",
            "forecast": "150K",
            "previous": "142K",
            "id": "test_1",
        }

        normalized = normalizer.normalize_forexfactory(raw)

        assert normalized.title == "US Non-Farm Payrolls"
        assert normalized.currency == "USD"
        assert normalized.impact == "HIGH"
        assert normalized.forecast == "150K"
        assert normalized.previous == "142K"
        assert normalized.source == "forexfactory"
        assert normalized.category == "employment"
        assert "EURUSD" in normalized.affected_symbols

    def test_normalize_tradingeconomics(self):
        """Test TradingEconomics normalization"""
        normalizer = EventNormalizer()

        raw = {
            "Event": "Non Farm Payrolls",
            "Country": "United States",
            "Date": "2025-11-07T13:30:00",
            "Importance": 3,
            "Forecast": "150K",
            "Previous": "142K",
        }

        normalized = normalizer.normalize_tradingeconomics(raw)

        assert normalized.title == "Non Farm Payrolls"
        assert normalized.currency == "USD"
        assert normalized.impact == "HIGH"
        assert normalized.source == "tradingeconomics"

    def test_normalize_fxstreet(self):
        """Test FXStreet normalization"""
        normalizer = EventNormalizer()

        raw = {
            "name": "US Non-Farm Payrolls",
            "countryCode": "US",
            "dateUtc": "2025-11-07T13:30:00Z",
            "volatility": "High",
            "consensus": "150K",
            "previous": "142K",
        }

        normalized = normalizer.normalize_fxstreet(raw)

        assert normalized.title == "US Non-Farm Payrolls"
        assert normalized.currency == "USD"
        assert normalized.impact == "HIGH"
        assert normalized.source == "fxstreet"

    def test_categorize_event(self):
        """Test event categorization"""
        normalizer = EventNormalizer()

        # Test employment
        raw = {
            "title": "Non-Farm Employment Change",
            "country": "USD",
            "date": "2025-11-07",
            "time": "13:30",
            "impact": "High",
        }
        normalized = normalizer.normalize_forexfactory(raw)
        assert normalized.category == "employment"

        # Test inflation
        raw["title"] = "Consumer Price Index"
        normalized = normalizer.normalize_forexfactory(raw)
        assert normalized.category == "inflation"

        # Test interest rate
        raw["title"] = "FOMC Rate Decision"
        normalized = normalizer.normalize_forexfactory(raw)
        assert normalized.category == "interest_rate"


class TestEventImpactScorer:
    """Test EventImpactScorer"""

    def test_calculate_impact_score_nfp(self):
        """Test impact score for NFP"""
        scorer = EventImpactScorer()

        event = NormalizedEvent(
            title="US Non-Farm Payrolls",
            country="USD",
            currency="USD",
            scheduled_time=datetime.utcnow() + timedelta(hours=1),
            impact="HIGH",
            source="forexfactory",
            category="employment",
        )

        score = scorer.calculate_impact_score(event)

        # NFP should have high impact score
        assert score >= 0.5
        assert score <= 1.0

    def test_calculate_impact_score_with_surprise(self):
        """Test impact score with surprise potential"""
        scorer = EventImpactScorer()

        event = NormalizedEvent(
            title="US CPI",
            country="USD",
            currency="USD",
            scheduled_time=datetime.utcnow() + timedelta(hours=1),
            impact="HIGH",
            source="forexfactory",
            category="inflation",
            forecast="3.5%",
            previous="3.0%",  # Large change = high surprise
        )

        score = scorer.calculate_impact_score(event)

        # Should have high score due to surprise potential
        assert score >= 0.4

    def test_get_impact_level(self):
        """Test impact level classification"""
        scorer = EventImpactScorer()

        assert scorer.get_impact_level(0.8) == "HIGH"
        assert scorer.get_impact_level(0.5) == "MEDIUM"
        assert scorer.get_impact_level(0.2) == "LOW"

    def test_score_multiple_events(self):
        """Test scoring multiple events"""
        scorer = EventImpactScorer()

        events = [
            NormalizedEvent(
                title="US NFP",
                country="USD",
                currency="USD",
                scheduled_time=datetime.utcnow() + timedelta(hours=1),
                impact="HIGH",
                source="test",
            ),
            NormalizedEvent(
                title="US Retail Sales",
                country="USD",
                currency="USD",
                scheduled_time=datetime.utcnow() + timedelta(hours=2),
                impact="MEDIUM",
                source="test",
            ),
            NormalizedEvent(
                title="US Trade Balance",
                country="USD",
                currency="USD",
                scheduled_time=datetime.utcnow() + timedelta(hours=3),
                impact="LOW",
                source="test",
            ),
        ]

        scored = scorer.score_multiple_events(events)

        # Should be sorted by score descending
        assert len(scored) == 3
        assert scored[0][1] >= scored[1][1]
        assert scored[1][1] >= scored[2][1]

    def test_get_high_impact_events(self):
        """Test filtering high impact events"""
        scorer = EventImpactScorer()

        events = [
            NormalizedEvent(
                title="US NFP",
                country="USD",
                currency="USD",
                scheduled_time=datetime.utcnow() + timedelta(hours=1),
                impact="HIGH",
                source="test",
            ),
            NormalizedEvent(
                title="US Retail Sales",
                country="USD",
                currency="USD",
                scheduled_time=datetime.utcnow() + timedelta(hours=2),
                impact="MEDIUM",
                source="test",
            ),
        ]

        high_impact = scorer.get_high_impact_events(events)

        # Should only include high impact events
        assert all(event.impact == "HIGH" for event in high_impact)


class TestPreEventRiskManager:
    """Test PreEventRiskManager"""

    def test_apply_risk_adjustment_no_events(self):
        """Test risk adjustment with no events"""
        manager = PreEventRiskManager()

        adjusted, info = manager.apply_risk_adjustment(0.8, [])

        assert adjusted == 0.8
        assert info["risk_level"] == "none"

    def test_apply_risk_adjustment_high_impact_5min(self):
        """Test risk adjustment 5 minutes before high impact event"""
        manager = PreEventRiskManager()

        event = NormalizedEvent(
            title="US NFP",
            country="USD",
            currency="USD",
            scheduled_time=datetime.utcnow() + timedelta(minutes=5),
            impact="HIGH",
            source="test",
            impact_score=0.9,
            affected_symbols=["EURUSD"],
        )

        adjusted, info = manager.apply_risk_adjustment(0.8, [event])

        # Should have severe confidence reduction
        assert adjusted < 0.1  # 0.8 * 0.05 = 0.04
        assert info["risk_level"] == "critical"
        assert info["nearest_event"]["title"] == "US NFP"

    def test_apply_risk_adjustment_high_impact_1h(self):
        """Test risk adjustment 1 hour before high impact event"""
        manager = PreEventRiskManager()

        event = NormalizedEvent(
            title="US NFP",
            country="USD",
            currency="USD",
            scheduled_time=datetime.utcnow() + timedelta(hours=1),
            impact="HIGH",
            source="test",
            impact_score=0.9,
        )

        adjusted, info = manager.apply_risk_adjustment(0.8, [event])

        # Should have major confidence reduction
        assert adjusted == 0.4  # 0.8 * 0.5
        assert info["risk_level"] == "high"

    def test_apply_risk_adjustment_medium_impact(self):
        """Test risk adjustment for medium impact event"""
        manager = PreEventRiskManager()

        event = NormalizedEvent(
            title="US Retail Sales",
            country="USD",
            currency="USD",
            scheduled_time=datetime.utcnow() + timedelta(minutes=30),
            impact="MEDIUM",
            source="test",
            impact_score=0.5,
        )

        adjusted, info = manager.apply_risk_adjustment(0.8, [event])

        # Should have moderate confidence reduction
        assert adjusted < 0.8
        assert adjusted > 0.2

    def test_post_event_recovery(self):
        """Test confidence recovery after event"""
        manager = PreEventRiskManager()

        # Event was 10 minutes ago
        event = NormalizedEvent(
            title="US NFP",
            country="USD",
            currency="USD",
            scheduled_time=datetime.utcnow() - timedelta(minutes=10),
            impact="HIGH",
            source="test",
            impact_score=0.9,
        )

        adjusted, info = manager.apply_risk_adjustment(0.8, [event])

        # Should be recovering (10/30 = 33% recovery)
        assert adjusted > 0.4  # More than 50% penalty
        assert adjusted < 0.8  # Less than full confidence
        assert info["risk_level"] == "post_event_recovery"

    def test_should_halt_trading(self):
        """Test trading halt decision"""
        manager = PreEventRiskManager()

        # High impact event in 3 minutes
        event = NormalizedEvent(
            title="US NFP",
            country="USD",
            currency="USD",
            scheduled_time=datetime.utcnow() + timedelta(minutes=3),
            impact="HIGH",
            source="test",
        )

        should_halt, reason = manager.should_halt_trading([event])

        assert should_halt is True
        assert "US NFP" in reason

    def test_should_not_halt_trading(self):
        """Test no trading halt for distant event"""
        manager = PreEventRiskManager()

        # High impact event in 1 hour
        event = NormalizedEvent(
            title="US NFP",
            country="USD",
            currency="USD",
            scheduled_time=datetime.utcnow() + timedelta(hours=1),
            impact="HIGH",
            source="test",
        )

        should_halt, reason = manager.should_halt_trading([event])

        assert should_halt is False

    def test_get_position_size_adjustment(self):
        """Test position size adjustment"""
        manager = PreEventRiskManager()

        # High impact event in 10 minutes
        event = NormalizedEvent(
            title="US NFP",
            country="USD",
            currency="USD",
            scheduled_time=datetime.utcnow() + timedelta(minutes=10),
            impact="HIGH",
            source="test",
        )

        adjustment = manager.get_position_size_adjustment([event])

        # Should reduce position size
        assert adjustment < 1.0
        assert adjustment >= 0.1

    def test_get_affected_symbols(self):
        """Test getting affected symbols"""
        manager = PreEventRiskManager()

        events = [
            NormalizedEvent(
                title="US NFP",
                country="USD",
                currency="USD",
                scheduled_time=datetime.utcnow() + timedelta(hours=1),
                impact="HIGH",
                source="test",
                affected_symbols=["EURUSD", "GBPUSD"],
            ),
            NormalizedEvent(
                title="ECB Rate",
                country="EUR",
                currency="EUR",
                scheduled_time=datetime.utcnow() + timedelta(hours=2),
                impact="HIGH",
                source="test",
                affected_symbols=["EURUSD", "EURGBP"],
            ),
        ]

        affected = manager.get_affected_symbols(events)

        assert "EURUSD" in affected
        assert "GBPUSD" in affected
        assert "EURGBP" in affected


class TestEconomicCalendarStream:
    """Test EconomicCalendarStream"""

    @pytest.mark.asyncio
    async def test_connect_mock_mode(self):
        """Test connection in mock mode"""
        stream = EconomicCalendarStream(mode="mock")

        connected = await stream.connect()

        assert connected is True

    @pytest.mark.asyncio
    async def test_fetch_mock_calendar(self):
        """Test fetching mock calendar"""
        stream = EconomicCalendarStream(mode="mock")
        await stream.connect()

        await stream._fetch_mock_calendar()

        # Should have generated some events
        assert len(stream.scheduled_events) > 0

        # Events should be sorted by time
        for i in range(len(stream.scheduled_events) - 1):
            assert (
                stream.scheduled_events[i].scheduled_time
                <= stream.scheduled_events[i + 1].scheduled_time
            )

    @pytest.mark.asyncio
    async def test_get_upcoming_events(self):
        """Test getting upcoming events"""
        stream = EconomicCalendarStream(mode="mock")
        await stream.connect()
        await stream._fetch_mock_calendar()

        upcoming = stream.get_upcoming_events(hours_ahead=24)

        # Should return events
        assert isinstance(upcoming, list)

        # All events should be in the future
        now = datetime.utcnow()
        for event in upcoming:
            assert event.scheduled_time >= now

    @pytest.mark.asyncio
    async def test_get_events_by_currency(self):
        """Test getting events by currency"""
        stream = EconomicCalendarStream(mode="mock")
        await stream.connect()
        await stream._fetch_mock_calendar()

        usd_events = stream.get_events_by_currency("USD", hours_ahead=24)

        # All events should be USD
        for event in usd_events:
            assert event.currency == "USD"

    @pytest.mark.asyncio
    async def test_stream_lifecycle(self):
        """Test stream start/stop lifecycle"""
        stream = EconomicCalendarStream(mode="mock", check_interval_s=1)

        # Start stream
        await stream.start()
        assert stream.status.value == "active"

        # Let it run briefly
        await asyncio.sleep(0.5)

        # Stop stream
        await stream.stop()
        assert stream.status.value == "paused"

        # Close stream
        await stream.close()
        assert stream.status.value == "closed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
