"""
Demo: RiskFixedFractional with Symbol Normalization
Demonstrates multi-broker position sizing with accurate normalization
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.trading_agent.core.symbol_normalization import (
    NormalizedSymbolInfo,
    UniversalSymbolNormalizer,
)
from src.trading_agent.tools.atomic.calc_risk import RiskFixedFractional


class DemoMockAdapter:
    """Mock adapter for demo purposes"""

    def __init__(self, mock_data: dict):
        self.mock_data = mock_data

    def get_symbol_info(self, symbol: str) -> dict:
        """Return mock symbol info"""
        return self.mock_data.get(symbol, {})


class DemoMockNormalizer:
    """Mock normalizer for demo"""

    def __init__(self, mock_data: dict):
        self.mock_data = mock_data
        self.adapter = DemoMockAdapter(mock_data)

    def parse_symbol_info(self, raw_info: dict) -> NormalizedSymbolInfo:
        """Return mock symbol info"""
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


def demo_fx_major():
    """Demo FX major (EURUSD) with normalizer"""
    print("=" * 60)
    print("FX MAJOR (EURUSD) WITH NORMALIZER")
    print("=" * 60)

    # Setup mock data
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

    broker_normalizer = DemoMockNormalizer(mock_data)
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

    print(f"\nAccount Balance: ${result.metadata['balance']:.2f}")
    print(f"Risk: {result.value['risk_pct'] * 100:.1f}%")
    print(f"Stop Loss: {result.metadata['stop_loss_pips']} pips")
    print("\n📊 CALCULATION:")
    print(f"  Risk Amount: ${result.value['risk_amount']:.2f}")
    print(f"  SL Value per Lot: ${result.value['stop_loss_value']:.2f}")
    print(f"  Raw Position Size: {result.metadata['raw_position_size']:.4f} lots")
    print(f"  Final Position Size: {result.value['position_size']:.2f} lots")
    print("\n📋 SYMBOL INFO:")
    print(f"  Category: {result.metadata['symbol_info']['category']}")
    print(f"  Base/Quote: {result.metadata['symbol_info']['base_currency']}/{result.metadata['symbol_info']['quote_currency']}")
    print(f"  Lot Constraints: {result.metadata['symbol_info']['min_size']:.2f} - {result.metadata['symbol_info']['max_size']:.2f}")
    print(f"  Lot Step: {result.metadata['symbol_info']['size_step']:.2f}")
    print("\n⚡ Performance:")
    print(f"  Latency: {result.latency_ms:.2f}ms")
    print(f"  Confidence: {result.confidence:.3f}")
    print(f"  Method: {result.metadata['calculation_method']}")


def demo_jpy_pair():
    """Demo JPY pair (USDJPY) with normalizer"""
    print("\n" + "=" * 60)
    print("JPY PAIR (USDJPY) WITH NORMALIZER")
    print("=" * 60)

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

    broker_normalizer = DemoMockNormalizer(mock_data)
    normalizer = UniversalSymbolNormalizer(broker_normalizer)
    risk_tool = RiskFixedFractional(normalizer=normalizer)

    result = risk_tool.execute(
        balance=10000,
        risk_pct=0.01,
        stop_loss_pips=20,
        symbol="USDJPY"
    )

    print(f"\nAccount Balance: ${result.metadata['balance']:.2f}")
    print(f"Risk: {result.value['risk_pct'] * 100:.1f}%")
    print(f"Stop Loss: {result.metadata['stop_loss_pips']} pips")
    print("\n📊 CALCULATION:")
    print(f"  Position Size: {result.value['position_size']:.2f} lots")
    print(f"  Risk Amount: ${result.value['risk_amount']:.2f}")
    print("\n📋 SYMBOL INFO:")
    print(f"  Quote Currency: {result.metadata['symbol_info']['quote_currency']} (JPY pairs use 0.01 pip value)")


def demo_crypto():
    """Demo crypto (BTCUSDT) with normalizer"""
    print("\n" + "=" * 60)
    print("CRYPTO (BTCUSDT) WITH NORMALIZER")
    print("=" * 60)

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
            'value_per_tick': 0.01,
            'contract_multiplier': 1.0,
        }
    }

    broker_normalizer = DemoMockNormalizer(mock_data)
    normalizer = UniversalSymbolNormalizer(broker_normalizer)
    risk_tool = RiskFixedFractional(normalizer=normalizer)

    result = risk_tool.execute(
        balance=10000,
        risk_pct=0.01,
        stop_loss_pips=100,  # 100 ticks for crypto
        symbol="BTCUSDT"
    )

    print(f"\nAccount Balance: ${result.metadata['balance']:.2f}")
    print(f"Risk: {result.value['risk_pct'] * 100:.1f}%")
    print(f"Stop Loss: {result.metadata['stop_loss_pips']} ticks")
    print("\n📊 CALCULATION:")
    print(f"  Position Size: {result.value['position_size']:.3f} BTC")
    print(f"  Risk Amount: ${result.value['risk_amount']:.2f}")
    print("\n📋 SYMBOL INFO:")
    print(f"  Category: {result.metadata['symbol_info']['category']}")
    print(f"  Min Size: {result.metadata['symbol_info']['min_size']} BTC")
    print("  Note: Crypto uses 1:1 contract multiplier (spot trading)")


def demo_cfd():
    """Demo CFD (XAUUSD - Gold) with normalizer"""
    print("\n" + "=" * 60)
    print("CFD (XAUUSD - GOLD) WITH NORMALIZER")
    print("=" * 60)

    mock_data = {
        'XAUUSD': {
            'symbol': 'XAUUSD',
            'category': 'cfd',
            'base_currency': 'XAU',
            'quote_currency': 'USD',
            'min_size': 0.01,
            'max_size': 10.0,
            'size_step': 0.01,
            'price_precision': 2,
            'min_price_move': 0.01,
            'value_per_tick': 1.0,
            'contract_multiplier': 100.0,
        }
    }

    broker_normalizer = DemoMockNormalizer(mock_data)
    normalizer = UniversalSymbolNormalizer(broker_normalizer)
    risk_tool = RiskFixedFractional(normalizer=normalizer)

    result = risk_tool.execute(
        balance=10000,
        risk_pct=0.01,
        stop_loss_pips=50,
        symbol="XAUUSD"
    )

    print(f"\nAccount Balance: ${result.metadata['balance']:.2f}")
    print(f"Risk: {result.value['risk_pct'] * 100:.1f}%")
    print(f"Stop Loss: {result.metadata['stop_loss_pips']} points")
    print("\n📊 CALCULATION:")
    print(f"  Position Size: {result.value['position_size']:.2f} lots")
    print(f"  Risk Amount: ${result.value['risk_amount']:.2f}")
    print("\n📋 SYMBOL INFO:")
    print(f"  Category: {result.metadata['symbol_info']['category']}")
    print(f"  Max Size: {result.metadata['symbol_info']['max_size']} lots (CFD often has lower limits)")


def demo_comparison():
    """Compare with and without normalizer"""
    print("\n" + "=" * 60)
    print("COMPARISON: WITH vs WITHOUT NORMALIZER")
    print("=" * 60)

    # Without normalizer
    risk_tool_simple = RiskFixedFractional(normalizer=None)
    result_simple = risk_tool_simple.execute(
        balance=10000,
        risk_pct=0.01,
        stop_loss_pips=20,
        symbol="EURUSD"
    )

    # With normalizer
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
    broker_normalizer = DemoMockNormalizer(mock_data)
    normalizer = UniversalSymbolNormalizer(broker_normalizer)
    risk_tool_normalized = RiskFixedFractional(normalizer=normalizer)
    result_normalized = risk_tool_normalized.execute(
        balance=10000,
        risk_pct=0.01,
        stop_loss_pips=20,
        symbol="EURUSD"
    )

    print("\n📊 WITHOUT NORMALIZER (Simplified):")
    print(f"  Method: {result_simple.metadata['calculation_method']}")
    print(f"  Position Size: {result_simple.value['position_size']:.2f} lots")
    print("  Symbol Info: Not available")

    print("\n📊 WITH NORMALIZER (Full):")
    print(f"  Method: {result_normalized.metadata['calculation_method']}")
    print(f"  Position Size: {result_normalized.value['position_size']:.2f} lots")
    print(f"  Symbol Info: Available ({result_normalized.metadata['symbol_info']['category']}, {result_normalized.metadata['symbol_info']['base_currency']}/{result_normalized.metadata['symbol_info']['quote_currency']})")

    print("\n✅ Benefits of Normalizer:")
    print("  - Accurate multi-broker calculations")
    print("  - Proper lot size rounding")
    print("  - Support for all asset types (FX, JPY, crypto, CFD)")
    print("  - Min/max lot constraints")
    print("  - Symbol metadata for validation")


def main():
    """Run all demos"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 5 + "RISK CALCULATION WITH SYMBOL NORMALIZATION" + " " * 10 + "║")
    print("╚" + "=" * 58 + "╝")

    demo_fx_major()
    demo_jpy_pair()
    demo_crypto()
    demo_cfd()
    demo_comparison()

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\n✅ Symbol Normalization Integration:")
    print("  - FX majors: ✅ EURUSD")
    print("  - JPY pairs: ✅ USDJPY")
    print("  - Crypto: ✅ BTCUSDT")
    print("  - CFD: ✅ XAUUSD")
    print("  - Multi-broker support: ✅ MT5, Binance, IBKR (stub)")
    print()


if __name__ == '__main__':
    main()
