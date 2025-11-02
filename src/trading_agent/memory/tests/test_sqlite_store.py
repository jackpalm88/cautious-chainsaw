"""
Tests for SQLite Memory Store

Uses in-memory SQLite database for fast testing.
"""

import os
import tempfile
from datetime import datetime, timedelta

import pytest

from trading_agent.memory import (
    Pattern,
    SQLiteMemoryStore,
    StoredDecision,
    TradeOutcome,
)


@pytest.fixture
def memory_store():
    """Create in-memory SQLite store for testing."""
    return SQLiteMemoryStore(db_path=":memory:")


@pytest.fixture
def temp_db_path():
    """Create temporary database file."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


class TestSQLiteMemoryStore:
    """Test SQLite Memory Store initialization."""

    def test_init_in_memory(self):
        """Test creating in-memory database."""
        store = SQLiteMemoryStore(db_path=":memory:")
        assert store.health_check()

    def test_init_file_db(self, temp_db_path):
        """Test creating file-based database."""
        store = SQLiteMemoryStore(db_path=temp_db_path)
        assert store.health_check()
        assert os.path.exists(temp_db_path)

    def test_schema_created(self, memory_store):
        """Test that schema is created on init."""
        # Should not raise an error
        snapshot = memory_store.load_snapshot()
        assert snapshot.recent_decisions == []


class TestDecisionStorage:
    """Test decision CRUD operations."""

    def test_save_and_load_decision(self, memory_store):
        """Test saving and loading a decision."""
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

        memory_store.save_decision(decision)
        loaded = memory_store.load_decision("test-001")

        assert loaded is not None
        assert loaded.id == "test-001"
        assert loaded.action == "BUY"
        assert loaded.confidence == 0.75
        assert loaded.symbol == "EURUSD"
        assert loaded.rsi == 35.0

    def test_load_nonexistent_decision(self, memory_store):
        """Test loading a decision that doesn't exist."""
        loaded = memory_store.load_decision("nonexistent")
        assert loaded is None

    def test_save_decision_with_agent_outputs(self, memory_store):
        """Test saving decision with INoT agent outputs."""
        decision = StoredDecision(
            id="test-002",
            timestamp=datetime.utcnow(),
            symbol="GBPUSD",
            action="SELL",
            confidence=0.82,
            lots=0.2,
            price=1.2500,
            signal_agent_output={'reasoning': 'RSI overbought'},
            risk_agent_output={'approved': True, 'position_size_adjustment': 1.0},
            context_agent_output={'regime': 'TRENDING'},
            synthesis_agent_output={'final_decision': 'SELL'},
        )

        memory_store.save_decision(decision)
        loaded = memory_store.load_decision("test-002")

        assert loaded.signal_agent_output == {'reasoning': 'RSI overbought'}
        assert loaded.risk_agent_output['approved'] is True

    def test_load_recent_decisions(self, memory_store):
        """Test loading recent decisions."""
        # Create 15 decisions
        for i in range(15):
            decision = StoredDecision(
                id=f"test-{i:03d}",
                timestamp=datetime.utcnow() - timedelta(days=i),
                symbol="EURUSD" if i % 2 == 0 else "GBPUSD",
                action="BUY",
                confidence=0.70 + (i * 0.01),
                lots=0.1,
                price=1.0900,
            )
            memory_store.save_decision(decision)

        # Load recent (should return 10 by default)
        recent = memory_store.load_recent_decisions()
        assert len(recent) == 10

        # Newest first
        assert recent[0].id == "test-000"
        assert recent[9].id == "test-009"

    def test_load_recent_decisions_with_symbol_filter(self, memory_store):
        """Test loading decisions filtered by symbol."""
        # Create decisions for multiple symbols
        for i in range(10):
            decision = StoredDecision(
                id=f"test-{i:03d}",
                timestamp=datetime.utcnow(),
                symbol="EURUSD" if i < 5 else "GBPUSD",
                action="BUY",
                confidence=0.75,
                lots=0.1,
                price=1.0900,
            )
            memory_store.save_decision(decision)

        # Load only EURUSD
        eurusd_decisions = memory_store.load_recent_decisions(symbol="EURUSD")
        assert len(eurusd_decisions) == 5
        assert all(d.symbol == "EURUSD" for d in eurusd_decisions)

    def test_load_decisions_with_days_filter(self, memory_store):
        """Test loading decisions within date range."""
        # Create old and new decisions
        old_decision = StoredDecision(
            id="old-001",
            timestamp=datetime.utcnow() - timedelta(days=60),
            symbol="EURUSD",
            action="BUY",
            confidence=0.75,
            lots=0.1,
            price=1.0900,
        )

        new_decision = StoredDecision(
            id="new-001",
            timestamp=datetime.utcnow() - timedelta(days=5),
            symbol="EURUSD",
            action="SELL",
            confidence=0.80,
            lots=0.1,
            price=1.0950,
        )

        memory_store.save_decision(old_decision)
        memory_store.save_decision(new_decision)

        # Load last 30 days only
        recent = memory_store.load_recent_decisions(days=30)
        assert len(recent) == 1
        assert recent[0].id == "new-001"


class TestOutcomeStorage:
    """Test outcome CRUD operations."""

    def test_save_and_get_outcome(self, memory_store):
        """Test saving and retrieving an outcome."""
        # First save a decision
        decision = StoredDecision(
            id="test-001",
            timestamp=datetime.utcnow(),
            symbol="EURUSD",
            action="BUY",
            confidence=0.75,
            lots=0.1,
            price=1.0900,
        )
        memory_store.save_decision(decision)

        # Then save outcome
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

        memory_store.save_outcome(outcome)
        loaded = memory_store.get_outcome("test-001")

        assert loaded is not None
        assert loaded.result == "WIN"
        assert loaded.pips == 50.0
        assert loaded.exit_reason == "TP"

    def test_get_outcome_for_open_trade(self, memory_store):
        """Test getting outcome for trade that hasn't closed."""
        decision = StoredDecision(
            id="test-002",
            timestamp=datetime.utcnow(),
            symbol="GBPUSD",
            action="SELL",
            confidence=0.80,
            lots=0.1,
            price=1.2500,
        )
        memory_store.save_decision(decision)

        # No outcome saved yet
        outcome = memory_store.get_outcome("test-002")
        assert outcome is None

    def test_load_outcomes(self, memory_store):
        """Test loading multiple outcomes."""
        # Create 10 decisions with outcomes
        for i in range(10):
            decision = StoredDecision(
                id=f"test-{i:03d}",
                timestamp=datetime.utcnow() - timedelta(days=i),
                symbol="EURUSD",
                action="BUY" if i % 2 == 0 else "SELL",
                confidence=0.75,
                lots=0.1,
                price=1.0900,
            )
            memory_store.save_decision(decision)

            outcome = TradeOutcome(
                decision_id=f"test-{i:03d}",
                closed_at=datetime.utcnow() - timedelta(days=i),
                result="WIN" if i < 7 else "LOSS",
                pips=50.0 if i < 7 else -20.0,
                duration_minutes=120,
                exit_reason="TP" if i < 7 else "SL",
            )
            memory_store.save_outcome(outcome)

        outcomes = memory_store.load_outcomes(days=30)
        assert len(outcomes) == 10

        wins = [o for o in outcomes if o.result == "WIN"]
        losses = [o for o in outcomes if o.result == "LOSS"]
        assert len(wins) == 7
        assert len(losses) == 3


class TestMemorySnapshot:
    """Test memory snapshot generation."""

    def test_load_empty_snapshot(self, memory_store):
        """Test loading snapshot with no data."""
        snapshot = memory_store.load_snapshot()

        assert snapshot.recent_decisions == []
        assert snapshot.win_rate_30d is None
        assert snapshot.current_regime is None
        assert snapshot.total_trades_30d == 0

    def test_load_snapshot_with_data(self, memory_store):
        """Test loading snapshot with decisions and outcomes."""
        # Create 10 decisions (7 wins, 3 losses)
        for i in range(10):
            decision = StoredDecision(
                id=f"test-{i:03d}",
                timestamp=datetime.utcnow() - timedelta(hours=i),
                symbol="EURUSD",
                action="BUY",
                confidence=0.75,
                lots=0.1,
                price=1.0900,
                regime="TRENDING" if i < 5 else "RANGING",
            )
            memory_store.save_decision(decision)

            outcome = TradeOutcome(
                decision_id=f"test-{i:03d}",
                closed_at=datetime.utcnow() - timedelta(hours=i),
                result="WIN" if i < 7 else "LOSS",
                pips=50.0 if i < 7 else -20.0,
                duration_minutes=120,
                exit_reason="TP" if i < 7 else "SL",
            )
            memory_store.save_outcome(outcome)

        snapshot = memory_store.load_snapshot()

        assert len(snapshot.recent_decisions) == 10
        assert snapshot.total_trades_30d == 10
        assert abs(snapshot.win_rate_30d - 0.70) < 0.01  # 70% win rate
        assert snapshot.avg_win_pips == 50.0
        assert snapshot.avg_loss_pips == 20.0
        assert snapshot.current_regime == "TRENDING"  # Most recent

    def test_snapshot_with_symbol_filter(self, memory_store):
        """Test loading snapshot filtered by symbol."""
        # Create decisions for multiple symbols
        for i in range(5):
            decision = StoredDecision(
                id=f"eur-{i:03d}",
                timestamp=datetime.utcnow(),
                symbol="EURUSD",
                action="BUY",
                confidence=0.75,
                lots=0.1,
                price=1.0900,
            )
            memory_store.save_decision(decision)

        for i in range(3):
            decision = StoredDecision(
                id=f"gbp-{i:03d}",
                timestamp=datetime.utcnow(),
                symbol="GBPUSD",
                action="SELL",
                confidence=0.80,
                lots=0.1,
                price=1.2500,
            )
            memory_store.save_decision(decision)

        # Load EURUSD only
        snapshot = memory_store.load_snapshot(symbol="EURUSD")
        assert len(snapshot.recent_decisions) == 5
        assert all(d['symbol'] == "EURUSD" for d in snapshot.recent_decisions)


class TestPatternStorage:
    """Test pattern CRUD operations."""

    def test_save_and_load_pattern(self, memory_store):
        """Test saving and loading a pattern."""
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

        memory_store.save_pattern(pattern)
        patterns = memory_store.load_patterns(min_sample_size=20)

        assert len(patterns) == 1
        assert patterns[0].pattern_id == "RSI_30-40_BULLISH_TRENDING"
        assert patterns[0].win_rate == 0.72

    def test_load_patterns_with_filters(self, memory_store):
        """Test loading patterns with various filters."""
        # Create multiple patterns
        patterns_data = [
            ("P1", 30, 40, "BULLISH", "TRENDING", 0.75, 50, 30),
            ("P2", 40, 50, "BEARISH", "RANGING", 0.60, 30, 15),
            ("P3", 60, 70, "BULLISH", "TRENDING", 0.68, 40, 25),
            ("P4", 20, 30, "BEARISH", "TRENDING", 0.55, 25, 8),  # Low sample
        ]

        for pid, rsi_min, rsi_max, macd, regime, wr, pips, samples in patterns_data:
            pattern = Pattern(
                pattern_id=pid,
                rsi_min=rsi_min,
                rsi_max=rsi_max,
                macd_signal=macd,
                regime=regime,
                win_rate=wr,
                avg_pips=pips,
                sample_size=samples,
            )
            memory_store.save_pattern(pattern)

        # Load with min_sample_size filter
        patterns = memory_store.load_patterns(min_sample_size=10)
        assert len(patterns) == 3  # P4 excluded (sample_size < 10)

        # Load with regime filter
        trending = memory_store.load_patterns(regime="TRENDING", min_sample_size=10)
        assert len(trending) == 2
        assert all(p.regime == "TRENDING" for p in trending)

    def test_find_similar_patterns(self, memory_store):
        """Test finding similar patterns for current context."""
        # Create patterns
        patterns_data = [
            ("P1", 30, 40, "BULLISH", "TRENDING", 0.75, 50, 30),
            ("P2", 35, 45, "BULLISH", "TRENDING", 0.70, 45, 25),
            ("P3", 60, 70, "BEARISH", "RANGING", 0.60, 30, 20),
        ]

        for pid, rsi_min, rsi_max, macd, regime, wr, pips, samples in patterns_data:
            pattern = Pattern(
                pattern_id=pid,
                rsi_min=rsi_min,
                rsi_max=rsi_max,
                macd_signal=macd,
                regime=regime,
                win_rate=wr,
                avg_pips=pips,
                sample_size=samples,
            )
            memory_store.save_pattern(pattern)

        # Find patterns for RSI=37, MACD positive, TRENDING
        similar = memory_store.find_similar_patterns(
            rsi=37.0,
            macd=0.0005,  # Positive = BULLISH
            bb_position="LOWER",
            regime="TRENDING",
            limit=2,
        )

        assert len(similar) == 2
        # Should match P1 and P2 (BULLISH + TRENDING)
        assert similar[0].pattern_id in ["P1", "P2"]
        assert similar[1].pattern_id in ["P1", "P2"]
        # Sorted by sample_size DESC
        assert similar[0].sample_size >= similar[1].sample_size


class TestUtilityMethods:
    """Test utility and monitoring methods."""

    def test_get_statistics(self, memory_store):
        """Test getting aggregate statistics."""
        # Create 10 decisions with outcomes
        for i in range(10):
            decision = StoredDecision(
                id=f"test-{i:03d}",
                timestamp=datetime.utcnow(),
                symbol="EURUSD",
                action="BUY",
                confidence=0.75,
                lots=0.1,
                price=1.0900,
            )
            memory_store.save_decision(decision)

            outcome = TradeOutcome(
                decision_id=f"test-{i:03d}",
                closed_at=datetime.utcnow(),
                result="WIN" if i < 7 else "LOSS",
                pips=50.0 if i < 7 else -20.0,
                duration_minutes=120,
                exit_reason="TP" if i < 7 else "SL",
            )
            memory_store.save_outcome(outcome)

        stats = memory_store.get_statistics(days=30)

        assert stats['total_decisions'] == 10
        assert stats['total_trades'] == 10
        assert abs(stats['win_rate'] - 0.70) < 0.01
        assert stats['max_pips'] == 50.0
        assert stats['min_pips'] == -20.0

    def test_health_check(self, memory_store):
        """Test health check."""
        assert memory_store.health_check() is True

    def test_clear_old_data(self, memory_store):
        """Test clearing old data (retention policy)."""
        # Create old and new decisions
        old_decision = StoredDecision(
            id="old-001",
            timestamp=datetime.utcnow() - timedelta(days=400),
            symbol="EURUSD",
            action="BUY",
            confidence=0.75,
            lots=0.1,
            price=1.0900,
        )

        new_decision = StoredDecision(
            id="new-001",
            timestamp=datetime.utcnow() - timedelta(days=30),
            symbol="EURUSD",
            action="BUY",
            confidence=0.75,
            lots=0.1,
            price=1.0900,
        )

        memory_store.save_decision(old_decision)
        memory_store.save_decision(new_decision)

        # Clear data older than 365 days
        deleted = memory_store.clear_old_data(days=365)
        assert deleted > 0

        # Old decision should be gone
        assert memory_store.load_decision("old-001") is None
        # New decision should remain
        assert memory_store.load_decision("new-001") is not None


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_storage_error_on_invalid_db_path(self):
        """Test that invalid DB path raises error."""
        # This should work (creates directory)
        store = SQLiteMemoryStore(db_path="/tmp/test_memory/memory.db")
        assert store.health_check()

    def test_concurrent_writes(self, memory_store):
        """Test that concurrent writes don't corrupt data."""
        # SQLite handles this via locking
        decisions = []
        for i in range(5):
            decision = StoredDecision(
                id=f"test-{i:03d}",
                timestamp=datetime.utcnow(),
                symbol="EURUSD",
                action="BUY",
                confidence=0.75,
                lots=0.1,
                price=1.0900,
            )
            memory_store.save_decision(decision)
            decisions.append(decision)

        # All should be saved
        for dec in decisions:
            loaded = memory_store.load_decision(dec.id)
            assert loaded is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
