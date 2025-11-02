"""
SQLite Memory Store Implementation

Production-ready SQLite backend for memory persistence.
Implements MemoryStore protocol with full CRUD operations.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from ..models import StoredDecision, TradeOutcome, MemorySnapshot, Pattern
from .base import MemoryStore, StorageError


class SQLiteMemoryStore:
    """
    SQLite-backed memory storage with three tables:
    
    - decisions: Full decision history (LLR Memory)
    - outcomes: Trade results (Feedback Loop)
    - patterns: Aggregated performance (HLR Memory)
    """
    
    def __init__(self, db_path: str = "memory.db"):
        """
        Initialize SQLite memory store.
        
        Args:
            db_path: Path to SQLite database file (default: "memory.db")
        """
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_schema()
    
    def _ensure_db_directory(self):
        """Create directory for database if it doesn't exist."""
        db_dir = Path(self.db_path).parent
        if db_dir and not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
    
    def _init_schema(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Table 1: Decision History (LLR Memory)
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    timestamp DATETIME NOT NULL,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    lots REAL NOT NULL,
                    stop_loss REAL,
                    take_profit REAL,
                    
                    -- Market context snapshot
                    price REAL NOT NULL DEFAULT 0.0,
                    rsi REAL,
                    macd REAL,
                    bb_position TEXT,
                    regime TEXT,
                    
                    -- INoT agent outputs (JSON serialized)
                    signal_agent_output TEXT,
                    risk_agent_output TEXT,
                    context_agent_output TEXT,
                    synthesis_agent_output TEXT,
                    
                    -- Indexes for fast queries
                    CHECK (action IN ('BUY', 'SELL', 'HOLD')),
                    CHECK (confidence BETWEEN 0 AND 1),
                    CHECK (lots > 0)
                );
                
                CREATE INDEX IF NOT EXISTS idx_decisions_timestamp 
                ON decisions(timestamp DESC);
                
                CREATE INDEX IF NOT EXISTS idx_decisions_symbol 
                ON decisions(symbol, timestamp DESC);
                
                CREATE INDEX IF NOT EXISTS idx_decisions_action 
                ON decisions(action, timestamp DESC);
                
                -- Table 2: Trade Outcomes (Feedback Loop)
                CREATE TABLE IF NOT EXISTS outcomes (
                    decision_id TEXT PRIMARY KEY REFERENCES decisions(id),
                    closed_at DATETIME NOT NULL,
                    result TEXT NOT NULL,
                    pips REAL NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    exit_reason TEXT NOT NULL,
                    fill_price REAL,
                    exit_price REAL,
                    
                    CHECK (result IN ('WIN', 'LOSS', 'BREAKEVEN')),
                    CHECK (exit_reason IN ('SL', 'TP', 'MANUAL', 'TIMEOUT'))
                );
                
                CREATE INDEX IF NOT EXISTS idx_outcomes_closed_at 
                ON outcomes(closed_at DESC);
                
                CREATE INDEX IF NOT EXISTS idx_outcomes_result 
                ON outcomes(result);
                
                -- Table 3: Pattern Performance (HLR Memory)
                CREATE TABLE IF NOT EXISTS patterns (
                    pattern_id TEXT PRIMARY KEY,
                    
                    -- Pattern definition
                    rsi_min REAL NOT NULL,
                    rsi_max REAL NOT NULL,
                    macd_signal TEXT NOT NULL,
                    bb_position TEXT,
                    regime TEXT,
                    
                    -- Performance metrics
                    win_rate REAL NOT NULL DEFAULT 0.0,
                    avg_pips REAL NOT NULL DEFAULT 0.0,
                    sample_size INTEGER NOT NULL DEFAULT 0,
                    last_updated DATETIME,
                    
                    CHECK (rsi_min >= 0 AND rsi_max <= 100),
                    CHECK (rsi_min < rsi_max),
                    CHECK (macd_signal IN ('BULLISH', 'BEARISH', 'NEUTRAL')),
                    CHECK (win_rate BETWEEN 0 AND 1),
                    CHECK (sample_size >= 0)
                );
                
                CREATE INDEX IF NOT EXISTS idx_patterns_regime 
                ON patterns(regime);
                
                CREATE INDEX IF NOT EXISTS idx_patterns_sample_size 
                ON patterns(sample_size DESC);
            """)
    
    # ========== DECISION STORAGE ==========
    
    def save_decision(self, decision: StoredDecision) -> None:
        """Save a trading decision to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO decisions VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    decision.id,
                    decision.timestamp.isoformat(),
                    decision.symbol,
                    decision.action,
                    decision.confidence,
                    decision.lots,
                    decision.stop_loss,
                    decision.take_profit,
                    decision.price,
                    decision.rsi,
                    decision.macd,
                    decision.bb_position,
                    decision.regime,
                    json.dumps(decision.signal_agent_output) if decision.signal_agent_output else None,
                    json.dumps(decision.risk_agent_output) if decision.risk_agent_output else None,
                    json.dumps(decision.context_agent_output) if decision.context_agent_output else None,
                    json.dumps(decision.synthesis_agent_output) if decision.synthesis_agent_output else None,
                ))
        except sqlite3.Error as e:
            raise StorageError(f"Failed to save decision: {e}")
    
    def load_decision(self, decision_id: str) -> Optional[StoredDecision]:
        """Load a specific decision by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM decisions WHERE id = ?",
                (decision_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_decision(row)
    
    def load_recent_decisions(
        self,
        limit: int = 10,
        symbol: Optional[str] = None,
        days: int = 30
    ) -> List[StoredDecision]:
        """Load recent decisions, optionally filtered by symbol."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if symbol:
                cursor = conn.execute("""
                    SELECT * FROM decisions
                    WHERE symbol = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (symbol, cutoff.isoformat(), limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM decisions
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (cutoff.isoformat(), limit))
            
            return [self._row_to_decision(row) for row in cursor.fetchall()]
    
    def _row_to_decision(self, row: sqlite3.Row) -> StoredDecision:
        """Convert database row to StoredDecision object."""
        return StoredDecision(
            id=row['id'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            symbol=row['symbol'],
            action=row['action'],
            confidence=row['confidence'],
            lots=row['lots'],
            stop_loss=row['stop_loss'],
            take_profit=row['take_profit'],
            price=row['price'],
            rsi=row['rsi'],
            macd=row['macd'],
            bb_position=row['bb_position'],
            regime=row['regime'],
            signal_agent_output=json.loads(row['signal_agent_output']) if row['signal_agent_output'] else None,
            risk_agent_output=json.loads(row['risk_agent_output']) if row['risk_agent_output'] else None,
            context_agent_output=json.loads(row['context_agent_output']) if row['context_agent_output'] else None,
            synthesis_agent_output=json.loads(row['synthesis_agent_output']) if row['synthesis_agent_output'] else None,
        )
    
    # ========== OUTCOME STORAGE (FEEDBACK LOOP) ==========
    
    def save_outcome(self, outcome: TradeOutcome) -> None:
        """Save trade outcome when position closes."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO outcomes VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    outcome.decision_id,
                    outcome.closed_at.isoformat(),
                    outcome.result,
                    outcome.pips,
                    outcome.duration_minutes,
                    outcome.exit_reason,
                    outcome.fill_price,
                    outcome.exit_price,
                ))
        except sqlite3.Error as e:
            raise StorageError(f"Failed to save outcome: {e}")
    
    def load_outcomes(
        self,
        days: int = 30,
        symbol: Optional[str] = None
    ) -> List[TradeOutcome]:
        """Load historical outcomes for calibration."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if symbol:
                cursor = conn.execute("""
                    SELECT o.* FROM outcomes o
                    JOIN decisions d ON o.decision_id = d.id
                    WHERE d.symbol = ? AND o.closed_at > ?
                    ORDER BY o.closed_at DESC
                """, (symbol, cutoff.isoformat()))
            else:
                cursor = conn.execute("""
                    SELECT * FROM outcomes
                    WHERE closed_at > ?
                    ORDER BY closed_at DESC
                """, (cutoff.isoformat(),))
            
            return [self._row_to_outcome(row) for row in cursor.fetchall()]
    
    def get_outcome(self, decision_id: str) -> Optional[TradeOutcome]:
        """Get outcome for a specific decision."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM outcomes WHERE decision_id = ?",
                (decision_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_outcome(row)
    
    def _row_to_outcome(self, row: sqlite3.Row) -> TradeOutcome:
        """Convert database row to TradeOutcome object."""
        return TradeOutcome(
            decision_id=row['decision_id'],
            closed_at=datetime.fromisoformat(row['closed_at']),
            result=row['result'],
            pips=row['pips'],
            duration_minutes=row['duration_minutes'],
            exit_reason=row['exit_reason'],
            fill_price=row['fill_price'],
            exit_price=row['exit_price'],
        )
    
    # ========== MEMORY SNAPSHOT (MI MEMORY) ==========
    
    def load_snapshot(
        self,
        days: int = 30,
        symbol: Optional[str] = None
    ) -> MemorySnapshot:
        """
        Load recent memory snapshot for INoT agents.
        
        Aggregates:
        - Last 10 decisions
        - 30-day performance metrics
        - Current regime
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Recent decisions (as dicts for JSON serialization)
            if symbol:
                cursor = conn.execute("""
                    SELECT * FROM decisions
                    WHERE symbol = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT 10
                """, (symbol, cutoff.isoformat()))
            else:
                cursor = conn.execute("""
                    SELECT * FROM decisions
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT 10
                """, (cutoff.isoformat(),))
            
            recent_decisions = [dict(row) for row in cursor.fetchall()]
            
            # Aggregate metrics (join decisions + outcomes)
            if symbol:
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        CAST(SUM(CASE WHEN o.result = 'WIN' THEN 1 ELSE 0 END) AS REAL) / COUNT(*) as win_rate,
                        AVG(CASE WHEN o.result = 'WIN' THEN o.pips ELSE NULL END) as avg_win_pips,
                        AVG(CASE WHEN o.result = 'LOSS' THEN ABS(o.pips) ELSE NULL END) as avg_loss_pips
                    FROM outcomes o
                    JOIN decisions d ON o.decision_id = d.id
                    WHERE d.symbol = ? AND o.closed_at > ?
                """, (symbol, cutoff.isoformat()))
            else:
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        CAST(SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) AS REAL) / COUNT(*) as win_rate,
                        AVG(CASE WHEN result = 'WIN' THEN pips ELSE NULL END) as avg_win_pips,
                        AVG(CASE WHEN result = 'LOSS' THEN ABS(pips) ELSE NULL END) as avg_loss_pips
                    FROM outcomes
                    WHERE closed_at > ?
                """, (cutoff.isoformat(),))
            
            metrics = cursor.fetchone()
            
            # Current regime (from most recent decision)
            if symbol:
                cursor = conn.execute("""
                    SELECT regime FROM decisions
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (symbol,))
            else:
                cursor = conn.execute("""
                    SELECT regime FROM decisions
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)
            
            regime_row = cursor.fetchone()
            current_regime = regime_row['regime'] if regime_row else None
            
            return MemorySnapshot(
                recent_decisions=recent_decisions,
                current_regime=current_regime,
                win_rate_30d=metrics['win_rate'] if metrics['total_trades'] > 0 else None,
                avg_win_pips=metrics['avg_win_pips'],
                avg_loss_pips=metrics['avg_loss_pips'],
                total_trades_30d=metrics['total_trades'],
                similar_patterns=[]  # Populated by find_similar_patterns if needed
            )
    
    # ========== PATTERN STORAGE (HLR MEMORY) ==========
    
    def save_pattern(self, pattern: Pattern) -> None:
        """Save or update a pattern's performance metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO patterns VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    pattern.pattern_id,
                    pattern.rsi_min,
                    pattern.rsi_max,
                    pattern.macd_signal,
                    pattern.bb_position,
                    pattern.regime,
                    pattern.win_rate,
                    pattern.avg_pips,
                    pattern.sample_size,
                    pattern.last_updated.isoformat() if pattern.last_updated else datetime.utcnow().isoformat(),
                ))
        except sqlite3.Error as e:
            raise StorageError(f"Failed to save pattern: {e}")
    
    def load_patterns(
        self,
        rsi_range: Optional[tuple[float, float]] = None,
        regime: Optional[str] = None,
        min_sample_size: int = 10
    ) -> List[Pattern]:
        """Load patterns matching criteria."""
        query = "SELECT * FROM patterns WHERE sample_size >= ?"
        params = [min_sample_size]
        
        if rsi_range:
            query += " AND rsi_min >= ? AND rsi_max <= ?"
            params.extend([rsi_range[0], rsi_range[1]])
        
        if regime:
            query += " AND regime = ?"
            params.append(regime)
        
        query += " ORDER BY sample_size DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [self._row_to_pattern(row) for row in cursor.fetchall()]
    
    def find_similar_patterns(
        self,
        rsi: float,
        macd: float,
        bb_position: Optional[str],
        regime: Optional[str],
        limit: int = 3
    ) -> List[Pattern]:
        """Find patterns similar to current market context."""
        macd_signal = 'BULLISH' if macd > 0 else 'BEARISH' if macd < 0 else 'NEUTRAL'
        
        query = """
            SELECT * FROM patterns
            WHERE rsi_min <= ? AND rsi_max >= ?
              AND macd_signal = ?
        """
        params = [rsi, rsi, macd_signal]
        
        if bb_position:
            query += " AND (bb_position = ? OR bb_position IS NULL)"
            params.append(bb_position)
        
        if regime:
            query += " AND (regime = ? OR regime IS NULL)"
            params.append(regime)
        
        query += " ORDER BY sample_size DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [self._row_to_pattern(row) for row in cursor.fetchall()]
    
    def _row_to_pattern(self, row: sqlite3.Row) -> Pattern:
        """Convert database row to Pattern object."""
        return Pattern(
            pattern_id=row['pattern_id'],
            rsi_min=row['rsi_min'],
            rsi_max=row['rsi_max'],
            macd_signal=row['macd_signal'],
            bb_position=row['bb_position'],
            regime=row['regime'],
            win_rate=row['win_rate'],
            avg_pips=row['avg_pips'],
            sample_size=row['sample_size'],
            last_updated=datetime.fromisoformat(row['last_updated']) if row['last_updated'] else None,
        )
    
    # ========== UTILITY METHODS ==========
    
    def get_statistics(self, days: int = 30) -> dict:
        """Get aggregate statistics for monitoring."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Overall stats
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    CAST(SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) AS REAL) / COUNT(*) as win_rate,
                    AVG(pips) as avg_pips,
                    MIN(pips) as min_pips,
                    MAX(pips) as max_pips,
                    AVG(duration_minutes) as avg_duration_minutes
                FROM outcomes
                WHERE closed_at > ?
            """, (cutoff.isoformat(),))
            
            stats = dict(cursor.fetchone())
            
            # Decisions count
            cursor = conn.execute("""
                SELECT COUNT(*) as total_decisions
                FROM decisions
                WHERE timestamp > ?
            """, (cutoff.isoformat(),))
            
            stats['total_decisions'] = cursor.fetchone()['total_decisions']
            
            # Pattern count
            cursor = conn.execute("SELECT COUNT(*) as total_patterns FROM patterns")
            stats['total_patterns'] = cursor.fetchone()['total_patterns']
            
            return stats
    
    def health_check(self) -> bool:
        """Check if storage backend is healthy."""
        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                conn.execute("SELECT 1")
            return True
        except sqlite3.Error:
            return False
    
    def clear_old_data(self, days: int = 365) -> int:
        """Delete data older than N days (retention policy)."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        deleted = 0
        
        with sqlite3.connect(self.db_path) as conn:
            # Delete old outcomes
            cursor = conn.execute("""
                DELETE FROM outcomes
                WHERE closed_at < ?
            """, (cutoff.isoformat(),))
            deleted += cursor.rowcount
            
            # Delete old decisions (that don't have outcomes)
            cursor = conn.execute("""
                DELETE FROM decisions
                WHERE timestamp < ?
                  AND id NOT IN (SELECT decision_id FROM outcomes)
            """, (cutoff.isoformat(),))
            deleted += cursor.rowcount
            
            # Update pattern last_updated (don't delete patterns)
            conn.execute("""
                UPDATE patterns
                SET last_updated = ?
                WHERE last_updated < ?
            """, (datetime.utcnow().isoformat(), cutoff.isoformat()))
        
        return deleted
