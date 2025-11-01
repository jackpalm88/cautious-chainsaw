"""
News Stream - Real-time news data stream
Supports mock and API modes (NewsAPI, Alpha Vantage)
"""

import asyncio
import random
from datetime import datetime
from typing import Any

from .data_stream import DataStream, StreamEvent
from .news_normalizer import NewsNormalizer
from .symbol_relevance import SymbolRelevanceScorer


class NewsStream(DataStream):
    """Real-time news data stream"""

    def __init__(
        self,
        symbols: list[str],
        mode: str = "mock",
        api_key: str | None = None,
        fetch_interval_s: int = 60,
        relevance_threshold: float = 0.5,
        **kwargs,
    ):
        """
        Initialize news stream

        Args:
            symbols: List of trading symbols to track
            mode: "mock", "newsapi", or "alphavantage"
            api_key: API key for news service
            fetch_interval_s: Fetch interval in seconds
            relevance_threshold: Minimum relevance score
            **kwargs: Additional args for DataStream
        """
        super().__init__(stream_id=f"news_{'_'.join(symbols[:2])}", **kwargs)
        self.symbols = symbols
        self.mode = mode
        self.api_key = api_key
        self.fetch_interval = fetch_interval_s
        self.relevance_threshold = relevance_threshold

        # Components
        self.normalizer = NewsNormalizer()
        self.relevance_scorer = SymbolRelevanceScorer()

        # Mock data
        self.mock_news_templates = [
            {
                "title": "ECB hints at potential rate cut in Q4",
                "description": "European Central Bank officials suggest monetary policy easing...",
                "source": "Reuters",
                "symbols": ["EURUSD"],
            },
            {
                "title": "Fed maintains hawkish stance on inflation",
                "description": "Federal Reserve reiterates commitment to 2% inflation target...",
                "source": "Bloomberg",
                "symbols": ["EURUSD", "USDJPY"],
            },
            {
                "title": "Gold prices surge on safe-haven demand",
                "description": "Precious metals rally amid geopolitical tensions...",
                "source": "CNBC",
                "symbols": ["XAUUSD"],
            },
            {
                "title": "Bank of England holds rates steady",
                "description": "BoE maintains current monetary policy stance...",
                "source": "Financial Times",
                "symbols": ["GBPUSD"],
            },
        ]

    async def connect(self) -> bool:
        """Connect to news source"""
        if self.mode == "mock":
            # Mock mode - always succeeds
            return True
        elif self.mode in ["newsapi", "alphavantage"]:
            # API mode - would validate API key
            if not self.api_key:
                return False
            # For MVP, simulate connection
            await asyncio.sleep(0.1)
            return True
        else:
            return False

    async def disconnect(self) -> None:
        """Disconnect from news source"""
        pass

    async def _fetch_data(self) -> StreamEvent | None:
        """Fetch news data"""
        if self.mode == "mock":
            return await self._fetch_mock_news()
        elif self.mode == "newsapi":
            return await self._fetch_newsapi()
        elif self.mode == "alphavantage":
            return await self._fetch_alphavantage()
        return None

    async def _fetch_mock_news(self) -> StreamEvent | None:
        """Generate mock news data"""
        # Wait for fetch interval
        await asyncio.sleep(self.fetch_interval)

        # Randomly select a news template
        template = random.choice(self.mock_news_templates)

        # Create raw news item
        raw_news = {
            "title": template["title"],
            "description": template["description"],
            "source": {"name": template["source"]},
            "url": "https://example.com/news",
            "publishedAt": datetime.now().isoformat(),
            "author": "Mock Author",
        }

        # Normalize
        normalized = self.normalizer.normalize_newsapi(raw_news)

        # Calculate relevance for each symbol
        relevant_symbols = []
        max_relevance = 0.0

        for symbol in self.symbols:
            relevance = self.relevance_scorer.calculate_relevance(normalized, symbol)
            if relevance >= self.relevance_threshold:
                relevant_symbols.append(symbol)
                max_relevance = max(max_relevance, relevance)

        # Skip if not relevant
        if not relevant_symbols:
            return None

        # Update normalized news
        normalized.symbols = relevant_symbols
        normalized.relevance_score = max_relevance

        # Create event
        event = StreamEvent(
            stream_id=self.stream_id,
            event_type="news_update",
            timestamp=normalized.published_at,
            data={
                "title": normalized.title,
                "description": normalized.description,
                "source": normalized.source,
                "url": normalized.url,
                "published_at": normalized.published_at.isoformat(),
                "symbols": normalized.symbols,
                "relevance_score": normalized.relevance_score,
                "sentiment_score": normalized.sentiment_score,
                "is_major_event": normalized.is_major_event,
            },
            metadata={
                "mode": "mock",
                "fetch_interval": self.fetch_interval,
                "relevance_threshold": self.relevance_threshold,
            },
        )

        return event

    async def _fetch_newsapi(self) -> StreamEvent | None:
        """Fetch news from NewsAPI (placeholder for MVP)"""
        # For MVP, simulate with mock data
        return await self._fetch_mock_news()

    async def _fetch_alphavantage(self) -> StreamEvent | None:
        """Fetch news from Alpha Vantage (placeholder for MVP)"""
        # For MVP, simulate with mock data
        return await self._fetch_mock_news()

    def get_latest_news(self, symbol: str | None = None) -> list[dict[str, Any]]:
        """
        Get latest news from queue

        Args:
            symbol: Filter by symbol (optional)

        Returns:
            List of news items
        """
        # This would retrieve from internal cache
        # For MVP, return empty list
        return []
