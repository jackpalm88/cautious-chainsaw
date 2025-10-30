"""
Tests for Trading Agent Tools
"""

import pytest
import numpy as np
from src.trading_agent.tools import (
    CalcRSI,
    CalcMACD,
    ToolRegistry,
    get_registry,
)


class TestCalcRSI:
    """Test RSI calculation tool"""
    
    def test_rsi_basic_calculation(self):
        """Test basic RSI calculation"""
        # Generate sample prices (trending up)
        prices = [100 + i * 0.5 for i in range(30)]
        
        rsi_tool = CalcRSI(period=14)
        result = rsi_tool.execute(prices=prices)
        
        assert result.success
        assert 'rsi' in result.value
        assert 0 <= result.value['rsi'] <= 100
        assert result.confidence > 0
        assert result.latency_ms >= 0
    
    def test_rsi_overbought(self):
        """Test RSI overbought detection"""
        # Strong uptrend
        prices = [100 + i * 2 for i in range(30)]
        
        rsi_tool = CalcRSI(period=14)
        result = rsi_tool.execute(prices=prices)
        
        assert result.success
        assert result.value['rsi'] > 70  # Should be overbought
        assert result.value['signal'] == 'bearish'
    
    def test_rsi_oversold(self):
        """Test RSI oversold detection"""
        # Strong downtrend
        prices = [100 - i * 2 for i in range(30)]
        
        rsi_tool = CalcRSI(period=14)
        result = rsi_tool.execute(prices=prices)
        
        assert result.success
        assert result.value['rsi'] < 30  # Should be oversold
        assert result.value['signal'] == 'bullish'
    
    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data"""
        prices = [100, 101, 102]  # Only 3 prices
        
        rsi_tool = CalcRSI(period=14)
        result = rsi_tool.execute(prices=prices)
        
        assert not result.success
        assert result.error is not None
        assert result.confidence == 0.0
    
    def test_rsi_confidence_components(self):
        """Test confidence calculation"""
        prices = [100 + i * 0.5 for i in range(50)]  # Plenty of data
        
        rsi_tool = CalcRSI(period=14)
        result = rsi_tool.execute(prices=prices)
        
        assert result.success
        assert 'confidence_components' in result.metadata
        components = result.metadata['confidence_components']
        
        assert 'sample_sufficiency' in components
        assert 'volatility_regime' in components
        assert 'data_quality' in components
        assert components['sample_sufficiency'] > 0.9  # Plenty of samples


class TestCalcMACD:
    """Test MACD calculation tool"""
    
    def test_macd_basic_calculation(self):
        """Test basic MACD calculation"""
        prices = [100 + i * 0.5 for i in range(50)]
        
        macd_tool = CalcMACD()
        result = macd_tool.execute(prices=prices)
        
        assert result.success
        assert 'macd' in result.value
        assert 'signal' in result.value
        assert 'histogram' in result.value
        assert result.confidence > 0
    
    def test_macd_bullish_signal(self):
        """Test MACD bullish signal"""
        # Create uptrend
        prices = [100 + i * 1.5 for i in range(50)]
        
        macd_tool = CalcMACD()
        result = macd_tool.execute(prices=prices)
        
        assert result.success
        assert result.value['trading_signal'] in ['bullish', 'neutral']
    
    def test_macd_bearish_signal(self):
        """Test MACD bearish signal"""
        # Create downtrend
        prices = [100 - i * 1.5 for i in range(50)]
        
        macd_tool = CalcMACD()
        result = macd_tool.execute(prices=prices)
        
        assert result.success
        assert result.value['trading_signal'] in ['bearish', 'neutral']
    
    def test_macd_insufficient_data(self):
        """Test MACD with insufficient data"""
        prices = [100, 101, 102]
        
        macd_tool = CalcMACD()
        result = macd_tool.execute(prices=prices)
        
        assert not result.success
        assert result.error is not None


class TestToolRegistry:
    """Test Tool Registry"""
    
    def test_registry_registration(self):
        """Test tool registration"""
        registry = ToolRegistry()
        
        rsi_tool = CalcRSI()
        registry.register(rsi_tool)
        
        assert len(registry) == 1
        assert 'calc_rsi' in registry
        assert registry.get('calc_rsi') is rsi_tool
    
    def test_registry_duplicate_registration(self):
        """Test duplicate tool registration raises error"""
        registry = ToolRegistry()
        
        rsi_tool = CalcRSI()
        registry.register(rsi_tool)
        
        with pytest.raises(ValueError):
            registry.register(rsi_tool)
    
    def test_registry_catalog_export(self):
        """Test catalog export for LLM"""
        registry = ToolRegistry()
        
        rsi_tool = CalcRSI()
        macd_tool = CalcMACD()
        
        registry.register(rsi_tool)
        registry.register(macd_tool)
        
        catalog = registry.catalog()
        
        assert 'version' in catalog
        assert 'total_tools' in catalog
        assert catalog['total_tools'] == 2
        assert 'tools' in catalog
        assert len(catalog['tools']) == 2
    
    def test_registry_llm_functions(self):
        """Test LLM function schema export"""
        registry = ToolRegistry()
        
        rsi_tool = CalcRSI()
        registry.register(rsi_tool)
        
        functions = registry.get_llm_functions()
        
        assert len(functions) == 1
        assert functions[0]['name'] == 'calc_rsi'
        assert 'parameters' in functions[0]
        assert 'properties' in functions[0]['parameters']


class TestPerformance:
    """Test performance requirements"""
    
    def test_atomic_tool_latency(self):
        """Test atomic tools meet <5ms p95 latency target"""
        prices = [100 + i * 0.5 for i in range(100)]
        
        # Run RSI multiple times
        rsi_tool = CalcRSI()
        latencies = []
        
        for _ in range(20):
            result = rsi_tool.execute(prices=prices)
            latencies.append(result.latency_ms)
        
        p95_latency = np.percentile(latencies, 95)
        
        # Atomic tools should be <5ms p95
        assert p95_latency < 5.0, f"P95 latency {p95_latency}ms exceeds 5ms target"
    
    def test_macd_latency(self):
        """Test MACD latency"""
        prices = [100 + i * 0.5 for i in range(100)]
        
        macd_tool = CalcMACD()
        latencies = []
        
        for _ in range(20):
            result = macd_tool.execute(prices=prices)
            latencies.append(result.latency_ms)
        
        p95_latency = np.percentile(latencies, 95)
        
        # Should still be very fast
        assert p95_latency < 10.0, f"P95 latency {p95_latency}ms too high"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
