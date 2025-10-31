"""
Tests for new tools: Bollinger Bands, Risk, and TechnicalOverview
"""

import os
import sys

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.trading_agent.tools import (
    CalcBollingerBands,
    RiskFixedFractional,
    TechnicalOverview,
)


class TestCalcBollingerBands:
    """Test Bollinger Bands calculation"""

    def test_bb_basic_calculation(self):
        """Test basic BB calculation"""
        bb = CalcBollingerBands(period=20, std_multiplier=2.0)

        # Generate uptrend prices
        prices = [100 + i * 0.5 for i in range(30)]

        result = bb.execute(prices=prices)

        assert result.value is not None
        assert 'upper_band' in result.value
        assert 'middle_band' in result.value
        assert 'lower_band' in result.value
        assert result.value['upper_band'] > result.value['middle_band']
        assert result.value['middle_band'] > result.value['lower_band']
        assert result.confidence > 0.7

    def test_bb_overbought(self):
        """Test BB overbought detection"""
        bb = CalcBollingerBands(period=20)

        # Prices near upper band
        prices = [100] * 20 + [110, 115, 120]

        result = bb.execute(prices=prices)

        assert result.value is not None
        assert result.value['band_position'] > 0.5  # Near upper band

    def test_bb_oversold(self):
        """Test BB oversold detection"""
        bb = CalcBollingerBands(period=20)

        # Prices near lower band
        prices = [100] * 20 + [90, 85, 80]

        result = bb.execute(prices=prices)

        assert result.value is not None
        assert result.value['band_position'] < -0.5  # Near lower band

    def test_bb_insufficient_data(self):
        """Test BB with insufficient data"""
        bb = CalcBollingerBands(period=20)

        prices = [100, 101, 102]  # Only 3 prices

        result = bb.execute(prices=prices)

        assert result.value is None
        assert result.error is not None
        assert result.confidence == 0.0

    def test_bb_latency(self):
        """Test BB calculation latency"""
        bb = CalcBollingerBands(period=20)

        prices = [100 + i * 0.3 for i in range(50)]

        result = bb.execute(prices=prices)

        assert result.latency_ms < 5.0  # Should be under 5ms


class TestRiskFixedFractional:
    """Test Risk calculation"""

    def test_risk_basic_calculation(self):
        """Test basic risk calculation"""
        risk = RiskFixedFractional()

        result = risk.execute(
            balance=10000,
            risk_pct=0.01,  # 1%
            stop_loss_pips=20,
            symbol="EURUSD"
        )

        assert result.value is not None
        assert 'position_size' in result.value
        assert result.value['position_size'] > 0
        assert result.value['risk_amount'] == 100  # 1% of 10000
        assert result.confidence > 0.9  # High confidence

    def test_risk_jpy_pair(self):
        """Test risk calculation for JPY pair"""
        risk = RiskFixedFractional()

        result = risk.execute(
            balance=10000,
            risk_pct=0.01,
            stop_loss_pips=20,
            symbol="USDJPY"
        )

        assert result.value is not None
        assert result.value['position_size'] > 0

    def test_risk_validation(self):
        """Test risk input validation"""
        risk = RiskFixedFractional()

        # Negative balance
        result = risk.execute(
            balance=-1000,
            risk_pct=0.01,
            stop_loss_pips=20,
            symbol="EURUSD"
        )
        assert result.error is not None

        # Excessive risk
        result = risk.execute(
            balance=10000,
            risk_pct=0.5,  # 50% - too high
            stop_loss_pips=20,
            symbol="EURUSD"
        )
        assert result.error is not None

    def test_risk_latency(self):
        """Test risk calculation latency"""
        risk = RiskFixedFractional()

        result = risk.execute(
            balance=10000,
            risk_pct=0.01,
            stop_loss_pips=20,
            symbol="EURUSD"
        )

        assert result.latency_ms < 5.0  # Should be under 5ms


class TestTechnicalOverview:
    """Test TechnicalOverview composite tool"""

    def test_overview_basic(self):
        """Test basic technical overview"""
        overview = TechnicalOverview()

        # Generate price series
        prices = [100 + i * 0.5 for i in range(50)]

        result = overview.execute(prices=prices)

        assert result.value is not None
        assert 'aggregated_signal' in result.value
        assert 'agreement_score' in result.value
        assert 'individual_signals' in result.value
        assert 'indicators' in result.value

    def test_overview_bullish_consensus(self):
        """Test bullish consensus detection"""
        overview = TechnicalOverview()

        # Strong uptrend
        prices = [100 + i * 1.0 for i in range(50)]

        result = overview.execute(prices=prices)

        assert result.value is not None
        # Should have some bullish signals
        signals = result.value['individual_signals']
        bullish_count = sum(1 for s in signals.values() if s == 'bullish')
        assert bullish_count >= 1

    def test_overview_agreement_score(self):
        """Test agreement score calculation"""
        overview = TechnicalOverview()

        prices = [100 + i * 0.5 for i in range(50)]

        result = overview.execute(prices=prices)

        assert result.value is not None
        assert 0.0 <= result.value['agreement_score'] <= 1.0

    def test_overview_confidence(self):
        """Test combined confidence"""
        overview = TechnicalOverview()

        prices = [100 + i * 0.5 for i in range(50)]

        result = overview.execute(prices=prices)

        assert result.confidence > 0.0
        assert result.confidence <= 1.0

    def test_overview_insufficient_data(self):
        """Test overview with insufficient data"""
        overview = TechnicalOverview()

        prices = [100, 101, 102]  # Only 3 prices

        result = overview.execute(prices=prices)

        assert result.value is None
        assert result.error is not None

    def test_overview_latency(self):
        """Test overview calculation latency"""
        overview = TechnicalOverview()

        prices = [100 + i * 0.3 for i in range(50)]

        result = overview.execute(prices=prices)

        assert result.latency_ms < 50.0  # Composite tool, allow 50ms


class TestIntegration:
    """Integration tests"""

    def test_full_workflow(self):
        """Test complete workflow: analysis → risk → decision"""
        # 1. Technical analysis
        overview = TechnicalOverview()
        prices = [100 + i * 0.5 for i in range(50)]

        analysis = overview.execute(prices=prices)

        assert analysis.value is not None
        assert analysis.is_high_confidence  # Should be high confidence

        # 2. Risk calculation
        risk = RiskFixedFractional()

        position = risk.execute(
            balance=10000,
            risk_pct=0.01,
            stop_loss_pips=20,
            symbol="EURUSD"
        )

        assert position.value is not None
        assert position.value['position_size'] > 0

        # 3. Decision logic
        if analysis.is_high_confidence and position.is_high_confidence:
            signal = analysis.value['aggregated_signal']
            size = position.value['position_size']

            assert signal in ['bullish', 'bearish', 'neutral']
            assert size > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
