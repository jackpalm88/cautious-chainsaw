"""
Symbol Relevance Scorer - Calculates news relevance for trading symbols
Filters noise and increases signal-to-noise ratio
"""

from datetime import datetime, time
from typing import Any


class SymbolRelevanceScorer:
    """Calculates relevance score for news items per trading symbol"""

    def __init__(self):
        """Initialize relevance scorer"""
        # Symbol-specific keywords (expandable)
        self.symbol_keywords = {
            "EURUSD": ["EUR", "USD", "ECB", "Fed", "euro", "dollar", "eurozone"],
            "GBPUSD": ["GBP", "USD", "pound", "dollar", "BoE", "Bank of England"],
            "USDJPY": ["USD", "JPY", "dollar", "yen", "BoJ", "Bank of Japan"],
            "XAUUSD": [
                "gold",
                "precious metals",
                "inflation",
                "safe haven",
                "commodity",
            ],
            "BTCUSD": ["bitcoin", "BTC", "crypto", "cryptocurrency", "blockchain"],
        }

        # Source credibility scores (0.0-1.0)
        self.source_credibility = {
            "Reuters": 1.0,
            "Bloomberg": 1.0,
            "Financial Times": 0.95,
            "Wall Street Journal": 0.95,
            "CNBC": 0.85,
            "MarketWatch": 0.80,
            "Yahoo Finance": 0.75,
            "Unknown": 0.50,
        }

        # Market hours (UTC)
        self.market_hours = {
            "forex": {"start": time(0, 0), "end": time(23, 59)},  # 24/7
            "us_stocks": {"start": time(13, 30), "end": time(20, 0)},  # 9:30-16:00 ET
        }

    def calculate_relevance(
        self, news_item: Any, symbol: str, market_type: str = "forex"
    ) -> float:
        """
        Calculate relevance score for news item and symbol

        Args:
            news_item: NormalizedNews object
            symbol: Trading symbol (e.g., "EURUSD")
            market_type: Market type ("forex", "us_stocks")

        Returns:
            Relevance score (0.0-1.0)
        """
        # Keyword matching (40% weight)
        keyword_score = self._keyword_match(news_item, symbol)

        # Source credibility (30% weight)
        source_score = self._source_credibility(news_item.source)

        # Temporal proximity to market hours (30% weight)
        timing_score = self._market_timing(news_item.published_at, market_type)

        # Weighted combination
        relevance = keyword_score * 0.4 + source_score * 0.3 + timing_score * 0.3

        # Boost for major events
        if news_item.is_major_event:
            relevance = min(1.0, relevance * 1.2)

        return relevance

    def _keyword_match(self, news_item: Any, symbol: str) -> float:
        """
        Calculate keyword matching score

        Args:
            news_item: NormalizedNews object
            symbol: Trading symbol

        Returns:
            Keyword score (0.0-1.0)
        """
        # Get keywords for symbol
        keywords = self.symbol_keywords.get(symbol, [])
        if not keywords:
            return 0.5  # Default for unknown symbols

        # Combine title and description
        text = f"{news_item.title} {news_item.description}".lower()

        # Count keyword matches
        matches = sum(1 for keyword in keywords if keyword.lower() in text)

        # Normalize by number of keywords
        score = min(1.0, matches / len(keywords) * 2.0)  # Scale up for partial matches

        return score

    def _source_credibility(self, source: str) -> float:
        """
        Get source credibility score

        Args:
            source: News source name

        Returns:
            Credibility score (0.0-1.0)
        """
        # Exact match
        if source in self.source_credibility:
            return self.source_credibility[source]

        # Partial match (case-insensitive)
        source_lower = source.lower()
        for known_source, score in self.source_credibility.items():
            if known_source.lower() in source_lower:
                return score

        # Default for unknown sources
        return 0.50

    def _market_timing(self, published_at: datetime, market_type: str) -> float:
        """
        Calculate timing score based on market hours

        Args:
            published_at: News publication timestamp
            market_type: Market type

        Returns:
            Timing score (0.0-1.0)
        """
        # Get market hours
        hours = self.market_hours.get(market_type, self.market_hours["forex"])

        # Extract time
        news_time = published_at.time()

        # Check if within market hours
        if hours["start"] <= news_time <= hours["end"]:
            return 1.0
        else:
            # Reduced score for off-hours news
            return 0.6

    def filter_relevant_news(
        self,
        news_items: list[Any],
        symbols: list[str],
        threshold: float = 0.5,
        market_type: str = "forex",
    ) -> dict[str, list[tuple[Any, float]]]:
        """
        Filter news items by relevance for multiple symbols

        Args:
            news_items: List of NormalizedNews objects
            symbols: List of trading symbols
            threshold: Minimum relevance score
            market_type: Market type

        Returns:
            Dict mapping symbol -> list of (news_item, relevance_score) tuples
        """
        results: dict[str, list[tuple[Any, float]]] = {symbol: [] for symbol in symbols}

        for news_item in news_items:
            for symbol in symbols:
                relevance = self.calculate_relevance(news_item, symbol, market_type)

                if relevance >= threshold:
                    results[symbol].append((news_item, relevance))

        # Sort by relevance (descending)
        for symbol in results:
            results[symbol].sort(key=lambda x: x[1], reverse=True)

        return results

    def add_symbol_keywords(self, symbol: str, keywords: list[str]) -> None:
        """
        Add custom keywords for a symbol

        Args:
            symbol: Trading symbol
            keywords: List of keywords
        """
        if symbol in self.symbol_keywords:
            self.symbol_keywords[symbol].extend(keywords)
        else:
            self.symbol_keywords[symbol] = keywords

    def add_source_credibility(self, source: str, score: float) -> None:
        """
        Add custom source credibility score

        Args:
            source: Source name
            score: Credibility score (0.0-1.0)
        """
        self.source_credibility[source] = max(0.0, min(1.0, score))
