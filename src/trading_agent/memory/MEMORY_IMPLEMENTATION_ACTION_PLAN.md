# 🧠 Memory Module - Implementation Action Plan

**Sprint:** v1.5 - Memory Persistence & Feedback Loop  
**Duration:** 8 weeks  
**Status:** 🚀 READY TO START

Based on: [MEMORY_INOT_DEEP_DIVE.md](computer:///mnt/user-data/outputs/MEMORY_INOT_DEEP_DIVE.md)

---

## 📋 EXECUTIVE SUMMARY

### Goal

Implement 3-layer Memory architecture:
1. **MI Memory** (Market Intelligence) - Recent context via MemorySnapshot
2. **LLR Memory** (Low-level Reflection) - Decision history via SQLite
3. **HLR Memory** (High-level Reflection) - Pattern learning via aggregation

### Success Criteria

- ✅ SQLite backend with 3 tables (decisions, outcomes, patterns)
- ✅ Feedback loop: Decision → Execute → Log Outcome
- ✅ MemorySnapshot loads from SQLite (backward compatible)
- ✅ 200+ trades collected for calibration data
- ✅ Confidence calibration deployed (Isotonic regression)
- ✅ Pattern recognition operational

### Timeline

```
Week 1-2:  SQLite Backend + Feedback Loop
Week 3-4:  Data Collection (operational phase)
Week 5:    Pattern Table + Query API
Week 6-8:  Confidence Calibration
```

---

## 🗓️ WEEK 1: SQLite Backend

### Day 1: Schema Design & Setup

**Files to Create:**
```
src/trading_agent/memory/
├── __init__.py
├── storage/
│   ├── __init__.py
│   ├── base.py          # MemoryStore protocol
│   └── sqlite_store.py  # SQLite implementation
└── models.py            # StoredDecision, TradeOutcome dataclasses
```

**Task 1.1: Base Protocol (1 hour)**
```python
# File: src/trading_agent/memory/storage/base.py

from typing import Protocol, List, Optional
from ..models import StoredDecision, TradeOutcome, MemorySnapshot

class MemoryStore(Protocol):
    """Abstract storage interface for memory persistence"""
    
    def save_decision(self, decision: StoredDecision) -> None:
        """Save a trading decision"""
        ...
    
    def save_outcome(self, outcome: TradeOutcome) -> None:
        """Save trade outcome when position closes"""
        ...
    
    def load_snapshot(self, days: int = 30) -> MemorySnapshot:
        """Load recent memory snapshot"""
        ...
    
    def load_outcomes(self, days: int = 30) -> List[TradeOutcome]:
        """Load historical outcomes for calibration"""
        ...
```

**Task 1.2: Data Models (2 hours)**
```python
# File: src/trading_agent/memory/models.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class StoredDecision:
    """Persistent decision record"""
    id: str
    timestamp: datetime
    symbol: str
    action: str  # BUY/SELL/HOLD
    confidence: float
    lots: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    
    # Market context snapshot
    price: float
    rsi: Optional[float]
    macd: Optional[float]
    bb_position: Optional[str]
    regime: Optional[str]
    
    # INoT agent outputs (JSON)
    signal_agent_output: Optional[Dict[str, Any]]
    risk_agent_output: Optional[Dict[str, Any]]
    context_agent_output: Optional[Dict[str, Any]]
    synthesis_agent_output: Optional[Dict[str, Any]]

@dataclass
class TradeOutcome:
    """Trade outcome record"""
    decision_id: str
    closed_at: datetime
    result: str  # WIN/LOSS/BREAKEVEN
    pips: float
    duration_minutes: int
    exit_reason: str  # SL/TP/MANUAL/TIMEOUT
    fill_price: Optional[float]
    exit_price: Optional[float]
```

**Task 1.3: SQLite Schema (2 hours)**
```python
# File: src/trading_agent/memory/storage/sqlite_store.py

import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional
import json
from ..models import StoredDecision, TradeOutcome, MemorySnapshot

class SQLiteMemoryStore:
    """SQLite-backed memory storage"""
    
    def __init__(self, db_path: str = "memory.db"):
        self.db_path = db_path
        self._init_schema()
    
    def _init_schema(self):
        """Create tables if not exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    timestamp DATETIME,
                    symbol TEXT,
                    action TEXT,
                    confidence REAL,
                    lots REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    
                    -- Context snapshot
                    price REAL,
                    rsi REAL,
                    macd REAL,
                    bb_position TEXT,
                    regime TEXT,
                    
                    -- Agent outputs (JSON)
                    signal_agent_output TEXT,
                    risk_agent_output TEXT,
                    context_agent_output TEXT,
                    synthesis_agent_output TEXT,
                    
                    -- Indexes
                    INDEX idx_timestamp ON decisions(timestamp),
                    INDEX idx_symbol ON decisions(symbol)
                );
                
                CREATE TABLE IF NOT EXISTS outcomes (
                    decision_id TEXT REFERENCES decisions(id),
                    closed_at DATETIME,
                    result TEXT,
                    pips REAL,
                    duration_minutes INTEGER,
                    exit_reason TEXT,
                    fill_price REAL,
                    exit_price REAL,
                    
                    PRIMARY KEY (decision_id),
                    INDEX idx_closed_at ON outcomes(closed_at),
                    INDEX idx_result ON outcomes(result)
                );
                
                CREATE TABLE IF NOT EXISTS patterns (
                    pattern_id TEXT PRIMARY KEY,
                    
                    -- Pattern definition
                    rsi_min REAL,
                    rsi_max REAL,
                    macd_signal TEXT,
                    bb_position TEXT,
                    regime TEXT,
                    
                    -- Performance metrics
                    win_rate REAL,
                    avg_pips REAL,
                    sample_size INTEGER,
                    last_updated DATETIME,
                    
                    INDEX idx_regime ON patterns(regime)
                );
            """)
    
    def save_decision(self, decision: StoredDecision) -> None:
        """Save decision to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO decisions VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                decision.id,
                decision.timestamp,
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
                json.dumps(decision.signal_agent_output),
                json.dumps(decision.risk_agent_output),
                json.dumps(decision.context_agent_output),
                json.dumps(decision.synthesis_agent_output),
            ))
    
    def save_outcome(self, outcome: TradeOutcome) -> None:
        """Save trade outcome"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO outcomes VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                outcome.decision_id,
                outcome.closed_at,
                outcome.result,
                outcome.pips,
                outcome.duration_minutes,
                outcome.exit_reason,
                outcome.fill_price,
                outcome.exit_price,
            ))
    
    def load_snapshot(self, days: int = 30) -> MemorySnapshot:
        """Load recent memory snapshot"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Recent decisions
            cursor = conn.execute("""
                SELECT * FROM decisions
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 10
            """, (cutoff,))
            recent_decisions = [dict(row) for row in cursor.fetchall()]
            
            # Aggregate metrics
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as win_rate,
                    AVG(CASE WHEN result = 'WIN' THEN pips ELSE 0 END) as avg_win_pips,
                    AVG(CASE WHEN result = 'LOSS' THEN ABS(pips) ELSE 0 END) as avg_loss_pips
                FROM outcomes
                WHERE closed_at > ?
            """, (cutoff,))
            metrics = cursor.fetchone()
            
            # Current regime (from most recent decision)
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
                win_rate_30d=metrics['win_rate'],
                avg_win_pips=metrics['avg_win_pips'],
                avg_loss_pips=metrics['avg_loss_pips'],
                total_trades_30d=metrics['total_trades']
            )
    
    def load_outcomes(self, days: int = 30) -> List[TradeOutcome]:
        """Load historical outcomes"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM outcomes
                WHERE closed_at > ?
                ORDER BY closed_at DESC
            """, (cutoff,))
            
            return [TradeOutcome(**dict(row)) for row in cursor.fetchall()]
```

**Deliverable Day 1:**
- ✅ SQLite schema created
- ✅ Base protocol defined
- ✅ Data models implemented
- ✅ Tests passing

---

### Day 2: Integration with Decision Engine

**Task 2.1: Modify TradingDecisionEngine (2 hours)**
```python
# Modify: src/trading_agent/decision/engine.py

from ..memory.storage.base import MemoryStore
from ..memory.storage.sqlite_store import SQLiteMemoryStore
from ..memory.models import StoredDecision

class TradingDecisionEngine:
    def __init__(
        self,
        config: Dict,
        memory_store: Optional[MemoryStore] = None
    ):
        # ... existing init ...
        
        # Memory store (default: SQLite)
        self.memory_store = memory_store or SQLiteMemoryStore()
    
    def decide(self, context: FusedContext) -> Decision:
        # Load memory snapshot from storage
        memory = self.memory_store.load_snapshot()
        
        # ... existing INoT reasoning ...
        
        decision = self.inot.reason(context, memory)
        
        # Save decision to storage
        stored_decision = StoredDecision(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            symbol=context.symbol,
            action=decision.action,
            confidence=decision.confidence,
            lots=decision.lots,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
            price=context.price,
            rsi=context.rsi,
            macd=context.macd,
            bb_position=context.bb_position,
            regime=memory.current_regime,
            signal_agent_output=decision.agent_outputs.get('Signal'),
            risk_agent_output=decision.agent_outputs.get('Risk'),
            context_agent_output=decision.agent_outputs.get('Context'),
            synthesis_agent_output=decision.agent_outputs.get('Synthesis'),
        )
        
        self.memory_store.save_decision(stored_decision)
        
        return decision
```

**Task 2.2: Unit Tests (2 hours)**
```python
# File: tests/test_memory_store.py

import pytest
from datetime import datetime
from trading_agent.memory.storage.sqlite_store import SQLiteMemoryStore
from trading_agent.memory.models import StoredDecision, TradeOutcome

@pytest.fixture
def memory_store():
    """In-memory SQLite for testing"""
    return SQLiteMemoryStore(db_path=":memory:")

def test_save_and_load_decision(memory_store):
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
        signal_agent_output={"reasoning": "RSI oversold"},
        risk_agent_output={"approved": True},
        context_agent_output={"regime": "TRENDING"},
        synthesis_agent_output={"final": "BUY"}
    )
    
    memory_store.save_decision(decision)
    snapshot = memory_store.load_snapshot()
    
    assert len(snapshot.recent_decisions) == 1
    assert snapshot.recent_decisions[0]['id'] == "test-001"

def test_save_outcome(memory_store):
    # First save a decision
    decision = StoredDecision(id="test-002", ...)
    memory_store.save_decision(decision)
    
    # Then save outcome
    outcome = TradeOutcome(
        decision_id="test-002",
        closed_at=datetime.utcnow(),
        result="WIN",
        pips=50.0,
        duration_minutes=120,
        exit_reason="TP",
        fill_price=1.0900,
        exit_price=1.0950
    )
    
    memory_store.save_outcome(outcome)
    outcomes = memory_store.load_outcomes()
    
    assert len(outcomes) == 1
    assert outcomes[0].result == "WIN"
    assert outcomes[0].pips == 50.0

def test_snapshot_metrics(memory_store):
    # Create 10 trades: 7 wins, 3 losses
    for i in range(10):
        decision = StoredDecision(id=f"test-{i:03d}", ...)
        memory_store.save_decision(decision)
        
        outcome = TradeOutcome(
            decision_id=f"test-{i:03d}",
            result="WIN" if i < 7 else "LOSS",
            pips=50.0 if i < 7 else -20.0,
            ...
        )
        memory_store.save_outcome(outcome)
    
    snapshot = memory_store.load_snapshot()
    
    assert snapshot.total_trades_30d == 10
    assert abs(snapshot.win_rate_30d - 0.70) < 0.01  # 70% win rate
    assert snapshot.avg_win_pips == 50.0
    assert snapshot.avg_loss_pips == 20.0
```

**Deliverable Day 2:**
- ✅ Decision engine integration
- ✅ Tests passing (unit + integration)
- ✅ Backward compatible (no breaking changes)

---

## 🗓️ WEEK 2: Feedback Loop

### Day 3: Outcome Monitor

**Task 3.1: Async Outcome Monitor (3 hours)**
```python
# File: src/trading_agent/memory/outcome_monitor.py

import asyncio
from datetime import datetime
from typing import Dict
from ..adapters.bridge import MT5ExecutionBridge
from ..memory.storage.base import MemoryStore
from ..memory.models import TradeOutcome

class OutcomeMonitor:
    """Monitors open trades and logs outcomes when closed"""
    
    def __init__(
        self,
        bridge: MT5ExecutionBridge,
        memory_store: MemoryStore,
        check_interval: int = 300  # 5 minutes
    ):
        self.bridge = bridge
        self.memory_store = memory_store
        self.check_interval = check_interval
        self.open_trades: Dict[str, Dict] = {}  # decision_id -> trade_info
    
    def register_trade(self, decision_id: str, order_id: int, entry_price: float):
        """Register a new open trade"""
        self.open_trades[decision_id] = {
            'order_id': order_id,
            'entry_price': entry_price,
            'opened_at': datetime.utcnow()
        }
    
    async def monitor_loop(self):
        """Async monitoring loop"""
        while True:
            await self._check_trades()
            await asyncio.sleep(self.check_interval)
    
    async def _check_trades(self):
        """Check all open trades for closure"""
        for decision_id, trade_info in list(self.open_trades.items()):
            order_id = trade_info['order_id']
            
            # Query broker for order status
            status = await self.bridge.get_order_status(order_id)
            
            if status['closed']:
                outcome = self._create_outcome(decision_id, trade_info, status)
                self.memory_store.save_outcome(outcome)
                del self.open_trades[decision_id]
    
    def _create_outcome(self, decision_id: str, trade_info: Dict, status: Dict) -> TradeOutcome:
        """Create outcome record"""
        entry_price = trade_info['entry_price']
        exit_price = status['exit_price']
        pips = abs(exit_price - entry_price) * 10000  # Assuming 4-digit broker
        
        duration = (datetime.utcnow() - trade_info['opened_at']).total_seconds() / 60
        
        # Determine result
        if exit_price > entry_price:
            result = "WIN" if status['action'] == "BUY" else "LOSS"
        elif exit_price < entry_price:
            result = "LOSS" if status['action'] == "BUY" else "WIN"
        else:
            result = "BREAKEVEN"
        
        return TradeOutcome(
            decision_id=decision_id,
            closed_at=datetime.utcnow(),
            result=result,
            pips=pips if result == "WIN" else -pips,
            duration_minutes=int(duration),
            exit_reason=status['exit_reason'],
            fill_price=entry_price,
            exit_price=exit_price
        )
```

**Task 3.2: Bridge Integration (2 hours)**
```python
# Modify: src/trading_agent/adapters/bridge.py

class MT5ExecutionBridge:
    def __init__(
        self,
        adapter: BaseExecutionAdapter,
        memory_store: Optional[MemoryStore] = None
    ):
        # ... existing init ...
        self.memory_store = memory_store
        self.outcome_monitor = OutcomeMonitor(self, memory_store) if memory_store else None
    
    async def execute_order(self, decision_id: str, signal: TradingSignal) -> ExecutionResult:
        # ... existing execution logic ...
        
        result = await self.adapter.place_order(...)
        
        if result.success and self.outcome_monitor:
            # Register trade for monitoring
            self.outcome_monitor.register_trade(
                decision_id=decision_id,
                order_id=result.order_id,
                entry_price=result.fill_price
            )
        
        return result
    
    async def get_order_status(self, order_id: int) -> Dict:
        """Query broker for order status"""
        return await self.adapter.get_order_info(order_id)
```

**Deliverable Day 3:**
- ✅ Outcome monitor implemented
- ✅ Bridge integration complete
- ✅ Async monitoring loop functional

---

### Day 4-5: End-to-End Testing

**Task 4.1: Integration Test (3 hours)**
```python
# File: tests/test_memory_integration.py

import pytest
import asyncio
from trading_agent.decision.engine import TradingDecisionEngine
from trading_agent.adapters.bridge import MT5ExecutionBridge
from trading_agent.adapters.adapter_mock import MockAdapter
from trading_agent.memory.storage.sqlite_store import SQLiteMemoryStore

@pytest.mark.asyncio
async def test_full_memory_flow():
    """Test complete flow: Decision → Execute → Outcome → Storage"""
    
    # Setup
    memory_store = SQLiteMemoryStore(db_path=":memory:")
    adapter = MockAdapter(success_rate=1.0)
    await adapter.connect()
    bridge = MT5ExecutionBridge(adapter, memory_store)
    engine = TradingDecisionEngine(config={}, memory_store=memory_store)
    
    # Create decision
    context = create_test_context()
    decision = engine.decide(context)
    
    # Execute
    result = await bridge.execute_order(decision.id, decision)
    assert result.success
    
    # Simulate trade closure (mock)
    await adapter.close_order(result.order_id, exit_price=1.0950)
    
    # Trigger outcome check
    await bridge.outcome_monitor._check_trades()
    
    # Verify outcome stored
    outcomes = memory_store.load_outcomes()
    assert len(outcomes) == 1
    assert outcomes[0].decision_id == decision.id
    assert outcomes[0].result == "WIN"
```

**Task 4.2: Documentation (2 hours)**
```markdown
# File: src/trading_agent/memory/README.md

# Memory Module

## Overview

Three-layer memory architecture for persistent storage and learning.

## Layers

1. **MI Memory** (Market Intelligence)
   - Recent market context
   - Loaded via `MemorySnapshot`

2. **LLR Memory** (Low-level Reflection)
   - Decision history
   - SQLite `decisions` table

3. **HLR Memory** (High-level Reflection)
   - Pattern learning
   - SQLite `patterns` table

## Usage

```python
from trading_agent.memory.storage.sqlite_store import SQLiteMemoryStore
from trading_agent.decision.engine import TradingDecisionEngine

memory_store = SQLiteMemoryStore(db_path="memory.db")
engine = TradingDecisionEngine(config, memory_store=memory_store)

# Memory is automatically saved/loaded
decision = engine.decide(context)
```

## Tables

### `decisions`
Stores every trading decision with full context.

### `outcomes`
Stores trade results (WIN/LOSS/BREAKEVEN) with pips and duration.

### `patterns`
Aggregated performance metrics per pattern.

## Querying

```python
# Load recent memory
snapshot = memory_store.load_snapshot(days=30)

# Load outcomes for calibration
outcomes = memory_store.load_outcomes(days=60)
```
```

**Deliverable Week 2:**
- ✅ Feedback loop operational
- ✅ Integration tests passing
- ✅ Documentation complete

---

## 🗓️ WEEK 3-4: Data Collection

**No new code - operational phase**

### Activities

1. **Deploy to Demo Account**
   - Configure MT5 demo account
   - Deploy trading agent
   - Start automated trading

2. **Monitor Data Quality**
   ```sql
   -- Daily health check
   SELECT 
       DATE(timestamp) as trade_date,
       COUNT(*) as decisions,
       (SELECT COUNT(*) FROM outcomes WHERE DATE(closed_at) = trade_date) as outcomes
   FROM decisions
   GROUP BY trade_date
   ORDER BY trade_date DESC
   LIMIT 7;
   ```

3. **Target Metrics**
   - **Goal:** 100 trades by Week 5 (minimum for calibration)
   - **Target:** 200 trades by Week 8 (robust calibration)
   - **Rate:** 5 trades/day average

### Weekly Checklist

- [ ] Monday: Review weekend data quality
- [ ] Wednesday: Check outcome logging (any gaps?)
- [ ] Friday: Export weekly stats

---

## 🗓️ WEEK 5: Pattern Table

### Task 5.1: Pattern Builder (3 hours)

```python
# File: src/trading_agent/memory/pattern_builder.py

from typing import List, Dict, Tuple
from collections import defaultdict
from ..models import StoredDecision, TradeOutcome

class PatternBuilder:
    """Extract patterns from historical decisions + outcomes"""
    
    def extract_patterns(self) -> List[Dict]:
        """Group decisions by pattern and calculate metrics"""
        
        # Query decisions with outcomes
        query = """
            SELECT 
                d.rsi, d.macd, d.bb_position, d.regime,
                o.result, o.pips
            FROM decisions d
            JOIN outcomes o ON d.id = o.decision_id
        """
        
        # Group by pattern
        patterns = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total_pips': 0})
        
        for row in self._query(query):
            pattern_key = self._create_pattern_key(row)
            patterns[pattern_key]['total'] += 1
            
            if row['result'] == 'WIN':
                patterns[pattern_key]['wins'] += 1
                patterns[pattern_key]['total_pips'] += row['pips']
            else:
                patterns[pattern_key]['losses'] += 1
                patterns[pattern_key]['total_pips'] -= row['pips']
        
        # Calculate metrics
        return [
            {
                'pattern_id': key,
                'rsi_min': key[0],
                'rsi_max': key[1],
                'macd_signal': key[2],
                'bb_position': key[3],
                'regime': key[4],
                'win_rate': stats['wins'] / (stats['wins'] + stats['losses']),
                'avg_pips': stats['total_pips'] / (stats['wins'] + stats['losses']),
                'sample_size': stats['wins'] + stats['losses']
            }
            for key, stats in patterns.items()
            if (stats['wins'] + stats['losses']) >= 10  # Minimum sample size
        ]
    
    def _create_pattern_key(self, row: Dict) -> Tuple:
        """Create pattern key from decision features"""
        # Bin RSI into ranges
        rsi_bin = int(row['rsi'] // 10) * 10  # 0-10, 10-20, etc.
        
        return (
            rsi_bin,
            rsi_bin + 10,
            'BULLISH' if row['macd'] > 0 else 'BEARISH',
            row['bb_position'],
            row['regime']
        )
    
    def save_patterns(self, patterns: List[Dict]):
        """Upsert patterns into database"""
        with sqlite3.connect(self.db_path) as conn:
            for pattern in patterns:
                conn.execute("""
                    INSERT OR REPLACE INTO patterns VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    pattern['pattern_id'],
                    pattern['rsi_min'],
                    pattern['rsi_max'],
                    pattern['macd_signal'],
                    pattern['bb_position'],
                    pattern['regime'],
                    pattern['win_rate'],
                    pattern['avg_pips'],
                    pattern['sample_size'],
                    datetime.utcnow()
                ))
```

### Task 5.2: Pattern Query API (2 hours)

```python
# File: src/trading_agent/memory/pattern_query.py

class PatternQuery:
    """Query similar patterns for current context"""
    
    def find_similar_patterns(
        self,
        rsi: float,
        macd: float,
        bb_position: str,
        regime: str,
        limit: int = 3
    ) -> List[Dict]:
        """Find top N most similar patterns"""
        
        rsi_bin = int(rsi // 10) * 10
        macd_signal = 'BULLISH' if macd > 0 else 'BEARISH'
        
        query = """
            SELECT * FROM patterns
            WHERE rsi_min <= ? AND rsi_max >= ?
              AND macd_signal = ?
              AND bb_position = ?
              AND regime = ?
            ORDER BY sample_size DESC
            LIMIT ?
        """
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, (
                rsi, rsi, macd_signal, bb_position, regime, limit
            ))
            
            return [dict(row) for row in cursor.fetchall()]
```

### Task 5.3: Integration (2 hours)

```python
# Modify: src/trading_agent/decision/engine.py

class TradingDecisionEngine:
    def __init__(self, ..., pattern_query: Optional[PatternQuery] = None):
        self.pattern_query = pattern_query or PatternQuery(memory_store.db_path)
    
    def decide(self, context: FusedContext) -> Decision:
        # Load memory
        memory = self.memory_store.load_snapshot()
        
        # Query similar patterns
        similar_patterns = self.pattern_query.find_similar_patterns(
            rsi=context.rsi,
            macd=context.macd,
            bb_position=context.bb_position,
            regime=memory.current_regime
        )
        
        # Add to memory snapshot
        memory.similar_patterns = similar_patterns
        
        # INoT reasoning with enriched memory
        decision = self.inot.reason(context, memory)
        
        return decision
```

**Deliverable Week 5:**
- ✅ Pattern table populated
- ✅ Pattern query API operational
- ✅ Similar patterns shown to INoT agents

---

## 🗓️ WEEK 6-8: Confidence Calibration

### Week 6: Data Preparation

```python
# File: src/trading_agent/memory/calibration_data.py

import pandas as pd
from ..storage.base import MemoryStore

def prepare_calibration_dataset(
    memory_store: MemoryStore,
    days: int = 60
) -> pd.DataFrame:
    """Prepare dataset for confidence calibration"""
    
    outcomes = memory_store.load_outcomes(days=days)
    
    data = {
        'predicted_confidence': [],
        'actual_outcome': []
    }
    
    for outcome in outcomes:
        # Load corresponding decision
        decision = memory_store.load_decision(outcome.decision_id)
        
        data['predicted_confidence'].append(decision.confidence)
        data['actual_outcome'].append(1 if outcome.result == 'WIN' else 0)
    
    df = pd.DataFrame(data)
    
    # Filter out low-sample bins
    return df[df.groupby(pd.cut(df['predicted_confidence'], bins=10))['predicted_confidence'].transform('size') >= 10]
```

### Week 7: Model Training

```python
# File: src/trading_agent/memory/calibrator.py

import pickle
from sklearn.isotonic import IsotonicRegression
import numpy as np

class ConfidenceCalibrator:
    """Confidence calibration using Isotonic Regression"""
    
    def __init__(self, model_path: str = "calibrator.pkl"):
        self.model_path = model_path
        self.model = None
        self.is_trained = False
    
    def fit(self, predicted: np.ndarray, actual: np.ndarray):
        """Train calibration model"""
        self.model = IsotonicRegression(out_of_bounds='clip')
        self.model.fit(predicted, actual)
        self.is_trained = True
        self._save_model()
    
    def calibrate(self, raw_confidence: float) -> float:
        """Calibrate a single confidence score"""
        if not self.is_trained:
            return raw_confidence  # Fallback to raw
        
        return float(self.model.predict([raw_confidence])[0])
    
    def _save_model(self):
        """Persist model to disk"""
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)
    
    def load_model(self):
        """Load model from disk"""
        try:
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            self.is_trained = True
        except FileNotFoundError:
            pass
```

### Week 8: Deployment

```python
# Modify: src/trading_agent/decision/engine.py

class TradingDecisionEngine:
    def __init__(self, ..., calibrator: Optional[ConfidenceCalibrator] = None):
        self.calibrator = calibrator or ConfidenceCalibrator()
        self.calibrator.load_model()  # Load if exists
    
    def decide(self, context: FusedContext) -> Decision:
        # ... INoT reasoning ...
        
        decision = self.inot.reason(context, memory)
        
        # Apply calibration
        if self.calibrator.is_trained:
            decision.confidence = self.calibrator.calibrate(decision.confidence)
            decision.calibrated = True
        
        return decision
```

**Deliverable Week 6-8:**
- ✅ 200+ trades collected
- ✅ Calibration model trained
- ✅ Confidence calibration deployed

---

## 📊 TESTING STRATEGY

### Unit Tests

```bash
pytest tests/test_memory_store.py -v
pytest tests/test_pattern_builder.py -v
pytest tests/test_calibrator.py -v
```

### Integration Tests

```bash
pytest tests/test_memory_integration.py -v
```

### Performance Tests

```python
# File: tests/test_memory_performance.py

def test_snapshot_load_performance():
    """Ensure snapshot loads in <50ms"""
    store = SQLiteMemoryStore()
    
    start = time.perf_counter()
    snapshot = store.load_snapshot()
    duration = (time.perf_counter() - start) * 1000
    
    assert duration < 50  # <50ms
```

---

## 🚀 DEPLOYMENT CHECKLIST

### Pre-Deployment

- [ ] All tests passing (unit + integration)
- [ ] SQLite schema validated
- [ ] Backup strategy defined
- [ ] Monitoring alerts configured

### Deployment

- [ ] Deploy to demo account first
- [ ] Monitor for 1 week
- [ ] Verify data quality
- [ ] Deploy to production

### Post-Deployment

- [ ] Daily health checks
- [ ] Weekly pattern analysis
- [ ] Monthly calibration updates

---

## 📚 SUCCESS METRICS

### Week 1-2

- ✅ SQLite backend operational
- ✅ Decision/outcome logging working
- ✅ 100% test coverage (unit tests)

### Week 3-4

- ✅ 100+ trades collected
- ✅ Zero data quality issues
- ✅ Outcome logging 100% accurate

### Week 5

- ✅ Pattern table populated
- ✅ Similar pattern queries working
- ✅ Patterns influence decisions

### Week 6-8

- ✅ 200+ trades for calibration
- ✅ Calibration model trained
- ✅ Confidence scores calibrated
- ✅ Win rate prediction improved

---

## 🎯 FINAL DELIVERABLES

1. **SQLite Backend** - Production-ready memory storage
2. **Feedback Loop** - Automated outcome logging
3. **Pattern Recognition** - SQL-based pattern matching
4. **Confidence Calibration** - Isotonic regression model
5. **Documentation** - Complete usage guide
6. **Tests** - 90%+ coverage

---

## 📞 SUPPORT

**Questions?** Open GitHub issue: `Memory Module Implementation (v1.5)`  
**Branch:** `feature/memory-persistence`  
**Docs:** [MEMORY_INOT_DEEP_DIVE.md](computer:///mnt/user-data/outputs/MEMORY_INOT_DEEP_DIVE.md)

---

**Status:** 🚀 Ready to Start Week 1  
**Next Action:** Create SQLite backend (Day 1)

---

*Based on INoT Deep Dive strategic analysis*  
*Timeline: 8 weeks to production-ready memory system*
