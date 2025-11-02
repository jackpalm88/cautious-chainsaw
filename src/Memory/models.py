"""
Memory Module - Data Models

Defines persistent data structures for memory storage.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class StoredDecision:
    """
    Persistent decision record with full context snapshot.

    Stored in SQLite `decisions` table for LLR (Low-level Reflection) memory.
    """

    # Primary identification
    id: str
    timestamp: datetime
    symbol: str

    # Decision output
    action: str  # BUY/SELL/HOLD
    confidence: float
    lots: float
    stop_loss: float | None = None
    take_profit: float | None = None

    # Market context snapshot (at decision time)
    price: float = 0.0
    rsi: float | None = None
    macd: float | None = None
    bb_position: str | None = None
    regime: str | None = None

    # INoT agent outputs (JSON serialized)
    signal_agent_output: dict[str, Any] | None = None
    risk_agent_output: dict[str, Any] | None = None
    context_agent_output: dict[str, Any] | None = None
    synthesis_agent_output: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'action': self.action,
            'confidence': self.confidence,
            'lots': self.lots,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'price': self.price,
            'rsi': self.rsi,
            'macd': self.macd,
            'bb_position': self.bb_position,
            'regime': self.regime,
            'signal_agent_output': self.signal_agent_output,
            'risk_agent_output': self.risk_agent_output,
            'context_agent_output': self.context_agent_output,
            'synthesis_agent_output': self.synthesis_agent_output,
        }


@dataclass
class TradeOutcome:
    """
    Trade outcome record for feedback loop.

    Stored in SQLite `outcomes` table, linked to StoredDecision via decision_id.
    """

    decision_id: str
    closed_at: datetime
    result: str  # WIN/LOSS/BREAKEVEN
    pips: float
    duration_minutes: int
    exit_reason: str  # SL/TP/MANUAL/TIMEOUT
    fill_price: float | None = None
    exit_price: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'decision_id': self.decision_id,
            'closed_at': self.closed_at.isoformat(),
            'result': self.result,
            'pips': self.pips,
            'duration_minutes': self.duration_minutes,
            'exit_reason': self.exit_reason,
            'fill_price': self.fill_price,
            'exit_price': self.exit_price,
        }


@dataclass
class Pattern:
    """
    Aggregated pattern performance metrics for HLR (High-level Reflection) memory.

    Stored in SQLite `patterns` table.
    """

    pattern_id: str

    # Pattern definition (feature ranges)
    rsi_min: float
    rsi_max: float
    macd_signal: str  # BULLISH/BEARISH/NEUTRAL
    bb_position: str | None = None
    regime: str | None = None

    # Performance metrics
    win_rate: float = 0.0
    avg_pips: float = 0.0
    sample_size: int = 0
    last_updated: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'pattern_id': self.pattern_id,
            'rsi_min': self.rsi_min,
            'rsi_max': self.rsi_max,
            'macd_signal': self.macd_signal,
            'bb_position': self.bb_position,
            'regime': self.regime,
            'win_rate': self.win_rate,
            'avg_pips': self.avg_pips,
            'sample_size': self.sample_size,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
        }


@dataclass
class MemorySnapshot:
    """
    MI (Market Intelligence) Memory - recent context for INoT agents.

    Loaded from SQLite, aggregated from recent decisions + outcomes.
    This is what gets passed to INoT agents for decision-making.
    """

    recent_decisions: list[dict[str, Any]] = field(default_factory=list)
    current_regime: str | None = None
    win_rate_30d: float | None = None
    avg_win_pips: float | None = None
    avg_loss_pips: float | None = None
    total_trades_30d: int | None = None
    similar_patterns: list[dict[str, Any]] = field(default_factory=list)

    def to_summary(self, max_tokens: int = 500) -> str:
        """
        Convert to text summary for LLM prompt.

        Args:
            max_tokens: Approximate token budget for summary

        Returns:
            Human-readable summary of memory state
        """
        lines = []

        # Recent performance
        if self.win_rate_30d is not None:
            lines.append(
                f"Recent Performance (30d): {self.win_rate_30d:.1%} win rate, {self.total_trades_30d} trades"
            )

        if self.avg_win_pips and self.avg_loss_pips:
            lines.append(
                f"Average: +{self.avg_win_pips:.1f} pips (wins), -{self.avg_loss_pips:.1f} pips (losses)"
            )

        # Current regime
        if self.current_regime:
            lines.append(f"Current Market Regime: {self.current_regime}")

        # Recent decisions (last 3)
        if self.recent_decisions:
            lines.append(f"\nLast {min(3, len(self.recent_decisions))} Decisions:")
            for dec in self.recent_decisions[:3]:
                lines.append(
                    f"  - {dec.get('action')} {dec.get('symbol')} @ {dec.get('confidence', 0):.2f} confidence"
                )

        # Similar patterns
        if self.similar_patterns:
            lines.append(f"\nSimilar Patterns Found: {len(self.similar_patterns)}")
            for pattern in self.similar_patterns[:2]:
                lines.append(
                    f"  - {pattern.get('win_rate', 0):.1%} win rate ({pattern.get('sample_size', 0)} trades)"
                )

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'recent_decisions': self.recent_decisions,
            'current_regime': self.current_regime,
            'win_rate_30d': self.win_rate_30d,
            'avg_win_pips': self.avg_win_pips,
            'avg_loss_pips': self.avg_loss_pips,
            'total_trades_30d': self.total_trades_30d,
            'similar_patterns': self.similar_patterns,
        }
