# Resilience Error Handling & Circuit Breakers

This guide documents the resilience utilities that live in `src/trading_agent/resilience`.
It explains how to configure circuit breakers, retries, health monitoring, and
fallback handlers to provide graceful degradation around flaky upstream
integrations such as MT5, LLM providers, or market data feeds.

## Circuit Breaker Overview

The circuit breaker mirrors the behaviour of trading venue halt switches. It
prevents cascading failures by opening after repeated errors and only allowing
traffic to resume after the cooling period.

### Key Components

- **`CircuitBreakerConfig`** — holds thresholds for failures, cool-down window,
  and half-open success requirements before the breaker can close again.
- **`CircuitBreaker`** — thread-safe implementation that wraps any callable via
  `execute`. It tracks state transitions (`CLOSED`, `OPEN`, `HALF_OPEN`) and the
  timestamp when the breaker opened.
- **`CircuitBreakerError`** — raised when the breaker denies execution while
  open, making it easy to branch to fallbacks.

### Usage

```python
from trading_agent.resilience import CircuitBreaker, CircuitBreakerConfig

# Configure for MT5 adapter: allow 3 consecutive errors and a 20s cooldown.
breaker = CircuitBreaker(
    CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=20,
        half_open_max_successes=2,
    )
)

result = breaker.execute(mt5_adapter.fetch_positions)
```

Wrap high-risk dependencies and expose the breaker instance via dependency
injection so multiple services share the same state when appropriate.

## Retry Strategies

`RetryStrategy` encapsulates exponential backoff with jitter. The
`run_with_retry` helper accepts an operation and optional error hook to report
progress to observability tooling.

```python
from trading_agent.resilience import run_with_retry, RetryStrategy

policy = RetryStrategy(max_attempts=5, base_delay=0.5, max_delay=5)

positions = run_with_retry(mt5_adapter.fetch_positions, strategy=policy)
```

Combine retries with circuit breakers to avoid retry storms—use the breaker to
open after repeated failures while the retry policy spaces out attempts.

## Health Monitoring

`HealthMonitor` stores a registry of named health checks returning
`ServiceHealth` snapshots. Each snapshot reports status, latency, and optional
metadata for dashboards or alerting.

```python
from trading_agent.resilience import HealthMonitor, ServiceStatus

monitor = HealthMonitor()

@monitor.register("mt5")
def check_mt5():
    start = time.perf_counter()
    try:
        mt5_adapter.ping()
        status = ServiceStatus.HEALTHY
    except Exception as exc:  # noqa: BLE001 - upstream failure should bubble up
        status = ServiceStatus.CRITICAL
        raise
    finally:
        duration = (time.perf_counter() - start) * 1000

    return ServiceHealth(status=status, checked_at=time.time(), latency_ms=duration)
```

Use the aggregated results from `evaluate_all()` to feed readiness probes or
operations dashboards.

## Fallback Handlers

Fallback handlers provide graceful degradation when primary dependencies fail.
The `FallbackRegistry` keeps handlers keyed by capability name and exposes
`execute` and `describe` helpers for command routing and documentation.

```python
from trading_agent.resilience import FallbackRegistry

fallbacks = FallbackRegistry()

@fallbacks.register("position-feed")
def cached_positions() -> list[dict[str, str]]:
    return cached_feed.load()

try:
    positions = breaker.execute(mt5_adapter.fetch_positions)
except CircuitBreakerError:
    positions = fallbacks.execute("position-feed")
```

Document each fallback via the optional `description` argument so that
operations engineers know exactly what the degraded behaviour looks like.

## Putting It Together

The `examples/demo_resilience.py` script shows a holistic flow that combines the
four primitives around a simulated flaky market data feed. Adapt the pattern for
production adapters:

1. Guard external calls with `CircuitBreaker.execute`.
2. Wrap operations inside `run_with_retry` to smooth over transient hiccups.
3. Record health checks via `HealthMonitor` for observability.
4. Provide safe fallbacks through `FallbackRegistry` to keep the agent
   responsive under duress.

By layering these patterns, the trading agent maintains resilience against
transient exchange outages, API rate limits, and other real-world failure modes.
