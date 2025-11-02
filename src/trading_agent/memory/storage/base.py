"""
Memory Storage - Base Protocol

Defines abstract interface for memory persistence backends.
Allows swapping storage implementations (SQLite, Redis, PostgreSQL, etc.)
"""

from typing import Protocol, List, Optional
from datetime import datetime, timedelta

from ..models import StoredDecision, TradeOutcome, MemorySnapshot, Pattern


class MemoryStore(Protocol):
    """
    Abstract storage interface for memory persistence.
    
    This protocol defines the contract that all storage backends must implement.
    Current implementation: SQLiteMemoryStore
    Future implementations: RedisMemoryStore, PostgreSQLMemoryStore
    """
    
    # ========== DECISION STORAGE ==========
    
    def save_decision(self, decision: StoredDecision) -> None:
        """
        Save a trading decision to persistent storage.
        
        Args:
            decision: StoredDecision with full context snapshot
            
        Raises:
            StorageError: If save operation fails
        """
        ...
    
    def load_decision(self, decision_id: str) -> Optional[StoredDecision]:
        """
        Load a specific decision by ID.
        
        Args:
            decision_id: Unique decision identifier
            
        Returns:
            StoredDecision if found, None otherwise
        """
        ...
    
    def load_recent_decisions(
        self,
        limit: int = 10,
        symbol: Optional[str] = None,
        days: int = 30
    ) -> List[StoredDecision]:
        """
        Load recent decisions, optionally filtered by symbol.
        
        Args:
            limit: Maximum number of decisions to return
            symbol: Optional symbol filter (e.g., "EURUSD")
            days: Only return decisions from last N days
            
        Returns:
            List of StoredDecision objects, newest first
        """
        ...
    
    # ========== OUTCOME STORAGE (FEEDBACK LOOP) ==========
    
    def save_outcome(self, outcome: TradeOutcome) -> None:
        """
        Save trade outcome when position closes.
        
        Args:
            outcome: TradeOutcome with result, pips, duration
            
        Raises:
            StorageError: If save operation fails
        """
        ...
    
    def load_outcomes(
        self,
        days: int = 30,
        symbol: Optional[str] = None
    ) -> List[TradeOutcome]:
        """
        Load historical outcomes for calibration or analysis.
        
        Args:
            days: Load outcomes from last N days
            symbol: Optional symbol filter
            
        Returns:
            List of TradeOutcome objects
        """
        ...
    
    def get_outcome(self, decision_id: str) -> Optional[TradeOutcome]:
        """
        Get outcome for a specific decision.
        
        Args:
            decision_id: Decision ID to lookup
            
        Returns:
            TradeOutcome if found, None if trade still open
        """
        ...
    
    # ========== MEMORY SNAPSHOT (MI MEMORY) ==========
    
    def load_snapshot(
        self,
        days: int = 30,
        symbol: Optional[str] = None
    ) -> MemorySnapshot:
        """
        Load recent memory snapshot for INoT agents.
        
        This aggregates:
        - Last N decisions
        - 30-day performance metrics (win rate, avg pips)
        - Current market regime
        - Similar patterns (if pattern recognition enabled)
        
        Args:
            days: Lookback window for aggregation
            symbol: Optional symbol filter
            
        Returns:
            MemorySnapshot ready for INoT reasoning
        """
        ...
    
    # ========== PATTERN STORAGE (HLR MEMORY) ==========
    
    def save_pattern(self, pattern: Pattern) -> None:
        """
        Save or update a pattern's performance metrics.
        
        Args:
            pattern: Pattern with win rate, avg pips, sample size
        """
        ...
    
    def load_patterns(
        self,
        rsi_range: Optional[tuple[float, float]] = None,
        regime: Optional[str] = None,
        min_sample_size: int = 10
    ) -> List[Pattern]:
        """
        Load patterns matching criteria.
        
        Args:
            rsi_range: Optional (min, max) RSI filter
            regime: Optional regime filter
            min_sample_size: Minimum trades for statistical significance
            
        Returns:
            List of Pattern objects
        """
        ...
    
    def find_similar_patterns(
        self,
        rsi: float,
        macd: float,
        bb_position: Optional[str],
        regime: Optional[str],
        limit: int = 3
    ) -> List[Pattern]:
        """
        Find patterns similar to current market context.
        
        Args:
            rsi: Current RSI value
            macd: Current MACD value
            bb_position: Current BB position
            regime: Current market regime
            limit: Max patterns to return
            
        Returns:
            List of most similar patterns, sorted by sample size
        """
        ...
    
    # ========== UTILITY METHODS ==========
    
    def get_statistics(self, days: int = 30) -> dict:
        """
        Get aggregate statistics for monitoring.
        
        Args:
            days: Lookback window
            
        Returns:
            Dict with keys: total_trades, win_rate, avg_pips, etc.
        """
        ...
    
    def health_check(self) -> bool:
        """
        Check if storage backend is healthy.
        
        Returns:
            True if storage is accessible, False otherwise
        """
        ...
    
    def clear_old_data(self, days: int = 365) -> int:
        """
        Delete data older than N days (retention policy).
        
        Args:
            days: Keep last N days of data
            
        Returns:
            Number of records deleted
        """
        ...


class StorageError(Exception):
    """Raised when storage operation fails."""
    pass
