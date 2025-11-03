"""
Tests for GenerateOrder execution tool
"""

import asyncio
import os
import random
import sys

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.trading_agent.adapters.adapter_mock import MockAdapter
from src.trading_agent.adapters.bridge import MT5ExecutionBridge
from src.trading_agent.tools.execution.generate_order import GenerateOrder


class TestGenerateOrder:
    """Test GenerateOrder execution tool"""

    @pytest.fixture(autouse=True)
    def setup_random_seed(self):
        """Set random seed for deterministic tests"""
        random.seed(42)

    @pytest.fixture
    def mock_adapter(self):
        """Create mock adapter"""
        adapter = MockAdapter()
        # Connect adapter (async method)
        asyncio.run(adapter.connect())
        return adapter

    @pytest.fixture
    def bridge(self, mock_adapter):
        """Create bridge with mock adapter"""
        return MT5ExecutionBridge(adapter=mock_adapter)

    @pytest.fixture
    def tool(self, bridge):
        """Create GenerateOrder tool"""
        return GenerateOrder(bridge=bridge)

    def test_tool_initialization(self, tool):
        """Test tool initialization"""
        assert tool.name == "generate_order"
        assert tool.version == "1.0.0"
        assert tool.tier.value == "execution"
        assert tool.bridge is not None

    def test_tool_without_bridge(self):
        """Test tool without bridge raises error"""
        tool = GenerateOrder(bridge=None)
        result = tool.execute(symbol="EURUSD", direction="LONG", size=0.1)
        assert result.value is None
        assert result.confidence == 0.0
        assert "not initialized" in result.error.lower()

    def test_successful_order_execution(self, tool):
        """Test successful order execution"""
        result = tool.execute(
            symbol="EURUSD",
            direction="LONG",
            size=0.1,
            stop_loss=1.0900,
            take_profit=1.1100,
            confidence=0.85,
            reasoning="RSI oversold + MACD bullish crossover",
        )

        assert result.value is not None
        assert result.value['success'] is True
        assert result.value['order_id'] is not None
        assert result.value['fill_price'] is not None
        assert result.value['fill_volume'] == 0.1
        assert result.value['status'] == 'SUCCESS'
        assert result.confidence == 0.85
        assert result.latency_ms > 0

    def test_short_order_execution(self, tool):
        """Test SHORT order execution"""
        result = tool.execute(symbol="GBPUSD", direction="SHORT", size=0.2, confidence=0.75)

        assert result.value is not None
        assert result.value['success'] is True
        assert result.value['order_id'] is not None

    def test_invalid_direction(self, tool):
        """Test invalid direction"""
        result = tool.execute(
            symbol="EURUSD",
            direction="BUY",  # Invalid, should be LONG or SHORT
            size=0.1,
        )

        assert result.value is None
        assert result.confidence == 0.0
        assert "direction" in result.error.lower()

    def test_invalid_size(self, tool):
        """Test invalid size"""
        result = tool.execute(
            symbol="EURUSD",
            direction="LONG",
            size=-0.1,  # Negative size
        )

        assert result.value is None
        assert result.confidence == 0.0
        assert "positive" in result.error.lower()

    def test_invalid_confidence(self, tool):
        """Test invalid confidence"""
        result = tool.execute(
            symbol="EURUSD",
            direction="LONG",
            size=0.1,
            confidence=1.5,  # Out of range
        )

        assert result.value is None
        assert result.confidence == 0.0
        assert "confidence" in result.error.lower()

    def test_empty_symbol(self, tool):
        """Test empty symbol"""
        result = tool.execute(symbol="", direction="LONG", size=0.1)

        assert result.value is None
        assert result.confidence == 0.0
        assert "symbol" in result.error.lower()

    def test_metadata_completeness(self, tool):
        """Test that metadata includes all expected fields"""
        result = tool.execute(symbol="EURUSD", direction="LONG", size=0.1, confidence=0.8)

        assert result.value is not None
        assert 'signal_id' in result.metadata
        assert 'execution_time_ms' in result.metadata
        assert 'symbol' in result.metadata
        assert 'direction' in result.metadata
        assert 'size' in result.metadata
        assert result.metadata['symbol'] == "EURUSD"
        assert result.metadata['direction'] == "LONG"
        assert result.metadata['size'] == 0.1

    def test_schema_generation(self, tool):
        """Test JSON schema for LLM function calling"""
        schema = tool.get_schema()

        assert schema['name'] == 'generate_order'
        assert 'description' in schema
        assert 'parameters' in schema

        params = schema['parameters']
        assert params['type'] == 'object'
        assert 'properties' in params
        assert 'required' in params

        # Check required fields
        assert 'symbol' in params['required']
        assert 'direction' in params['required']
        assert 'size' in params['required']

        # Check properties
        props = params['properties']
        assert 'symbol' in props
        assert 'direction' in props
        assert 'size' in props
        assert 'stop_loss' in props
        assert 'take_profit' in props
        assert 'confidence' in props
        assert 'reasoning' in props

        # Check direction enum
        assert props['direction']['enum'] == ['LONG', 'SHORT']

    def test_latency_measurement(self, tool):
        """Test latency measurement"""
        result = tool.execute(symbol="EURUSD", direction="LONG", size=0.1)

        assert result.latency_ms > 0
        # Should be reasonably fast (< 1000ms for mock)
        assert result.latency_ms < 1000

    def test_multiple_orders(self, tool):
        """Test executing multiple orders"""
        symbols = ["EURUSD", "GBPUSD", "USDJPY"]
        results = []

        for symbol in symbols:
            result = tool.execute(symbol=symbol, direction="LONG", size=0.1, confidence=0.8)
            results.append(result)

        # All should succeed
        assert all(r.value is not None for r in results)
        assert all(r.value['success'] for r in results)

        # Each should have unique order ID
        order_ids = [r.value['order_id'] for r in results]
        assert len(set(order_ids)) == len(order_ids)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
