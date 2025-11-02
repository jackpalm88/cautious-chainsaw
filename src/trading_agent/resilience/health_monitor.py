"""Simple health monitoring utilities for external dependencies."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum

__all__ = ["ServiceStatus", "ServiceHealth", "HealthMonitor"]


class ServiceStatus(str, Enum):
    """Coarse health states used across the trading agent."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class ServiceHealth:
    """Represents the result of a health check."""

    name: str
    status: ServiceStatus
    checked_at: float
    latency_ms: float | None = None
    details: Mapping[str, str] = field(default_factory=dict)


HealthCheck = Callable[[], ServiceHealth]


class HealthMonitor:
    """Registry of service health checks with thread-safe evaluation."""

    def __init__(self) -> None:
        self._checks: dict[str, HealthCheck] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register(self, name: str, check: HealthCheck) -> None:
        """Register a new health check."""

        with self._lock:
            self._checks[name] = check

    def unregister(self, name: str) -> None:
        with self._lock:
            self._checks.pop(name, None)

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    def evaluate(self, name: str) -> ServiceHealth:
        """Evaluate a single health check by ``name``."""

        with self._lock:
            check = self._checks.get(name)
        if check is None:
            raise KeyError(f"health check '{name}' is not registered")
        return check()

    def evaluate_all(self) -> list[ServiceHealth]:
        """Run every registered health check."""

        with self._lock:
            checks: Iterable[HealthCheck] = list(self._checks.values())
        return [check() for check in checks]

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    @staticmethod
    def timed(check: Callable[[], ServiceStatus]) -> HealthCheck:
        """Wrap a function returning :class:`ServiceStatus` into a full check."""

        def wrapper() -> ServiceHealth:
            start = time.perf_counter()
            status = check()
            latency_ms = (time.perf_counter() - start) * 1000.0
            return ServiceHealth(
                name=getattr(check, "__name__", "anonymous_check"),
                status=status,
                checked_at=time.time(),
                latency_ms=latency_ms,
            )

        return wrapper
