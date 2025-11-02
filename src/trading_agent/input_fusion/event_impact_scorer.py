"""
Event Impact Scorer - Calculate economic event impact scores
Based on historical volatility, surprise potential, and market conditions
"""

from .event_normalizer import NormalizedEvent


class EventImpactScorer:
    """Calculate impact scores for economic events"""

    def __init__(self):
        # Historical volatility database (average pips moved in 15min post-event)
        # Data based on typical market reactions for major currency pairs
        self.impact_database = {
            # US Events
            "us_nonfarm_payrolls": {
                "avg_move": 120,
                "max_move": 300,
                "frequency": "monthly",
                "keywords": ["non-farm", "nfp", "payrolls"],
            },
            "us_fomc_rate_decision": {
                "avg_move": 180,
                "max_move": 500,
                "frequency": "8x_year",
                "keywords": ["fomc", "fed rate", "federal reserve rate"],
            },
            "us_cpi": {
                "avg_move": 80,
                "max_move": 200,
                "frequency": "monthly",
                "keywords": ["consumer price index", "cpi"],
            },
            "us_gdp": {
                "avg_move": 40,
                "max_move": 120,
                "frequency": "quarterly",
                "keywords": ["gdp", "gross domestic product"],
            },
            "us_retail_sales": {
                "avg_move": 35,
                "max_move": 100,
                "frequency": "monthly",
                "keywords": ["retail sales"],
            },
            "us_unemployment": {
                "avg_move": 30,
                "max_move": 80,
                "frequency": "monthly",
                "keywords": ["unemployment rate"],
            },
            # EUR Events
            "ecb_rate_decision": {
                "avg_move": 150,
                "max_move": 400,
                "frequency": "8x_year",
                "keywords": ["ecb rate", "ecb decision", "european central bank rate"],
            },
            "eur_cpi": {
                "avg_move": 60,
                "max_move": 150,
                "frequency": "monthly",
                "keywords": ["eurozone cpi", "euro area cpi"],
            },
            "eur_gdp": {
                "avg_move": 35,
                "max_move": 100,
                "frequency": "quarterly",
                "keywords": ["eurozone gdp", "euro area gdp"],
            },
            # GBP Events
            "boe_rate_decision": {
                "avg_move": 140,
                "max_move": 350,
                "frequency": "8x_year",
                "keywords": ["boe rate", "bank of england rate"],
            },
            "gbp_cpi": {
                "avg_move": 50,
                "max_move": 130,
                "frequency": "monthly",
                "keywords": ["uk cpi", "britain cpi"],
            },
            # JPY Events
            "boj_rate_decision": {
                "avg_move": 100,
                "max_move": 300,
                "frequency": "8x_year",
                "keywords": ["boj rate", "bank of japan rate"],
            },
            # Other Events
            "pmi_manufacturing": {
                "avg_move": 25,
                "max_move": 70,
                "frequency": "monthly",
                "keywords": ["pmi", "manufacturing pmi"],
            },
            "trade_balance": {
                "avg_move": 20,
                "max_move": 60,
                "frequency": "monthly",
                "keywords": ["trade balance"],
            },
        }

        # Impact score thresholds
        self.impact_thresholds = {
            "HIGH": 0.7,
            "MEDIUM": 0.4,
            "LOW": 0.0,
        }

    def calculate_impact_score(
        self,
        event: NormalizedEvent,
        current_volatility: float = 1.0,
    ) -> float:
        """
        Calculate 0.0-1.0 impact score based on:
        1. Historical volatility (50% weight)
        2. Market surprise potential (30% weight)
        3. Current market conditions (20% weight)

        Args:
            event: Normalized economic event
            current_volatility: Current market volatility multiplier (default: 1.0)

        Returns:
            Impact score from 0.0 to 1.0
        """
        # 1. Historical volatility score (50% weight)
        historical_score = self._calculate_historical_score(event)

        # 2. Surprise potential score (30% weight)
        surprise_score = self._calculate_surprise_score(event)

        # 3. Market conditions score (20% weight)
        market_score = min(1.0, current_volatility)

        # Weighted combination
        final_score = historical_score * 0.5 + surprise_score * 0.3 + market_score * 0.2

        return min(1.0, max(0.0, final_score))

    def _calculate_historical_score(self, event: NormalizedEvent) -> float:
        """Calculate score based on historical volatility data"""
        # Classify event type
        event_type = self._classify_event_type(event)

        # Get historical data
        historical_data = self.impact_database.get(event_type, {"avg_move": 20, "max_move": 60})

        # Normalize to 0.0-1.0 scale (300 pips = max impact)
        avg_move = historical_data["avg_move"]
        score = min(1.0, avg_move / 300.0)

        # Boost score based on manual impact classification
        if event.impact == "HIGH":
            score = max(score, 0.7)
        elif event.impact == "MEDIUM":
            score = max(score, 0.4)
        else:  # LOW
            score = max(score, 0.2)

        return score

    def _calculate_surprise_score(self, event: NormalizedEvent) -> float:
        """Calculate surprise potential score"""
        # If we have forecast and previous data, calculate surprise potential
        if event.forecast and event.previous:
            try:
                # Extract numeric values
                forecast_val = self._extract_numeric(event.forecast)
                previous_val = self._extract_numeric(event.previous)

                if forecast_val is not None and previous_val is not None:
                    # Calculate relative change
                    if previous_val != 0:
                        change_pct = abs((forecast_val - previous_val) / previous_val)
                        # Normalize to 0.0-1.0 (10% change = max surprise)
                        surprise = min(1.0, change_pct / 0.10)
                        return surprise
            except (ValueError, ZeroDivisionError):
                pass

        # Default surprise score based on event impact
        if event.impact == "HIGH":
            return 0.7  # High impact events always have surprise potential
        elif event.impact == "MEDIUM":
            return 0.5
        else:
            return 0.3

    def _classify_event_type(self, event: NormalizedEvent) -> str:
        """Classify event into known types"""
        title_lower = event.title.lower()
        event.country.lower()

        # Search for matching event type
        for event_type, data in self.impact_database.items():
            keywords = data.get("keywords", [])
            for keyword in keywords:
                if keyword in title_lower:
                    return event_type

        # Fallback to generic classification
        if event.category:
            return f"generic_{event.category}"

        return "generic_other"

    def _extract_numeric(self, value_str: str) -> float | None:
        """Extract numeric value from string"""
        if not value_str:
            return None

        # Remove common suffixes
        cleaned = (
            value_str.replace("K", "000")
            .replace("M", "000000")
            .replace("B", "000000000")
            .replace("%", "")
            .strip()
        )

        try:
            return float(cleaned)
        except ValueError:
            return None

    def get_impact_level(self, score: float) -> str:
        """
        Get impact level from score

        Args:
            score: Impact score (0.0-1.0)

        Returns:
            Impact level: "HIGH", "MEDIUM", or "LOW"
        """
        if score >= self.impact_thresholds["HIGH"]:
            return "HIGH"
        elif score >= self.impact_thresholds["MEDIUM"]:
            return "MEDIUM"
        else:
            return "LOW"

    def score_multiple_events(
        self,
        events: list[NormalizedEvent],
        current_volatility: float = 1.0,
    ) -> list[tuple[NormalizedEvent, float]]:
        """
        Score multiple events and return sorted by impact

        Args:
            events: List of events to score
            current_volatility: Current market volatility multiplier

        Returns:
            List of (event, score) tuples sorted by score descending
        """
        scored = [
            (event, self.calculate_impact_score(event, current_volatility)) for event in events
        ]

        # Sort by score descending
        return sorted(scored, key=lambda x: x[1], reverse=True)

    def get_high_impact_events(
        self,
        events: list[NormalizedEvent],
        current_volatility: float = 1.0,
    ) -> list[NormalizedEvent]:
        """
        Filter events to only high impact ones

        Args:
            events: List of events to filter
            current_volatility: Current market volatility multiplier

        Returns:
            List of high impact events
        """
        scored = self.score_multiple_events(events, current_volatility)
        return [event for event, score in scored if score >= self.impact_thresholds["HIGH"]]
