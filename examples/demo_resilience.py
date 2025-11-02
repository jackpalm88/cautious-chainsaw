"""Demonstration of the resilience toolkit (circuit breakers, retries, fallbacks)."""

from __future__ import annotations

import random
import time
from typing import Iterator

from trading_agent.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    FallbackRegistry,
    HealthMonitor,
    RetryStrategy,
    ServiceStatus,
    run_with_retry,
)


def flaky_exchange_feed(failures: Iterator[bool]) -> str:
    """Simulate a market data call that fails according to ``failures``."""

    try:
        should_fail = next(failures)
    except StopIteration:
        should_fail = False

    if should_fail:
        raise ConnectionError("exchange feed disconnected")
    return "QUOTE: EURUSD 1.07950"


def main() -> None:
    breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1.0, name="exchange-feed"))

    registry = FallbackRegistry()
    registry.register(
        "exchange-feed",
        lambda: "FALLBACK: using last known quote",
        description="Provides stale quote when the live feed is unavailable.",
    )

    # Register a lightweight health check that simply verifies breaker state.
    monitor = HealthMonitor()

    @monitor.timed
    def exchange_health() -> ServiceStatus:
        state = breaker.state
        if state is CircuitBreakerState.OPEN:
            return ServiceStatus.UNAVAILABLE
        if state is CircuitBreakerState.HALF_OPEN:
            return ServiceStatus.DEGRADED
        return ServiceStatus.HEALTHY

    monitor.register("exchange", exchange_health)

    # Sequence of failures (True) and successes (False) to show transitions.
    pattern = iter([True, True, True, False, False, False])

    def execute_feed() -> str:
        return breaker.call(flaky_exchange_feed, pattern)

    retry_policy = RetryStrategy(max_attempts=3, base_delay=0.2, max_delay=1.0)

    for tick in range(6):
        try:
            quote = run_with_retry(execute_feed, strategy=retry_policy, sleep=lambda s: time.sleep(s / 10))
        except Exception:
            quote = registry.execute("exchange-feed")
        print(f"tick={tick} quote={quote} state={breaker.state}")
        time.sleep(0.1)

    print("Health snapshot:")
    for health in monitor.evaluate_all():
        print(f" - {health.name}: {health.status} (latency={health.latency_ms:.2f}ms)")


if __name__ == "__main__":  # pragma: no cover - manual demo
    random.seed(42)
    main()
