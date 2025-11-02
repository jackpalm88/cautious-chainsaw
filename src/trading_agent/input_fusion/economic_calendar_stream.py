"""
Economic Calendar Stream - Scheduled economic events data stream
Supports mock and API modes (ForexFactory, TradingEconomics, FXStreet)
"""

import asyncio
import random
from datetime import datetime, time, timedelta

from .data_stream import DataStream, StreamEvent
from .event_impact_scorer import EventImpactScorer
from .event_normalizer import EventNormalizer, NormalizedEvent


class EconomicCalendarStream(DataStream):
    """Real-time economic calendar event stream"""

    def __init__(
        self,
        symbols: list[str] | None = None,
        mode: str = "mock",
        api_key: str | None = None,
        daily_fetch_time: time = time(6, 0),  # 06:00 UTC
        check_interval_s: int = 300,  # 5 minutes
        proximity_window_h: int = 2,  # 2 hours
        **kwargs,
    ):
        """
        Initialize economic calendar stream

        Args:
            symbols: List of trading symbols to track (optional, uses currency mapping)
            mode: "mock", "forexfactory", "tradingeconomics", or "fxstreet"
            api_key: API key for calendar service
            daily_fetch_time: Time to fetch daily calendar (UTC)
            check_interval_s: Check interval in seconds
            proximity_window_h: Hours ahead to check for upcoming events
            **kwargs: Additional args for DataStream
        """
        super().__init__(stream_id="economic_calendar", **kwargs)
        self.symbols = symbols or []
        self.mode = mode
        self.api_key = api_key
        self.daily_fetch_time = daily_fetch_time
        self.check_interval = check_interval_s
        self.proximity_window = timedelta(hours=proximity_window_h)

        # Components
        self.normalizer = EventNormalizer()
        self.impact_scorer = EventImpactScorer()

        # Event storage
        self.scheduled_events: list[NormalizedEvent] = []
        self.last_daily_fetch: datetime | None = None
        self.emitted_event_ids: set[str] = set()

        # Mock data templates
        self.mock_event_templates = [
            {
                "title": "US Non-Farm Payrolls",
                "country": "USD",
                "impact": "High",
                "category": "employment",
                "forecast": "150K",
                "previous": "142K",
            },
            {
                "title": "FOMC Interest Rate Decision",
                "country": "USD",
                "impact": "High",
                "category": "interest_rate",
                "forecast": "5.25%",
                "previous": "5.25%",
            },
            {
                "title": "ECB Interest Rate Decision",
                "country": "EUR",
                "impact": "High",
                "category": "interest_rate",
                "forecast": "4.00%",
                "previous": "4.00%",
            },
            {
                "title": "US Consumer Price Index (CPI)",
                "country": "USD",
                "impact": "High",
                "category": "inflation",
                "forecast": "3.2%",
                "previous": "3.1%",
            },
            {
                "title": "US Gross Domestic Product (GDP)",
                "country": "USD",
                "impact": "Medium",
                "category": "gdp",
                "forecast": "2.5%",
                "previous": "2.4%",
            },
            {
                "title": "UK Retail Sales",
                "country": "GBP",
                "impact": "Medium",
                "category": "retail",
                "forecast": "0.3%",
                "previous": "0.1%",
            },
            {
                "title": "Japan Manufacturing PMI",
                "country": "JPY",
                "impact": "Low",
                "category": "manufacturing",
                "forecast": "49.5",
                "previous": "49.2",
            },
        ]

    async def connect(self) -> bool:
        """Connect to calendar source"""
        if self.mode == "mock":
            # Mock mode - always succeeds
            return True
        elif self.mode in ["forexfactory", "tradingeconomics", "fxstreet"]:
            # API mode - would validate API key
            if not self.api_key:
                return False
            # For MVP, simulate connection
            await asyncio.sleep(0.1)
            return True
        else:
            return False

    async def disconnect(self) -> None:
        """Disconnect from calendar source"""
        pass

    async def _fetch_data(self) -> StreamEvent | None:
        """Fetch calendar data"""
        # Check if we need to fetch daily calendar
        await self._check_daily_fetch()

        # Check for upcoming events
        return await self._check_upcoming_events()

    async def _check_daily_fetch(self) -> None:
        """Check if daily calendar fetch is needed"""
        now = datetime.utcnow()

        # Check if we need to fetch today's calendar
        should_fetch = False

        if self.last_daily_fetch is None:
            should_fetch = True
        else:
            # Check if it's a new day and past fetch time
            last_fetch_date = self.last_daily_fetch.date()
            current_date = now.date()

            if current_date > last_fetch_date:
                current_time = now.time()
                if current_time >= self.daily_fetch_time:
                    should_fetch = True

        if should_fetch:
            await self._fetch_daily_calendar()
            self.last_daily_fetch = now

    async def _fetch_daily_calendar(self) -> None:
        """Fetch full day's economic calendar"""
        if self.mode == "mock":
            await self._fetch_mock_calendar()
        elif self.mode == "forexfactory":
            await self._fetch_forexfactory_calendar()
        elif self.mode == "tradingeconomics":
            await self._fetch_tradingeconomics_calendar()
        elif self.mode == "fxstreet":
            await self._fetch_fxstreet_calendar()

    async def _fetch_mock_calendar(self) -> None:
        """Generate mock calendar events for today"""
        now = datetime.utcnow()
        now.date()

        # Generate 3-5 events throughout the day
        num_events = random.randint(3, 5)
        events = []

        for i in range(num_events):
            # Generate future times (1-12 hours ahead)
            hours_ahead = random.randint(1, 12)
            scheduled_time = now + timedelta(hours=hours_ahead)

            # Select random template
            template = random.choice(self.mock_event_templates)

            # Create raw event
            raw_event = {
                "title": template["title"],
                "country": template["country"],
                "date": scheduled_time.date().isoformat(),
                "time": scheduled_time.strftime("%H:%M"),
                "impact": template["impact"],
                "forecast": template.get("forecast"),
                "previous": template.get("previous"),
                "id": f"mock_{scheduled_time.date()}_{i}",
            }

            # Normalize
            normalized = self.normalizer.normalize_forexfactory(raw_event)

            # Calculate impact score
            impact_score = self.impact_scorer.calculate_impact_score(normalized)
            normalized.impact_score = impact_score

            events.append(normalized)

        # Sort by time
        self.scheduled_events = sorted(events, key=lambda x: x.scheduled_time)

    async def _fetch_forexfactory_calendar(self) -> None:
        """Fetch calendar from ForexFactory (placeholder for MVP)"""
        # For MVP, use mock data
        await self._fetch_mock_calendar()

    async def _fetch_tradingeconomics_calendar(self) -> None:
        """Fetch calendar from TradingEconomics (placeholder for MVP)"""
        # For MVP, use mock data
        await self._fetch_mock_calendar()

    async def _fetch_fxstreet_calendar(self) -> None:
        """Fetch calendar from FXStreet (placeholder for MVP)"""
        # For MVP, use mock data
        await self._fetch_mock_calendar()

    async def _check_upcoming_events(self) -> StreamEvent | None:
        """Check for upcoming events and create proximity warnings"""
        now = datetime.utcnow()
        proximity_threshold = now + self.proximity_window

        # Find upcoming events within proximity window
        upcoming = [
            event
            for event in self.scheduled_events
            if now <= event.scheduled_time <= proximity_threshold
        ]

        if not upcoming:
            # Wait for check interval
            await asyncio.sleep(self.check_interval)
            return None

        # Find the nearest event
        nearest_event = min(upcoming, key=lambda x: x.scheduled_time)

        # Check if we already emitted this event
        event_key = f"{nearest_event.event_id}_{nearest_event.scheduled_time.isoformat()}"
        if event_key in self.emitted_event_ids:
            # Wait for check interval
            await asyncio.sleep(self.check_interval)
            return None

        # Calculate time to event
        time_to_event = (nearest_event.scheduled_time - now).total_seconds()
        minutes_to_event = time_to_event / 60

        # Create proximity warning event
        event = StreamEvent(
            stream_id=self.stream_id,
            event_type="economic_event",
            timestamp=now,
            data={
                "event_id": nearest_event.event_id,
                "title": nearest_event.title,
                "country": nearest_event.country,
                "currency": nearest_event.currency,
                "scheduled_time": nearest_event.scheduled_time.isoformat(),
                "impact": nearest_event.impact,
                "impact_score": nearest_event.impact_score,
                "category": nearest_event.category,
                "forecast": nearest_event.forecast,
                "previous": nearest_event.previous,
                "actual": nearest_event.actual,
                "affected_symbols": nearest_event.affected_symbols or [],
                "time_to_event_minutes": minutes_to_event,
                "proximity_warning": True,
            },
            metadata={
                "mode": self.mode,
                "check_interval": self.check_interval,
                "proximity_window_hours": self.proximity_window.total_seconds() / 3600,
                "source": nearest_event.source,
            },
        )

        # Mark as emitted
        self.emitted_event_ids.add(event_key)

        # Wait for check interval
        await asyncio.sleep(self.check_interval)

        return event

    def get_upcoming_events(
        self, hours_ahead: int = 24, min_impact: str | None = None
    ) -> list[NormalizedEvent]:
        """
        Get upcoming events

        Args:
            hours_ahead: Hours ahead to look
            min_impact: Minimum impact level ("HIGH", "MEDIUM", "LOW")

        Returns:
            List of upcoming events
        """
        now = datetime.utcnow()
        threshold = now + timedelta(hours=hours_ahead)

        events = [
            event for event in self.scheduled_events if now <= event.scheduled_time <= threshold
        ]

        # Filter by impact if specified
        if min_impact:
            impact_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
            min_level = impact_order.get(min_impact, 0)
            events = [event for event in events if impact_order.get(event.impact, 0) >= min_level]

        return sorted(events, key=lambda x: x.scheduled_time)

    def get_events_by_currency(self, currency: str, hours_ahead: int = 24) -> list[NormalizedEvent]:
        """
        Get upcoming events for specific currency

        Args:
            currency: Currency code (e.g., "USD")
            hours_ahead: Hours ahead to look

        Returns:
            List of upcoming events for currency
        """
        all_events = self.get_upcoming_events(hours_ahead=hours_ahead)
        return [event for event in all_events if event.currency == currency]
