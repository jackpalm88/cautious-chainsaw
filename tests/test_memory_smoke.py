"""Smoke tests for the Memory module."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from Memory import MemorySnapshot, SQLiteMemoryStore, StoredDecision, TradeOutcome


def test_memory_snapshot_smoke(tmp_path: Path) -> None:
    """End-to-end smoke test for persisting and reading memory snapshots."""
    db_path = tmp_path / "memory.db"
    store = SQLiteMemoryStore(db_path=str(db_path))

    decision_id = str(uuid4())
    now = datetime.utcnow()

    decision = StoredDecision(
        id=decision_id,
        timestamp=now,
        symbol="EURUSD",
        action="BUY",
        confidence=0.75,
        lots=1.0,
        stop_loss=1.05,
        take_profit=1.15,
        price=1.10,
        rsi=55.0,
        macd=0.1,
        bb_position="MIDDLE",
        regime="BULLISH",
        signal_agent_output={"score": 0.8},
        risk_agent_output={"risk": "medium"},
        context_agent_output={"news": "positive"},
        synthesis_agent_output={"summary": "enter long"},
    )
    store.save_decision(decision)

    outcome = TradeOutcome(
        decision_id=decision_id,
        closed_at=now + timedelta(hours=2),
        result="WIN",
        pips=25.0,
        duration_minutes=120,
        exit_reason="TP",
        fill_price=1.11,
        exit_price=1.135,
    )
    store.save_outcome(outcome)

    snapshot: MemorySnapshot = store.load_snapshot(days=30)

    assert snapshot.total_trades_30d is not None
    assert snapshot.total_trades_30d >= 1
    assert snapshot.recent_decisions
