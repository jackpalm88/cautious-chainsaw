"""
News Normalizer - Structured news data processing
Normalizes news from different APIs into common format
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class NormalizedNews:
    """Normalized news item"""

    title: str
    description: str
    source: str
    url: str
    published_at: datetime
    symbols: list[str]  # Relevant trading symbols
    relevance_score: float  # 0.0-1.0
    sentiment_score: float | None = None  # -1.0 to 1.0 (negative to positive)
    is_major_event: bool = False
    metadata: dict[str, Any] | None = None


class NewsNormalizer:
    """Normalizes news from different API sources"""

    def __init__(self):
        """Initialize news normalizer"""
        self.major_event_keywords = [
            "FOMC",
            "NFP",
            "ECB",
            "Fed",
            "rate decision",
            "GDP",
            "inflation",
            "unemployment",
            "central bank",
        ]

    def normalize_newsapi(self, raw_news: dict[str, Any]) -> NormalizedNews:
        """
        Normalize news from NewsAPI format

        Args:
            raw_news: Raw news item from NewsAPI

        Returns:
            NormalizedNews
        """
        # Parse published date
        published_str = raw_news.get("publishedAt", "")
        try:
            published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            published_at = datetime.now()

        # Extract basic fields
        title = raw_news.get("title", "")
        description = raw_news.get("description", "")
        source_name = raw_news.get("source", {}).get("name", "Unknown")
        url = raw_news.get("url", "")

        # Detect major events
        is_major = self._is_major_event(title, description)

        normalized = NormalizedNews(
            title=title,
            description=description or "",
            source=source_name,
            url=url,
            published_at=published_at,
            symbols=[],  # Will be filled by relevance scorer
            relevance_score=0.0,  # Will be calculated by relevance scorer
            is_major_event=is_major,
            metadata={"raw_source": "newsapi", "author": raw_news.get("author")},
        )

        return normalized

    def normalize_alphavantage(self, raw_news: dict[str, Any]) -> NormalizedNews:
        """
        Normalize news from Alpha Vantage format

        Args:
            raw_news: Raw news item from Alpha Vantage

        Returns:
            NormalizedNews
        """
        # Parse timestamp
        time_str = raw_news.get("time_published", "")
        try:
            # Alpha Vantage format: YYYYMMDDTHHMMSS
            published_at = datetime.strptime(time_str, "%Y%m%dT%H%M%S")
        except (ValueError, AttributeError):
            published_at = datetime.now()

        title = raw_news.get("title", "")
        summary = raw_news.get("summary", "")
        source = raw_news.get("source", "Unknown")
        url = raw_news.get("url", "")

        # Alpha Vantage provides ticker symbols
        tickers = raw_news.get("ticker_sentiment", [])
        symbols = [t.get("ticker", "") for t in tickers if t.get("ticker")]

        # Extract sentiment if available
        sentiment_score = None
        if tickers and len(tickers) > 0:
            # Use first ticker's sentiment as overall
            sentiment_str = tickers[0].get("ticker_sentiment_score")
            if sentiment_str:
                try:
                    sentiment_score = float(sentiment_str)
                except (ValueError, TypeError):
                    pass

        is_major = self._is_major_event(title, summary)

        normalized = NormalizedNews(
            title=title,
            description=summary,
            source=source,
            url=url,
            published_at=published_at,
            symbols=symbols,
            relevance_score=0.0,  # Will be calculated
            sentiment_score=sentiment_score,
            is_major_event=is_major,
            metadata={
                "raw_source": "alphavantage",
                "overall_sentiment_score": raw_news.get("overall_sentiment_score"),
            },
        )

        return normalized

    def _is_major_event(self, title: str, description: str) -> bool:
        """
        Detect if news is a major market event

        Args:
            title: News title
            description: News description

        Returns:
            True if major event
        """
        text = f"{title} {description}".lower()

        for keyword in self.major_event_keywords:
            if keyword.lower() in text:
                return True

        return False

    def normalize(
        self, raw_news: dict[str, Any], source: str = "newsapi"
    ) -> NormalizedNews:
        """
        Normalize news from any source

        Args:
            raw_news: Raw news item
            source: Source API name

        Returns:
            NormalizedNews
        """
        if source == "newsapi":
            return self.normalize_newsapi(raw_news)
        elif source == "alphavantage":
            return self.normalize_alphavantage(raw_news)
        else:
            # Generic normalization
            return NormalizedNews(
                title=raw_news.get("title", ""),
                description=raw_news.get("description", ""),
                source=raw_news.get("source", "Unknown"),
                url=raw_news.get("url", ""),
                published_at=datetime.now(),
                symbols=[],
                relevance_score=0.0,
                metadata={"raw_source": source},
            )
