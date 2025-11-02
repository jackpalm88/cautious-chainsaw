"""
Tests for Memory Models
"""

from datetime import datetime

import pytest

from trading_agent.memory.models import MemorySnapshot, Pattern, StoredDecision, TradeOutcome


class TestStoredDecision:
    """Test StoredDecision model."""

    def test_create_decision(self):
        """Test creating a decision."""
        decision = StoredDecision(
            id="test-001",
            timestamp=datetime.utcnow(),
            symbol="EURUSD",
            action="BUY",
            confidence=0.75,
            lots=0.1,
            stop_loss=1.0800,
            take_profit=1.1000,
            price=1.0900,
            rsi=35.0,
            macd=0.0005,
            bb_position="LOWER",
            regime="TRENDING",
        )

        assert decision.id == "test-001"
        assert decision.action == "BUY"
        assert decision.confidence == 0.75
        assert decision.symbol == "EURUSD"

    def test_decision_to_dict(self):
        """Test converting decision to dict."""
        decision = StoredDecision(
            id="test-002",
            timestamp=datetime(2025, 11, 2, 10, 30),
            symbol="GBPUSD",
            action="SELL",
            confidence=0.82,
            lots=0.2,
            price=1.2500,
        )

        d = decision.to_dict()

        assert d['id'] == "test-002"
        assert d['action'] == "SELL"
        assert d['confidence'] == 0.82
        assert isinstance(d['timestamp'], str)  # ISO format


class TestTradeOutcome:
    """Test TradeOutcome model."""

    def test_create_outcome_win(self):
        """Test creating a win outcome."""
        outcome = TradeOutcome(
            decision_id="test-001",
            closed_at=datetime.utcnow(),
            result="WIN",
            pips=50.0,
            duration_minutes=120,
            exit_reason="TP",
            fill_price=1.0900,
            exit_price=1.0950,
        )

        assert outcome.result == "WIN"
        assert outcome.pips == 50.0
        assert outcome.exit_reason == "TP"

    def test_create_outcome_loss(self):
        """Test creating a loss outcome."""
        outcome = TradeOutcome(
            decision_id="test-002",
            closed_at=datetime.utcnow(),
            result="LOSS",
            pips=-20.0,
            duration_minutes=30,
            exit_reason="SL",
            fill_price=1.2500,
            exit_price=1.2480,
        )

        assert outcome.result == "LOSS"
        assert outcome.pips == -20.0
        assert outcome.exit_reason == "SL"

    def test_outcome_to_dict(self):
        """Test converting outcome to dict."""
        outcome = TradeOutcome(
            decision_id="test-003",
            closed_at=datetime(2025, 11, 2, 12, 0),
            result="BREAKEVEN",
            pips=0.0,
            duration_minutes=60,
            exit_reason="MANUAL",
        )

        d = outcome.to_dict()

        assert d['decision_id'] == "test-003"
        assert d['result'] == "BREAKEVEN"
        assert d['pips'] == 0.0


class TestPattern:
    """Test Pattern model."""

    def test_create_pattern(self):
        """Test creating a pattern."""
        pattern = Pattern(
            pattern_id="RSI_30-40_BULLISH_TRENDING",
            rsi_min=30.0,
            rsi_max=40.0,
            macd_signal="BULLISH",
            regime="TRENDING",
            win_rate=0.72,
            avg_pips=45.0,
            sample_size=25,
        )

        assert pattern.win_rate == 0.72
        assert pattern.sample_size == 25
        assert pattern.macd_signal == "BULLISH"

    def test_pattern_to_dict(self):
        """Test converting pattern to dict."""
        pattern = Pattern(
            pattern_id="TEST_PATTERN",
            rsi_min=50.0,
            rsi_max=60.0,
            macd_signal="BEARISH",
            win_rate=0.65,
            avg_pips=30.0,
            sample_size=15,
            last_updated=datetime(2025, 11, 2),
        )

        d = pattern.to_dict()

        assert d['pattern_id'] == "TEST_PATTERN"
        assert d['win_rate'] == 0.65
        assert isinstance(d['last_updated'], str)


class TestMemorySnapshot:
    """Test MemorySnapshot model."""

    def test_create_snapshot(self):
        """Test creating a memory snapshot."""
        snapshot = MemorySnapshot(
            recent_decisions=[
                {'id': '001', 'action': 'BUY', 'confidence': 0.75},
                {'id': '002', 'action': 'SELL', 'confidence': 0.80},
            ],
            current_regime="TRENDING",
            win_rate_30d=0.65,
            avg_win_pips=45.0,
            avg_loss_pips=20.0,
            total_trades_30d=20,
        )

        assert len(snapshot.recent_decisions) == 2
        assert snapshot.win_rate_30d == 0.65
        assert snapshot.current_regime == "TRENDING"

    def test_snapshot_to_summary(self):
        """Test converting snapshot to text summary."""
        snapshot = MemorySnapshot(
            recent_decisions=[
                {'action': 'BUY', 'symbol': 'EURUSD', 'confidence': 0.75},
                {'action': 'SELL', 'symbol': 'GBPUSD', 'confidence': 0.80},
                {'action': 'HOLD', 'symbol': 'USDJPY', 'confidence': 0.60},
            ],
            current_regime="RANGING",
            win_rate_30d=0.68,
            avg_win_pips=50.0,
            avg_loss_pips=25.0,
            total_trades_30d=30,
            similar_patterns=[
                {'win_rate': 0.72, 'sample_size': 20},
                {'win_rate': 0.65, 'sample_size': 15},
            ],
        )

        summary = snapshot.to_summary()

        assert "68.0% win rate" in summary
        assert "RANGING" in summary
        assert "Last 3 Decisions" in summary
        assert "Similar Patterns Found: 2" in summary

    def test_empty_snapshot(self):
        """Test empty snapshot."""
        snapshot = MemorySnapshot()

        assert snapshot.recent_decisions == []
        assert snapshot.win_rate_30d is None
        assert snapshot.current_regime is None

        summary = snapshot.to_summary()
        assert summary == ""

    def test_snapshot_to_dict(self):
        """Test converting snapshot to dict."""
        snapshot = MemorySnapshot(
            recent_decisions=[{'id': '001'}],
            current_regime="TRENDING",
            win_rate_30d=0.70,
            total_trades_30d=10,
        )

        d = snapshot.to_dict()

        assert d['current_regime'] == "TRENDING"
        assert d['win_rate_30d'] == 0.70
        assert len(d['recent_decisions']) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
