"""
Tests for NewsStream v1.9 components
"""

import asyncio
from datetime import datetime

import pytest

from src.trading_agent.input_fusion import (
    NewsNormalizer,
    NewsStream,
    SentimentAnalyzer,
    SymbolRelevanceScorer,
)


class TestNewsNormalizer:
    """Test NewsNormalizer"""

    def test_normalize_newsapi(self):
        """Test NewsAPI normalization"""
        normalizer = NewsNormalizer()

        raw_news = {
            "title": "ECB hints at rate cut",
            "description": "European Central Bank officials suggest policy easing",
            "source": {"name": "Reuters"},
            "url": "https://example.com",
            "publishedAt": "2025-01-01T10:00:00Z",
            "author": "John Doe",
        }

        normalized = normalizer.normalize_newsapi(raw_news)

        assert normalized.title == "ECB hints at rate cut"
        assert normalized.source == "Reuters"
        assert normalized.is_major_event is True  # "ECB" is major keyword

    def test_normalize_alphavantage(self):
        """Test Alpha Vantage normalization"""
        normalizer = NewsNormalizer()

        raw_news = {
            "title": "Fed maintains rates",
            "summary": "Federal Reserve keeps policy unchanged",
            "source": "Bloomberg",
            "url": "https://example.com",
            "time_published": "20250101T100000",
            "ticker_sentiment": [
                {"ticker": "EUR", "ticker_sentiment_score": "0.5"}
            ],
        }

        normalized = normalizer.normalize_alphavantage(raw_news)

        assert normalized.title == "Fed maintains rates"
        assert normalized.symbols == ["EUR"]
        assert normalized.sentiment_score == 0.5

    def test_major_event_detection(self):
        """Test major event detection"""
        normalizer = NewsNormalizer()

        # Major event
        assert normalizer._is_major_event("FOMC rate decision", "") is True
        assert normalizer._is_major_event("", "NFP report shows growth") is True

        # Not major event
        assert normalizer._is_major_event("Company earnings", "") is False


class TestSymbolRelevanceScorer:
    """Test SymbolRelevanceScorer"""

    def test_keyword_matching(self):
        """Test keyword matching"""
        scorer = SymbolRelevanceScorer()
        normalizer = NewsNormalizer()

        # High relevance news
        raw_news = {
            "title": "ECB announces euro policy change",
            "description": "European Central Bank adjusts eurozone rates",
            "source": {"name": "Reuters"},
            "url": "https://example.com",
            "publishedAt": datetime.now().isoformat(),
        }

        news_item = normalizer.normalize_newsapi(raw_news)
        relevance = scorer.calculate_relevance(news_item, "EURUSD")

        assert relevance > 0.5  # Should be relevant

    def test_source_credibility(self):
        """Test source credibility scoring"""
        scorer = SymbolRelevanceScorer()

        assert scorer._source_credibility("Reuters") == 1.0
        assert scorer._source_credibility("Bloomberg") == 1.0
        assert scorer._source_credibility("Unknown Source") == 0.5

    def test_filter_relevant_news(self):
        """Test news filtering"""
        scorer = SymbolRelevanceScorer()
        normalizer = NewsNormalizer()

        # Create test news items
        news_items = []
        for title in ["ECB policy update", "Gold prices surge", "Tech stocks rally"]:
            raw = {
                "title": title,
                "description": "",
                "source": {"name": "Reuters"},
                "url": "https://example.com",
                "publishedAt": datetime.now().isoformat(),
            }
            news_items.append(normalizer.normalize_newsapi(raw))

        # Filter for EURUSD
        results = scorer.filter_relevant_news(
            news_items, ["EURUSD"], threshold=0.3
        )

        assert "EURUSD" in results
        assert len(results["EURUSD"]) > 0  # Should have at least ECB news

    def test_add_custom_keywords(self):
        """Test adding custom keywords"""
        scorer = SymbolRelevanceScorer()

        scorer.add_symbol_keywords("CUSTOM", ["keyword1", "keyword2"])
        assert "CUSTOM" in scorer.symbol_keywords
        assert "keyword1" in scorer.symbol_keywords["CUSTOM"]


class TestSentimentAnalyzer:
    """Test SentimentAnalyzer"""

    def test_positive_sentiment(self):
        """Test positive sentiment detection"""
        analyzer = SentimentAnalyzer(mode="rule_based")
        normalizer = NewsNormalizer()

        raw_news = {
            "title": "Markets surge on positive economic data",
            "description": "Strong growth and optimistic outlook boost investor confidence",
            "source": {"name": "Reuters"},
            "url": "https://example.com",
            "publishedAt": datetime.now().isoformat(),
        }

        news_item = normalizer.normalize_newsapi(raw_news)
        sentiment, confidence = analyzer.analyze(news_item)

        assert sentiment > 0.0  # Positive sentiment
        assert confidence > 0.0

    def test_negative_sentiment(self):
        """Test negative sentiment detection"""
        analyzer = SentimentAnalyzer(mode="rule_based")
        normalizer = NewsNormalizer()

        raw_news = {
            "title": "Markets plunge on recession fears",
            "description": "Economic decline and weak data trigger bearish sentiment",
            "source": {"name": "Reuters"},
            "url": "https://example.com",
            "publishedAt": datetime.now().isoformat(),
        }

        news_item = normalizer.normalize_newsapi(raw_news)
        sentiment, confidence = analyzer.analyze(news_item)

        assert sentiment < 0.0  # Negative sentiment
        assert confidence > 0.0

    def test_neutral_sentiment(self):
        """Test neutral sentiment"""
        analyzer = SentimentAnalyzer(mode="rule_based")
        normalizer = NewsNormalizer()

        raw_news = {
            "title": "Central bank meeting scheduled",
            "description": "Officials to discuss policy options",
            "source": {"name": "Reuters"},
            "url": "https://example.com",
            "publishedAt": datetime.now().isoformat(),
        }

        news_item = normalizer.normalize_newsapi(raw_news)
        sentiment, confidence = analyzer.analyze(news_item)

        assert -0.3 <= sentiment <= 0.3  # Neutral range
        assert confidence < 0.5  # Low confidence due to no keywords

    def test_sentiment_labels(self):
        """Test sentiment label generation"""
        analyzer = SentimentAnalyzer()

        assert analyzer.get_sentiment_label(0.5) == "POSITIVE"
        assert analyzer.get_sentiment_label(-0.5) == "NEGATIVE"
        assert analyzer.get_sentiment_label(0.0) == "NEUTRAL"

    def test_batch_analyze(self):
        """Test batch sentiment analysis"""
        analyzer = SentimentAnalyzer()
        normalizer = NewsNormalizer()

        news_items = []
        for title in ["Markets surge", "Markets plunge", "Markets stable"]:
            raw = {
                "title": title,
                "description": "",
                "source": {"name": "Reuters"},
                "url": "https://example.com",
                "publishedAt": datetime.now().isoformat(),
            }
            news_items.append(normalizer.normalize_newsapi(raw))

        results = analyzer.batch_analyze(news_items)

        assert len(results) == 3
        assert all(len(r) == 3 for r in results)  # (news, sentiment, confidence)


@pytest.mark.asyncio
class TestNewsStream:
    """Test NewsStream"""

    async def test_connect_mock_mode(self):
        """Test connection in mock mode"""
        stream = NewsStream(symbols=["EURUSD"], mode="mock")

        connected = await stream.connect()
        assert connected is True

        await stream.disconnect()

    async def test_fetch_mock_news(self):
        """Test fetching mock news"""
        stream = NewsStream(
            symbols=["EURUSD"], mode="mock", fetch_interval_s=1
        )

        await stream.connect()
        await stream.start()

        # Wait for first news event
        await asyncio.sleep(1.5)

        await stream.stop()

        # Check that events were generated
        assert stream.event_count > 0

    async def test_relevance_filtering(self):
        """Test relevance filtering in news stream"""
        stream = NewsStream(
            symbols=["EURUSD"],
            mode="mock",
            fetch_interval_s=1,
            relevance_threshold=0.8,  # High threshold
        )

        await stream.connect()
        await stream.start()

        await asyncio.sleep(1.5)

        await stream.stop()

        # Events should be filtered by relevance
        # (Some mock news may not pass high threshold)
