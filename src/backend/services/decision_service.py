"""In-memory decision feed used by the UI and socket layer."""

from __future__ import annotations

import random
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, Iterable, List


@dataclass(slots=True)
class AgentInsight:
    """Insight contributed by one of the decision agents."""

    agent: str
    statement: str


@dataclass(slots=True)
class DecisionRecord:
    """Normalized decision payload shared with the frontend."""

    id: str
    timestamp: datetime
    action: str
    symbol: str
    confidence: float
    summary: str
    rationale: str
    risk_score: float
    agent_insights: List[AgentInsight] = field(default_factory=list)

    def to_payload(self) -> dict:
        """Serialize record to JSON-friendly structure."""

        return {
            "id": self.id,
            "timestamp": int(self.timestamp.timestamp() * 1000),
            "action": self.action,
            "symbol": self.symbol,
            "confidence": self.confidence,
            "summary": self.summary,
            "rationale": self.rationale,
            "riskScore": self.risk_score,
            "agentInsights": [
                {"agent": insight.agent, "statement": insight.statement}
                for insight in self.agent_insights
            ],
        }


class DecisionService:
    """Stateful service that fabricates realistic looking decisions."""

    def __init__(self, *, history_limit: int = 20) -> None:
        self._history: Deque[DecisionRecord] = deque(maxlen=history_limit)
        self._rng = random.Random("decision-feed")
        self._seed_initial_decisions()

    def _seed_initial_decisions(self) -> None:
        for symbol in ("EURUSD", "GBPUSD", "USDJPY"):
            self.create_decision(symbol=symbol)

    def list_decisions(self, *, limit: int | None = None) -> list[dict]:
        """Return most recent decisions as dictionaries."""

        records: Iterable[DecisionRecord] = self._history
        if limit is not None:
            records = list(records)[-limit:]
        return [record.to_payload() for record in reversed(list(records))]

    def create_decision(self, *, symbol: str) -> dict:
        """Create a new decision and append it to the history."""

        now = datetime.now(timezone.utc)
        action = self._rng.choices(["BUY", "SELL", "HOLD"], weights=[0.4, 0.35, 0.25])[0]
        confidence = max(0.35, min(0.92, self._rng.normalvariate(0.65, 0.12)))
        risk_score = max(0.1, min(0.95, 1 - confidence + self._rng.random() * 0.2))
        summary = self._summaries(action=action)
        rationale = self._rationales(action=action, symbol=symbol)
        insights = self._agent_insights(action=action, symbol=symbol)

        record = DecisionRecord(
            id=str(uuid.uuid4()),
            timestamp=now,
            action=action,
            symbol=symbol,
            confidence=round(confidence, 2),
            summary=summary,
            rationale=rationale,
            agent_insights=insights,
            risk_score=round(risk_score, 2),
        )
        self._history.append(record)
        return record.to_payload()

    # Helpers -----------------------------------------------------------------
    def _summaries(self, *, action: str) -> str:
        mapping = {
            "BUY": "Momentum alignment with supportive sentiment delta.",
            "SELL": "Macro drag with weakening order-book participation.",
            "HOLD": "Signals conflicted – preserving capital while volatility settles.",
        }
        return mapping[action]

    def _rationales(self, *, action: str, symbol: str) -> str:
        base = {
            "BUY": "Price structure retains higher-lows; liquidity pockets layered below.",
            "SELL": "Rate expectations drift lower; sentiment dispersion widening.",
            "HOLD": "Awaiting confirmation from macro calendar and liquidity regime.",
        }[action]
        return f"{symbol}: {base}"

    def _agent_insights(self, *, action: str, symbol: str) -> list[AgentInsight]:
        statements = {
            "BUY": [
                "Market Intelligence", "News sentiment shifted +0.34 in last 5 min.",
                "Low-Level Reflection", "Latency stable; microstructure supportive.",
                "High-Level Reflection", "Risk budget intact, macro flows constructive.",
                "Decision Agent", "Deploy 1.25% risk with stop under session VWAP.",
            ],
            "SELL": [
                "Market Intelligence", "Negative macro surprise index reinforcing downside.",
                "Low-Level Reflection", "Order-book imbalance favoring offers by 12%.",
                "High-Level Reflection", "Portfolio beta stretched; trimming high beta FX.",
                "Decision Agent", "Scale in via 2 tranches, target weekly value area.",
            ],
            "HOLD": [
                "Market Intelligence", "Headline velocity neutral, crowd sentiment indecisive.",
                "Low-Level Reflection", "Spread widening while liquidity retreats.",
                "High-Level Reflection", "Systematic sleeve at risk limits – caution advised.",
                "Decision Agent", "Monitoring catalysts before adjusting stance.",
            ],
        }[action]

        return [
            AgentInsight(agent=statements[i], statement=statements[i + 1])
            for i in range(0, len(statements), 2)
        ]


__all__ = ["DecisionService"]
