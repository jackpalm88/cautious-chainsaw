"""
Tests for RiskFixedFractional with Symbol Normalization
"""

import os
import sys

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.trading_agent.core.symbol_normalization import (
    NormalizedSymbolInfo,
    UniversalSymbolNormalizer,
)
from src.trading_agent.tools.atomic.calc_risk import RiskFixedFractional


class MockAdapter:
    """Mock adapter for testing"""

    def __init__(self, mock_data: dict):
        self.mock_data = mock_data

    def get_symbol_info(self, symbol: str) -> dict:
        """Return mock symbol info"""
        return self.mock_data.get(symbol, {})


class MockBrokerNormalizer:
    """Mock normalizer for testing"""

    def __init__(self, mock_data: dict):
        self.mock_data = mock_data
        self.adapter = MockAdapter(mock_data)

    def parse_symbol_info(self, raw_info: dict) -> NormalizedSymbolInfo:
        """Return mock symbol info"""
        # raw_info is the mock_data for the symbol
        return NormalizedSymbolInfo(
            symbol=raw_info.get('symbol', 'EURUSD'),
            category=raw_info.get('category', 'forex'),
            base_currency=raw_info.get('base_currency', 'EUR'),
            quote_currency=raw_info.get('quote_currency', 'USD'),
            min_size=raw_info.get('min_size', 0.01),
            max_size=raw_info.get('max_size', 100.0),
            size_step=raw_info.get('size_step', 0.01),
            price_precision=raw_info.get('price_precision', 5),
            min_price_move=raw_info.get('min_price_move', 0.00001),
            value_per_tick=raw_info.get('value_per_tick', 1.0),
            contract_multiplier=raw_info.get('contract_multiplier', 100000.0),
        )


class TestRiskWithNormalizer:
    """Test RiskFixedFractional with normalizer integration"""

    def test_fx_major_with_normalizer(self):
        """Test FX major (EURUSD) with normalizer"""
        # Setup mock normalizer
        mock_data = {
            'EURUSD': {
                'symbol': 'EURUSD',
                'category': 'forex',
                'base_currency': 'EUR',
                'quote_currency': 'USD',
                'min_size': 0.01,
                'max_size': 100.0,
                'size_step': 0.01,
                'price_precision': 5,
                'min_price_move': 0.00001,
                'value_per_tick': 1.0,
                'contract_multiplier': 100000.0,
            }
        }

        broker_normalizer = MockBrokerNormalizer(mock_data)
        normalizer = UniversalSymbolNormalizer(broker_normalizer)

        # Create risk tool with normalizer
        risk_tool = RiskFixedFractional(normalizer=normalizer)

        # Execute
        result = risk_tool.execute(
            balance=10000,
            risk_pct=0.01,
            stop_loss_pips=20,
            symbol="EURUSD"
        )

        assert result.value is not None
        assert result.value['position_size'] > 0
        assert result.value['risk_amount'] == 100.0
        assert result.metadata['calculation_method'] == 'normalized'
        assert 'symbol_info' in result.metadata

    def test_jpy_pair_with_normalizer(self):
        """Test JPY pair (USDJPY) with normalizer"""
        mock_data = {
            'USDJPY': {
                'symbol': 'USDJPY',
                'category': 'forex',
                'base_currency': 'USD',
                'quote_currency': 'JPY',
                'min_size': 0.01,
                'max_size': 100.0,
                'size_step': 0.01,
                'price_precision': 3,
                'min_price_move': 0.001,
                'value_per_tick': 1.0,
                'contract_multiplier': 100000.0,
            }
        }

        broker_normalizer = MockBrokerNormalizer(mock_data)
        normalizer = UniversalSymbolNormalizer(broker_normalizer)

        risk_tool = RiskFixedFractional(normalizer=normalizer)

        result = risk_tool.execute(
            balance=10000,
            risk_pct=0.01,
            stop_loss_pips=20,
            symbol="USDJPY"
        )

        assert result.value is not None
        assert result.value['position_size'] > 0
        assert result.metadata['symbol_info']['quote_currency'] == 'JPY'

    def test_crypto_with_normalizer(self):
        """Test crypto (BTCUSDT) with normalizer"""
        mock_data = {
            'BTCUSDT': {
                'symbol': 'BTCUSDT',
                'category': 'crypto',
                'base_currency': 'BTC',
                'quote_currency': 'USDT',
                'min_size': 0.001,
                'max_size': 100.0,
                'size_step': 0.001,
                'price_precision': 2,
                'min_price_move': 0.01,
                'value_per_tick': 0.01,  # Dynamic, but mock as fixed
                'contract_multiplier': 1.0,
            }
        }

        broker_normalizer = MockBrokerNormalizer(mock_data)
        normalizer = UniversalSymbolNormalizer(broker_normalizer)

        risk_tool = RiskFixedFractional(normalizer=normalizer)

        result = risk_tool.execute(
            balance=10000,
            risk_pct=0.01,
            stop_loss_pips=100,  # 100 ticks for crypto
            symbol="BTCUSDT"
        )

        assert result.value is not None
        assert result.value['position_size'] > 0
        assert result.metadata['symbol_info']['category'] == 'crypto'
        assert result.metadata['symbol_info']['category'] == 'crypto'

    def test_lot_size_rounding(self):
        """Test lot size rounding with custom step"""
        mock_data = {
            'GBPUSD': {
                'symbol': 'GBPUSD',
                'category': 'forex',
                'base_currency': 'GBP',
                'quote_currency': 'USD',
                'min_size': 0.1,  # Min 0.1 lots
                'max_size': 50.0,
                'size_step': 0.1,  # Step 0.1 lots
                'price_precision': 5,
                'min_price_move': 0.00001,
                'value_per_tick': 1.0,
                'contract_multiplier': 100000.0,
            }
        }

        broker_normalizer = MockBrokerNormalizer(mock_data)
        normalizer = UniversalSymbolNormalizer(broker_normalizer)

        risk_tool = RiskFixedFractional(normalizer=normalizer)

        result = risk_tool.execute(
            balance=10000,
            risk_pct=0.01,
            stop_loss_pips=20,
            symbol="GBPUSD"
        )

        assert result.value is not None
        # Position size should be rounded to 0.1 step
        # Note: Due to floating point precision, check with tolerance
        remainder = result.value['position_size'] % 0.1
        assert remainder < 0.01 or remainder > 0.09, f"Position size {result.value['position_size']} not properly rounded to 0.1 step"
        assert result.value['position_size'] >= 0.1  # Min size

    def test_min_max_lot_constraints(self):
        """Test min/max lot size constraints"""
        mock_data = {
            'XAUUSD': {
                'symbol': 'XAUUSD',
                'category': 'cfd',
                'base_currency': 'XAU',
                'quote_currency': 'USD',
                'min_size': 0.01,
                'max_size': 10.0,  # Max 10 lots
                'size_step': 0.01,
                'price_precision': 2,
                'min_price_move': 0.01,
                'value_per_tick': 1.0,
                'contract_multiplier': 100.0,
            }
        }

        broker_normalizer = MockBrokerNormalizer(mock_data)
        normalizer = UniversalSymbolNormalizer(broker_normalizer)

        risk_tool = RiskFixedFractional(normalizer=normalizer)

        # Try to calculate very large position
        result = risk_tool.execute(
            balance=100000,  # Large balance
            risk_pct=0.05,  # 5% risk
            stop_loss_pips=10,  # Small SL
            symbol="XAUUSD"
        )

        assert result.value is not None
        # Should be clamped to max_size
        assert result.value['position_size'] <= 10.0

    def test_without_normalizer_fallback(self):
        """Test fallback to simplified calculation without normalizer"""
        risk_tool = RiskFixedFractional(normalizer=None)

        result = risk_tool.execute(
            balance=10000,
            risk_pct=0.01,
            stop_loss_pips=20,
            symbol="EURUSD"
        )

        assert result.value is not None
        assert result.value['position_size'] > 0
        assert result.metadata['calculation_method'] == 'simplified'
        assert 'symbol_info' not in result.metadata

    def test_metadata_completeness(self):
        """Test that metadata includes all expected fields"""
        mock_data = {
            'EURUSD': {
                'symbol': 'EURUSD',
                'category': 'forex',
                'base_currency': 'EUR',
                'quote_currency': 'USD',
                'min_size': 0.01,
                'max_size': 100.0,
                'size_step': 0.01,
                'price_precision': 5,
                'min_price_move': 0.00001,
                'value_per_tick': 1.0,
                'contract_multiplier': 100000.0,
            }
        }

        broker_normalizer = MockBrokerNormalizer(mock_data)
        normalizer = UniversalSymbolNormalizer(broker_normalizer)

        risk_tool = RiskFixedFractional(normalizer=normalizer)

        result = risk_tool.execute(
            balance=10000,
            risk_pct=0.01,
            stop_loss_pips=20,
            symbol="EURUSD"
        )

        assert result.value is not None
        assert 'calculation_method' in result.metadata
        assert 'balance' in result.metadata
        assert 'stop_loss_pips' in result.metadata
        assert 'raw_position_size' in result.metadata
        assert 'sl_value_per_lot' in result.metadata
        assert 'symbol_info' in result.metadata

        symbol_info = result.metadata['symbol_info']
        assert 'category' in symbol_info
        assert 'base_currency' in symbol_info
        assert 'quote_currency' in symbol_info
        assert 'min_size' in symbol_info
        assert 'max_size' in symbol_info
        assert 'size_step' in symbol_info


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
