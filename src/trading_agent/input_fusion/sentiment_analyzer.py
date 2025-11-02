"""
Sentiment Analyzer - News sentiment analysis
Supports rule-based and LLM-based sentiment scoring
"""

from typing import Any


class SentimentAnalyzer:
    """Analyzes sentiment of news items"""

    def __init__(self, mode: str = "rule_based"):
        """
        Initialize sentiment analyzer

        Args:
            mode: "rule_based" or "llm" (LLM for future)
        """
        self.mode = mode

        # Positive and negative keywords for rule-based analysis
        self.positive_keywords = [
            "surge",
            "rally",
            "gain",
            "rise",
            "boost",
            "positive",
            "growth",
            "strong",
            "optimistic",
            "bullish",
            "recovery",
            "improve",
            "increase",
            "soar",
            "jump",
        ]

        self.negative_keywords = [
            "fall",
            "drop",
            "decline",
            "plunge",
            "negative",
            "weak",
            "pessimistic",
            "bearish",
            "recession",
            "crisis",
            "concern",
            "worry",
            "decrease",
            "slump",
            "crash",
        ]

        # Intensifiers
        self.intensifiers = [
            "very",
            "extremely",
            "significantly",
            "sharply",
            "dramatically",
        ]

    def analyze(self, news_item: Any) -> tuple[float, float]:
        """
        Analyze sentiment of news item

        Args:
            news_item: NormalizedNews object

        Returns:
            Tuple of (sentiment_score, confidence)
            sentiment_score: -1.0 (negative) to 1.0 (positive)
            confidence: 0.0 to 1.0
        """
        if self.mode == "rule_based":
            return self._rule_based_sentiment(news_item)
        elif self.mode == "llm":
            # Placeholder for LLM-based sentiment
            return self._llm_sentiment(news_item)
        else:
            return (0.0, 0.0)

    def _rule_based_sentiment(self, news_item: Any) -> tuple[float, float]:
        """
        Rule-based sentiment analysis

        Args:
            news_item: NormalizedNews object

        Returns:
            Tuple of (sentiment_score, confidence)
        """
        # Combine title and description
        text = f"{news_item.title} {news_item.description}".lower()

        # Count positive and negative keywords
        positive_count = sum(1 for keyword in self.positive_keywords if keyword in text)
        negative_count = sum(1 for keyword in self.negative_keywords if keyword in text)

        # Check for intensifiers
        has_intensifier = any(intensifier in text for intensifier in self.intensifiers)
        intensifier_multiplier = 1.3 if has_intensifier else 1.0

        # Calculate raw sentiment
        total_keywords = positive_count + negative_count

        if total_keywords == 0:
            # Neutral - no sentiment keywords found
            return (0.0, 0.3)  # Low confidence

        # Sentiment score
        sentiment = (positive_count - negative_count) / total_keywords
        sentiment *= intensifier_multiplier
        sentiment = max(-1.0, min(1.0, sentiment))  # Clamp to [-1, 1]

        # Confidence based on keyword count
        confidence = min(1.0, total_keywords / 5.0)  # Max confidence at 5+ keywords

        # Boost confidence for major events
        if news_item.is_major_event:
            confidence = min(1.0, confidence * 1.2)

        return (sentiment, confidence)

    def _llm_sentiment(self, news_item: Any) -> tuple[float, float]:
        """
        LLM-based sentiment analysis (placeholder)

        Args:
            news_item: NormalizedNews object

        Returns:
            Tuple of (sentiment_score, confidence)
        """
        # Placeholder for future LLM integration
        # Would call OpenAI/Anthropic API with financial sentiment prompt
        return (0.0, 0.5)

    def batch_analyze(self, news_items: list[Any]) -> list[tuple[Any, float, float]]:
        """
        Analyze sentiment for multiple news items

        Args:
            news_items: List of NormalizedNews objects

        Returns:
            List of (news_item, sentiment_score, confidence) tuples
        """
        results = []

        for news_item in news_items:
            sentiment, confidence = self.analyze(news_item)
            results.append((news_item, sentiment, confidence))

        return results

    def add_positive_keywords(self, keywords: list[str]) -> None:
        """
        Add custom positive keywords

        Args:
            keywords: List of positive keywords
        """
        self.positive_keywords.extend(keywords)

    def add_negative_keywords(self, keywords: list[str]) -> None:
        """
        Add custom negative keywords

        Args:
            keywords: List of negative keywords
        """
        self.negative_keywords.extend(keywords)

    def get_sentiment_label(self, sentiment_score: float) -> str:
        """
        Get human-readable sentiment label

        Args:
            sentiment_score: Sentiment score (-1.0 to 1.0)

        Returns:
            Sentiment label
        """
        if sentiment_score > 0.3:
            return "POSITIVE"
        elif sentiment_score < -0.3:
            return "NEGATIVE"
        else:
            return "NEUTRAL"
