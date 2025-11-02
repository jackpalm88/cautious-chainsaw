"""
Tests for MarketContext tool
"""

import numpy as np

from src.trading_agent.tools import MarketContext


class TestMarketContext:
    """Test suite for MarketContext tool"""

    def test_trending_market(self):
        """Test detection of trending market"""
        # Generate strong uptrend
        prices = [100 + i * 1.0 for i in range(100)]

        tool = MarketContext()
        result = tool.execute(prices=prices)

        assert result.success
        assert result.value["regime"] == "trending"
        assert result.value["trend_strength"] > 0.8
        assert result.confidence > 0.7

    def test_ranging_market(self):
        """Test detection of ranging market"""
        # Generate sideways movement
        prices = [100 + np.sin(i * 0.1) * 2 for i in range(100)]

        tool = MarketContext()
        result = tool.execute(prices=prices)

        assert result.success
        assert result.value["regime"] == "ranging"
        assert result.value["trend_strength"] < 0.5

    def test_volatile_market(self):
        """Test detection of volatile market"""
        # Generate high volatility
        np.random.seed(42)
        prices = [100 + np.random.randn() * 5 for i in range(100)]

        tool = MarketContext()
        result = tool.execute(prices=prices)

        assert result.success
        assert result.value["regime"] == "volatile"
        assert result.value["volatility"] > 0

    def test_atr_calculation(self):
        """Test ATR calculation"""
        prices = [100 + i * 0.1 for i in range(50)]

        tool = MarketContext(atr_period=14)
        result = tool.execute(prices=prices)

        assert result.success
        assert "volatility" in result.value
        assert result.value["volatility"] > 0
        assert "volatility_normalized" in result.value

    def test_trend_strength(self):
        """Test trend strength calculation"""
        # Strong uptrend
        strong_trend = [100 + i * 1.0 for i in range(100)]
        # Weak trend
        weak_trend = [100 + i * 0.1 + np.sin(i * 0.5) * 2 for i in range(100)]

        tool = MarketContext()

        result_strong = tool.execute(prices=strong_trend)
        result_weak = tool.execute(prices=weak_trend)

        assert result_strong.value["trend_strength"] > result_weak.value["trend_strength"]
        assert result_strong.value["trend_strength"] > 0.9
        assert result_weak.value["trend_strength"] < 0.7

    def test_insufficient_data(self):
        """Test with insufficient data"""
        prices = [100, 101, 102]  # Only 3 prices

        tool = MarketContext(atr_period=14, regime_lookback=50)

        valid, msg = tool.validate_inputs(prices=prices)
        assert not valid
        assert "at least" in msg.lower()

    def test_metadata(self):
        """Test metadata in result"""
        prices = [100 + i * 0.1 for i in range(100)]

        tool = MarketContext(atr_period=14, regime_lookback=50)
        result = tool.execute(prices=prices)

        assert result.success
        assert "atr_period" in result.metadata
        assert "regime_lookback" in result.metadata
        assert "sample_size" in result.metadata
        assert result.metadata["sample_size"] == 100

    def test_confidence_calculation(self):
        """Test confidence calculation"""
        # Large sample, clear trend
        prices = [100 + i * 0.5 for i in range(200)]

        tool = MarketContext()
        result = tool.execute(prices=prices)

        assert result.success
        assert result.confidence > 0.7
        assert result.confidence <= 0.95

    def test_llm_function_format(self):
        """Test LLM function calling format"""
        tool = MarketContext()
        func = tool.to_llm_function()

        assert func["name"] == "market_context"
        assert "description" in func
        assert "parameters" in func
        assert "prices" in func["parameters"]["properties"]

    def test_custom_parameters(self):
        """Test with custom ATR and lookback periods"""
        prices = [100 + i * 0.1 for i in range(100)]

        tool = MarketContext(atr_period=20, regime_lookback=30)
        result = tool.execute(prices=prices)

        assert result.success
        assert result.metadata["atr_period"] == 20
        assert result.metadata["regime_lookback"] == 30

    def test_downtrend_detection(self):
        """Test detection of downtrend"""
        # Generate downtrend
        prices = [100 - i * 0.5 for i in range(100)]

        tool = MarketContext()
        result = tool.execute(prices=prices)

        assert result.success
        assert result.value["regime"] == "trending"
        assert result.value["trend_strength"] > 0.8

    def test_volatility_normalization(self):
        """Test that volatility is normalized by price"""
        # High price, same absolute volatility
        high_prices = [1000 + i * 0.1 for i in range(100)]
        # Low price, same absolute volatility
        low_prices = [10 + i * 0.1 for i in range(100)]

        tool = MarketContext()

        result_high = tool.execute(prices=high_prices)
        result_low = tool.execute(prices=low_prices)

        # Normalized volatility should be lower for high prices
        assert (
            result_high.value["volatility_normalized"] < result_low.value["volatility_normalized"]
        )
