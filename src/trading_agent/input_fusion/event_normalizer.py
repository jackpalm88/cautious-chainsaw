"""
Event Normalizer - Economic calendar event normalization
Supports multiple sources: ForexFactory, TradingEconomics, FXStreet
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class NormalizedEvent:
    """Normalized economic calendar event"""

    title: str
    country: str
    currency: str
    scheduled_time: datetime
    impact: str  # "HIGH", "MEDIUM", "LOW"
    source: str
    event_id: str | None = None
    forecast: str | None = None
    previous: str | None = None
    actual: str | None = None
    url: str | None = None
    category: str | None = None  # "employment", "inflation", "gdp", etc.

    # Computed fields
    impact_score: float = 0.0  # 0.0-1.0 computed by ImpactScorer
    affected_symbols: list[str] | None = None


class EventNormalizer:
    """Normalize economic calendar events from multiple sources"""

    def __init__(self):
        # Currency to symbol mapping
        self.currency_symbols = {
            "USD": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "XAUUSD"],
            "EUR": ["EURUSD", "EURGBP", "EURJPY", "EURAUD", "EURCAD", "EURCHF"],
            "GBP": ["GBPUSD", "EURGBP", "GBPJPY", "GBPAUD", "GBPCAD", "GBPCHF"],
            "JPY": ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "CHFJPY"],
            "AUD": ["AUDUSD", "EURAUD", "GBPAUD", "AUDJPY", "AUDCAD", "AUDCHF"],
            "CAD": ["USDCAD", "EURCAD", "GBPCAD", "CADJPY", "AUDCAD"],
            "CHF": ["USDCHF", "EURCHF", "GBPCHF", "CHFJPY", "AUDCHF"],
            "NZD": ["NZDUSD", "EURNZD", "GBPNZD", "NZDJPY", "AUDNZD"],
        }

        # Event category keywords
        self.category_keywords = {
            "employment": ["payrolls", "employment", "unemployment", "jobs", "nfp"],
            "inflation": ["cpi", "inflation", "ppi", "prices", "price index"],
            "gdp": ["gdp", "growth", "output"],
            "interest_rate": ["rate decision", "interest rate", "monetary policy", "fomc", "ecb"],
            "manufacturing": ["pmi", "manufacturing", "industrial production"],
            "retail": ["retail sales", "consumer spending"],
            "housing": ["housing", "building permits", "home sales"],
            "trade": ["trade balance", "exports", "imports"],
            "sentiment": ["confidence", "sentiment", "expectations"],
        }

    def normalize_forexfactory(self, raw: dict[str, Any]) -> NormalizedEvent:
        """
        Normalize ForexFactory event format

        Expected format:
        {
            "title": "Non-Farm Employment Change",
            "country": "USD",
            "date": "2025-11-07",
            "time": "13:30",
            "impact": "High",
            "forecast": "150K",
            "previous": "142K"
        }
        """
        # Parse datetime
        date_str = raw.get("date", "")
        time_str = raw.get("time", "")
        scheduled_time = self._parse_datetime(f"{date_str} {time_str}")

        # Normalize impact
        impact = self._normalize_impact(raw.get("impact", ""))

        # Determine currency
        country = raw.get("country", "")
        currency = self._country_to_currency(country)

        # Categorize event
        title = raw.get("title", "")
        category = self._categorize_event(title)

        # Get affected symbols
        affected_symbols = self.currency_symbols.get(currency, [])

        return NormalizedEvent(
            title=title,
            country=country,
            currency=currency,
            scheduled_time=scheduled_time,
            impact=impact,
            source="forexfactory",
            event_id=raw.get("id"),
            forecast=raw.get("forecast"),
            previous=raw.get("previous"),
            actual=raw.get("actual"),
            url=raw.get("url"),
            category=category,
            affected_symbols=affected_symbols,
        )

    def normalize_tradingeconomics(self, raw: dict[str, Any]) -> NormalizedEvent:
        """
        Normalize TradingEconomics event format

        Expected format:
        {
            "Event": "Non Farm Payrolls",
            "Country": "United States",
            "Date": "2025-11-07T13:30:00",
            "Actual": null,
            "Previous": "142K",
            "Forecast": "150K",
            "TEForecast": "148K",
            "Importance": 3
        }
        """
        # Parse datetime
        date_str = raw.get("Date", "")
        scheduled_time = self._parse_datetime(date_str)

        # Normalize impact from importance (1-3 scale)
        importance = raw.get("Importance", 1)
        if importance >= 3:
            impact = "HIGH"
        elif importance >= 2:
            impact = "MEDIUM"
        else:
            impact = "LOW"

        # Determine currency from country
        country = raw.get("Country", "")
        currency = self._country_to_currency(country)

        # Categorize event
        title = raw.get("Event", "")
        category = self._categorize_event(title)

        # Get affected symbols
        affected_symbols = self.currency_symbols.get(currency, [])

        return NormalizedEvent(
            title=title,
            country=country,
            currency=currency,
            scheduled_time=scheduled_time,
            impact=impact,
            source="tradingeconomics",
            event_id=raw.get("CalendarId"),
            forecast=raw.get("Forecast"),
            previous=raw.get("Previous"),
            actual=raw.get("Actual"),
            category=category,
            affected_symbols=affected_symbols,
        )

    def normalize_fxstreet(self, raw: dict[str, Any]) -> NormalizedEvent:
        """
        Normalize FXStreet event format

        Expected format:
        {
            "name": "US Non-Farm Payrolls",
            "countryCode": "US",
            "dateUtc": "2025-11-07T13:30:00Z",
            "volatility": "High",
            "consensus": "150K",
            "previous": "142K"
        }
        """
        # Parse datetime
        date_str = raw.get("dateUtc", "")
        scheduled_time = self._parse_datetime(date_str)

        # Normalize impact from volatility
        volatility = raw.get("volatility", "")
        impact = self._normalize_impact(volatility)

        # Determine currency from country code
        country_code = raw.get("countryCode", "")
        currency = self._country_code_to_currency(country_code)

        # Categorize event
        title = raw.get("name", "")
        category = self._categorize_event(title)

        # Get affected symbols
        affected_symbols = self.currency_symbols.get(currency, [])

        return NormalizedEvent(
            title=title,
            country=country_code,
            currency=currency,
            scheduled_time=scheduled_time,
            impact=impact,
            source="fxstreet",
            event_id=raw.get("id"),
            forecast=raw.get("consensus"),
            previous=raw.get("previous"),
            actual=raw.get("actual"),
            url=raw.get("url"),
            category=category,
            affected_symbols=affected_symbols,
        )

    def _parse_datetime(self, date_str: str) -> datetime:
        """Parse datetime string with multiple format support"""
        if not date_str:
            return datetime.utcnow()

        # Try ISO format first
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass

        # Try common formats
        formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Fallback to current time
        return datetime.utcnow()

    def _normalize_impact(self, impact_str: str) -> str:
        """Normalize impact string to HIGH/MEDIUM/LOW"""
        impact_lower = impact_str.lower()

        if any(word in impact_lower for word in ["high", "3", "red", "important", "major"]):
            return "HIGH"
        elif any(word in impact_lower for word in ["medium", "2", "orange", "moderate"]):
            return "MEDIUM"
        else:
            return "LOW"

    def _country_to_currency(self, country: str) -> str:
        """Map country to currency code"""
        country_lower = country.lower()

        mapping = {
            "usd": "USD",
            "united states": "USD",
            "us": "USD",
            "eur": "EUR",
            "euro": "EUR",
            "eurozone": "EUR",
            "germany": "EUR",
            "france": "EUR",
            "gbp": "GBP",
            "united kingdom": "GBP",
            "uk": "GBP",
            "jpy": "JPY",
            "japan": "JPY",
            "aud": "AUD",
            "australia": "AUD",
            "cad": "CAD",
            "canada": "CAD",
            "chf": "CHF",
            "switzerland": "CHF",
            "nzd": "NZD",
            "new zealand": "NZD",
        }

        return mapping.get(country_lower, "USD")

    def _country_code_to_currency(self, code: str) -> str:
        """Map country code to currency"""
        code_upper = code.upper()

        mapping = {
            "US": "USD",
            "EU": "EUR",
            "DE": "EUR",
            "FR": "EUR",
            "GB": "GBP",
            "UK": "GBP",
            "JP": "JPY",
            "AU": "AUD",
            "CA": "CAD",
            "CH": "CHF",
            "NZ": "NZD",
        }

        return mapping.get(code_upper, "USD")

    def _categorize_event(self, title: str) -> str:
        """Categorize event based on title keywords"""
        title_lower = title.lower()

        for category, keywords in self.category_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                return category

        return "other"
