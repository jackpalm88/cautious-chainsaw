"""
Tests for symbol normalization across multiple brokers.

Validates:
- MT5 EURUSD normalization
- Binance BTCUSDT normalization
- Cross-broker consistency
- Edge cases (JPY pairs, crypto)
"""

import json
from pathlib import Path

import pytest

from trading_agent.core.symbol_normalization import (
    BinanceNormalizer,
    MT5Normalizer,
    NormalizedSymbolInfo,
    NormalizerFactory,
    UniversalSymbolNormalizer,
)

# ============= Fixtures =============


@pytest.fixture
def mt5_eurusd_data():
    """Load MT5 EURUSD fixture"""
    fixture_path = Path(__file__).parent.parent / "data" / "fixtures" / "mt5_eurusd.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def binance_btcusdt_data():
    """Load Binance BTCUSDT fixture"""
    fixture_path = Path(__file__).parent.parent / "data" / "fixtures" / "binance_btcusdt.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def mock_mt5_adapter(mt5_eurusd_data):
    """Mock MT5 adapter"""

    class MockAdapter:
        def get_symbol_info(self, symbol):
            return mt5_eurusd_data

        def get_current_price(self, symbol):
            return mt5_eurusd_data["bid"]

    return MockAdapter()


@pytest.fixture
def mock_binance_adapter(binance_btcusdt_data):
    """Mock Binance adapter"""

    class MockAdapter:
        def get_symbol_info(self, symbol):
            return binance_btcusdt_data

        def get_current_price(self, symbol):
            return binance_btcusdt_data["current_price"]

    return MockAdapter()


# ============= Unit Tests =============


@pytest.mark.unit
def test_mt5_normalizer_parse(mock_mt5_adapter, mt5_eurusd_data):
    """Test MT5 normalizer parses symbol info correctly"""
    normalizer = MT5Normalizer(mock_mt5_adapter)
    info = normalizer.parse_symbol_info(mt5_eurusd_data)

    assert isinstance(info, NormalizedSymbolInfo)
    assert info.symbol == "EURUSD"
    assert info.category == "forex"
    assert info.base_currency == "EUR"
    assert info.quote_currency == "USD"
    assert info.min_size == 0.01
    assert info.max_size == 500.0
    assert info.size_step == 0.01
    assert info.price_precision == 5
    assert info.min_price_move == 0.00001
    assert info.value_per_tick == 1.0
    assert info.contract_multiplier == 100000.0


@pytest.mark.unit
def test_binance_normalizer_parse(mock_binance_adapter, binance_btcusdt_data):
    """Test Binance normalizer parses symbol info correctly"""
    normalizer = BinanceNormalizer(mock_binance_adapter)
    info = normalizer.parse_symbol_info(binance_btcusdt_data)

    assert isinstance(info, NormalizedSymbolInfo)
    assert info.symbol == "BTCUSDT"
    assert info.category == "crypto"
    assert info.base_currency == "BTC"
    assert info.quote_currency == "USDT"
    assert info.min_size == 0.00001
    assert info.max_size == 9000.0
    assert info.size_step == 0.00001
    assert info.min_price_move == 0.01
    # Tick value = tick_size * current_price
    assert info.value_per_tick == pytest.approx(0.01 * 67850.50, rel=1e-5)
    assert info.contract_multiplier == 1.0


@pytest.mark.unit
def test_universal_normalizer_to_risk_units_eurusd(mock_mt5_adapter):
    """Test risk unit conversion for EURUSD (20 pips)"""
    normalizer = UniversalSymbolNormalizer(MT5Normalizer(mock_mt5_adapter))

    # 20 pips on EURUSD
    # = 20 * 0.0001 (pip size) * 100,000 (contract) * 1.0 (tick value)
    # = 200.0
    risk = normalizer.to_risk_units("EURUSD", 20, "pips")

    assert risk == pytest.approx(200.0, rel=1e-5)


@pytest.mark.unit
def test_universal_normalizer_round_lot_size(mock_mt5_adapter):
    """Test lot size rounding to valid increments"""
    normalizer = UniversalSymbolNormalizer(MT5Normalizer(mock_mt5_adapter))

    # Min: 0.01, Max: 500.0, Step: 0.01

    # Below min → clamp to min
    assert normalizer.round_to_lot_size("EURUSD", 0.005) == 0.01

    # Above max → clamp to max
    assert normalizer.round_to_lot_size("EURUSD", 600.0) == 500.0

    # Not on step → round to nearest step
    assert normalizer.round_to_lot_size("EURUSD", 0.437) == 0.44

    # Already valid → no change
    assert normalizer.round_to_lot_size("EURUSD", 1.23) == 1.23


@pytest.mark.unit
def test_normalizer_factory():
    """Test factory creates correct normalizer type"""

    class MockAdapter:
        pass

    adapter = MockAdapter()

    mt5_norm = NormalizerFactory.create("mt5", adapter)
    assert isinstance(mt5_norm, MT5Normalizer)

    binance_norm = NormalizerFactory.create("binance", adapter)
    assert isinstance(binance_norm, BinanceNormalizer)

    with pytest.raises(ValueError, match="Unsupported broker type"):
        NormalizerFactory.create("unknown", adapter)


# ============= Integration Tests =============


@pytest.mark.integration
def test_cross_broker_consistency(mock_mt5_adapter, mock_binance_adapter):
    """
    Test that equivalent positions produce similar risk values
    across brokers (accounting for different contract sizes).

    This is a sanity check, not an exact equality assertion.
    """
    mt5_norm = UniversalSymbolNormalizer(MT5Normalizer(mock_mt5_adapter))
    binance_norm = UniversalSymbolNormalizer(BinanceNormalizer(mock_binance_adapter))

    # MT5: 20 pips on EURUSD = $200/lot
    mt5_risk = mt5_norm.to_risk_units("EURUSD", 20, "pips")

    # Binance: Can't directly compare (different asset)
    # But we can verify calculation is reasonable
    # 10 ticks on BTC at $67,850 = 10 * 0.01 * 67,850.50 = $6,785.05
    binance_risk = binance_norm.to_risk_units("BTCUSDT", 10, "ticks")

    assert mt5_risk == pytest.approx(200.0, rel=1e-5)
    assert binance_risk == pytest.approx(6785.05, rel=1e-5)


# ============= Edge Cases =============


@pytest.mark.unit
def test_normalized_symbol_info_validation():
    """Test that NormalizedSymbolInfo validates inputs"""

    # Valid construction
    info = NormalizedSymbolInfo(
        symbol="TEST",
        category="forex",
        base_currency="EUR",
        quote_currency="USD",
        min_size=0.01,
        max_size=100.0,
        size_step=0.01,
        price_precision=5,
        min_price_move=0.00001,
        value_per_tick=1.0,
        contract_multiplier=100000.0,
    )
    assert info.symbol == "TEST"

    # Invalid: min_size <= 0
    with pytest.raises(ValueError, match="min_size must be positive"):
        NormalizedSymbolInfo(
            symbol="TEST",
            category="forex",
            base_currency="EUR",
            quote_currency="USD",
            min_size=-0.01,  # Invalid
            max_size=100.0,
            size_step=0.01,
            price_precision=5,
            min_price_move=0.00001,
            value_per_tick=1.0,
            contract_multiplier=100000.0,
        )

    # Invalid: max_size < min_size
    with pytest.raises(ValueError, match="max_size.*< min_size"):
        NormalizedSymbolInfo(
            symbol="TEST",
            category="forex",
            base_currency="EUR",
            quote_currency="USD",
            min_size=10.0,
            max_size=5.0,  # Invalid
            size_step=0.01,
            price_precision=5,
            min_price_move=0.00001,
            value_per_tick=1.0,
            contract_multiplier=100000.0,
        )


@pytest.mark.unit
def test_jpy_pair_normalization():
    """
    Test JPY pair special handling.

    JPY pairs: 1 pip = 0.01 (not 0.0001)
    """

    class MockAdapter:
        def get_symbol_info(self, symbol):
            return {
                "name": "USDJPY",
                "path": "Forex\\Major",
                "digits": 3,
                "point": 0.001,
                "currency_base": "USD",
                "currency_profit": "JPY",
                "volume_min": 0.01,
                "volume_max": 500.0,
                "volume_step": 0.01,
                "trade_contract_size": 100000.0,
                "trade_tick_value": 9.09,  # At 110.00 rate
            }

    adapter = MockAdapter()
    normalizer = UniversalSymbolNormalizer(MT5Normalizer(adapter))

    # 20 pips on USDJPY
    # = 20 * 0.01 (JPY pip size) * 100,000 * 9.09
    # = 181,800 (in JPY terms, ~ $1,653 at 110.00)
    risk = normalizer.to_risk_units("USDJPY", 20, "pips")

    # Should be 20 * 0.01 * 100,000 * 9.09
    expected = 20 * 0.01 * 100000.0 * 9.09
    assert risk == pytest.approx(expected, rel=1e-5)
