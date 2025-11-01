"""
Pre-Event Risk Manager - Apply confidence penalties before major economic events
Prevents catastrophic losses during unpredictable volatility spikes
"""

from datetime import datetime
from typing import Any

from .event_normalizer import NormalizedEvent


class PreEventRiskManager:
    """Manage trading risk before major economic events"""

    def __init__(self):
        # Proximity thresholds: time_window -> confidence_multiplier
        # Multiplier applied to base confidence based on event proximity
        self.proximity_thresholds = {
            "HIGH": {
                "24h": 0.95,  # Slight confidence reduction
                "4h": 0.80,  # Moderate reduction
                "1h": 0.50,  # Major reduction
                "15m": 0.20,  # Severe reduction
                "5m": 0.05,  # Almost abort trading
            },
            "MEDIUM": {
                "4h": 0.90,  # Slight reduction
                "1h": 0.70,  # Moderate reduction
                "15m": 0.40,  # Major reduction
            },
            "LOW": {
                "1h": 0.85,  # Slight reduction
            },
        }

        # Post-event recovery time (minutes)
        # How long after event to gradually restore confidence
        self.recovery_periods = {
            "HIGH": 30,  # 30 minutes
            "MEDIUM": 15,  # 15 minutes
            "LOW": 5,  # 5 minutes
        }

    def apply_risk_adjustment(
        self,
        base_confidence: float,
        upcoming_events: list[NormalizedEvent],
        current_time: datetime | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """
        Apply confidence penalty based on upcoming event proximity

        Args:
            base_confidence: Base trading confidence (0.0-1.0)
            upcoming_events: List of upcoming events
            current_time: Current time (default: utcnow())

        Returns:
            Tuple of (adjusted_confidence, risk_info)
        """
        if not upcoming_events:
            return base_confidence, {"risk_level": "none", "events": []}

        if current_time is None:
            current_time = datetime.utcnow()

        # Find most impactful upcoming event
        max_impact_event = max(
            upcoming_events, key=lambda x: self._get_impact_priority(x.impact)
        )

        # Calculate time to event
        time_to_event = (max_impact_event.scheduled_time - current_time).total_seconds()
        minutes_to_event = time_to_event / 60

        # Check if event is in the past (post-event period)
        if minutes_to_event < 0:
            return self._apply_post_event_adjustment(
                base_confidence, max_impact_event, abs(minutes_to_event)
            )

        # Apply pre-event confidence penalty
        multiplier = self._get_confidence_multiplier(
            max_impact_event.impact, minutes_to_event
        )

        adjusted_confidence = base_confidence * multiplier

        # Build risk info
        risk_info = {
            "risk_level": self._get_risk_level(multiplier),
            "confidence_multiplier": multiplier,
            "nearest_event": {
                "title": max_impact_event.title,
                "impact": max_impact_event.impact,
                "impact_score": max_impact_event.impact_score,
                "scheduled_time": max_impact_event.scheduled_time.isoformat(),
                "time_to_event_minutes": minutes_to_event,
                "currency": max_impact_event.currency,
                "affected_symbols": max_impact_event.affected_symbols or [],
            },
            "events": [
                {
                    "title": event.title,
                    "impact": event.impact,
                    "scheduled_time": event.scheduled_time.isoformat(),
                    "time_to_event_minutes": (
                        event.scheduled_time - current_time
                    ).total_seconds()
                    / 60,
                }
                for event in upcoming_events
            ],
        }

        return adjusted_confidence, risk_info

    def _apply_post_event_adjustment(
        self,
        base_confidence: float,
        event: NormalizedEvent,
        minutes_since_event: float,
    ) -> tuple[float, dict[str, Any]]:
        """Apply gradual confidence recovery after event"""
        recovery_period = self.recovery_periods.get(event.impact, 15)

        if minutes_since_event >= recovery_period:
            # Full recovery
            return base_confidence, {
                "risk_level": "post_event_recovered",
                "events": [],
            }

        # Gradual recovery
        recovery_progress = minutes_since_event / recovery_period
        multiplier = 0.5 + (0.5 * recovery_progress)  # 0.5 -> 1.0

        adjusted_confidence = base_confidence * multiplier

        risk_info = {
            "risk_level": "post_event_recovery",
            "confidence_multiplier": multiplier,
            "recovery_progress": recovery_progress,
            "recent_event": {
                "title": event.title,
                "impact": event.impact,
                "minutes_since_event": minutes_since_event,
                "recovery_period": recovery_period,
            },
        }

        return adjusted_confidence, risk_info

    def _get_confidence_multiplier(self, impact: str, minutes_to_event: float) -> float:
        """Get confidence multiplier based on event impact and proximity"""
        thresholds = self.proximity_thresholds.get(impact, {})

        # Check each time window
        if minutes_to_event <= 5:
            return thresholds.get("5m", 1.0)
        elif minutes_to_event <= 15:
            return thresholds.get("15m", 1.0)
        elif minutes_to_event <= 60:
            return thresholds.get("1h", 1.0)
        elif minutes_to_event <= 240:
            return thresholds.get("4h", 1.0)
        elif minutes_to_event <= 1440:
            return thresholds.get("24h", 1.0)
        else:
            return 1.0  # No adjustment

    def _get_impact_priority(self, impact: str) -> int:
        """Get numeric priority for impact level"""
        priorities = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        return priorities.get(impact, 0)

    def _get_risk_level(self, multiplier: float) -> str:
        """Get risk level description from multiplier"""
        if multiplier >= 0.90:
            return "low"
        elif multiplier >= 0.70:
            return "moderate"
        elif multiplier >= 0.40:
            return "high"
        elif multiplier >= 0.20:
            return "severe"
        else:
            return "critical"

    def should_halt_trading(
        self,
        upcoming_events: list[NormalizedEvent],
        current_time: datetime | None = None,
    ) -> tuple[bool, str]:
        """
        Determine if trading should be halted

        Args:
            upcoming_events: List of upcoming events
            current_time: Current time (default: utcnow())

        Returns:
            Tuple of (should_halt, reason)
        """
        if not upcoming_events:
            return False, ""

        if current_time is None:
            current_time = datetime.utcnow()

        # Find nearest high impact event
        high_impact_events = [e for e in upcoming_events if e.impact == "HIGH"]

        if not high_impact_events:
            return False, ""

        nearest_event = min(high_impact_events, key=lambda x: x.scheduled_time)
        time_to_event = (nearest_event.scheduled_time - current_time).total_seconds()
        minutes_to_event = time_to_event / 60

        # Halt trading if within 5 minutes of high impact event
        if 0 <= minutes_to_event <= 5:
            return True, f"High impact event '{nearest_event.title}' in {minutes_to_event:.1f} minutes"

        return False, ""

    def get_position_size_adjustment(
        self,
        upcoming_events: list[NormalizedEvent],
        current_time: datetime | None = None,
    ) -> float:
        """
        Get position size adjustment multiplier

        Args:
            upcoming_events: List of upcoming events
            current_time: Current time (default: utcnow())

        Returns:
            Position size multiplier (0.0-1.0)
        """
        if not upcoming_events:
            return 1.0

        if current_time is None:
            current_time = datetime.utcnow()

        # Find most impactful event
        max_impact_event = max(
            upcoming_events, key=lambda x: self._get_impact_priority(x.impact)
        )

        time_to_event = (max_impact_event.scheduled_time - current_time).total_seconds()
        minutes_to_event = time_to_event / 60

        # Position size reduction based on proximity
        if max_impact_event.impact == "HIGH":
            if minutes_to_event <= 5:
                return 0.1  # 10% of normal size
            elif minutes_to_event <= 15:
                return 0.3  # 30% of normal size
            elif minutes_to_event <= 60:
                return 0.5  # 50% of normal size
            elif minutes_to_event <= 240:
                return 0.7  # 70% of normal size
        elif max_impact_event.impact == "MEDIUM":
            if minutes_to_event <= 15:
                return 0.5  # 50% of normal size
            elif minutes_to_event <= 60:
                return 0.7  # 70% of normal size

        return 1.0  # No adjustment

    def get_affected_symbols(
        self, upcoming_events: list[NormalizedEvent]
    ) -> set[str]:
        """
        Get all symbols affected by upcoming events

        Args:
            upcoming_events: List of upcoming events

        Returns:
            Set of affected symbol names
        """
        affected = set()

        for event in upcoming_events:
            if event.affected_symbols:
                affected.update(event.affected_symbols)

        return affected
