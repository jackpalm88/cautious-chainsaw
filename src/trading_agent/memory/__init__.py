"""
Trading Agent - Memory Module

Three-layer memory architecture for persistent storage and learning:

1. MI Memory (Market Intelligence) - Recent context via MemorySnapshot
2. LLR Memory (Low-level Reflection) - Decision history via SQLite
3. HLR Memory (High-level Reflection) - Pattern learning via aggregation

Usage:
    from trading_agent.memory import SQLiteMemoryStore, MemorySnapshot
    
    memory_store = SQLiteMemoryStore(db_path="memory.db")
    snapshot = memory_store.load_snapshot(days=30)
"""

from .models import (
    StoredDecision,
    TradeOutcome,
    Pattern,
    MemorySnapshot
)

from .storage.base import MemoryStore, StorageError
from .storage.sqlite_store import SQLiteMemoryStore

__all__ = [
    # Models
    'StoredDecision',
    'TradeOutcome',
    'Pattern',
    'MemorySnapshot',
    
    # Storage
    'MemoryStore',
    'StorageError',
    'SQLiteMemoryStore',
]

__version__ = '1.5.0'
