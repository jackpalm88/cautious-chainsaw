"""Circuit breaker primitives for protecting downstream services.

The implementation draws inspiration from market circuit breakers where trading
halts are triggered after repeated failures.  When a downstream dependency is
unstable we trip the breaker, stop issuing calls for a configurable cool-down
period and then cautiously probe recovery with a half-open state.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerState",
    "CircuitBreakerError",
]


class CircuitBreakerError(RuntimeError):
    """Raised when a call is attempted while the circuit is open."""


class CircuitBreakerState(str, Enum):
    """Enumeration capturing the different circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Configuration knobs for the :class:`CircuitBreaker`.

    Attributes
    ----------
    failure_threshold:
        Number of consecutive failures allowed before opening the circuit.
    recovery_timeout:
        Number of seconds to wait after the circuit opens before allowing a
        probe request in the half-open state.
    half_open_max_successes:
        Number of consecutive successes required while half-open to transition
        back to the closed state.
    name:
        Optional identifier useful when logging aggregated metrics.
    clock:
        Optional callable returning the current monotonic time.  Injecting a
        clock makes the breaker deterministic for tests.
    """

    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_successes: int = 2
    name: str = ""
    clock: Callable[[], float] = time.monotonic


_ResponseT = TypeVar("_ResponseT")


class CircuitBreaker(Generic[_ResponseT]):
    """Protects critical sections by short-circuiting on sustained failures.

    The breaker is thread-safe and designed to wrap the potentially flaky call
    site directly.  A simple example::

        breaker = CircuitBreaker()

        def execute_order():
            return breaker.call(trading_gateway.submit_order)

    When the downstream dependency keeps failing the breaker transitions from
    ``CLOSED`` -> ``OPEN`` -> ``HALF_OPEN`` -> ``CLOSED`` as stability returns.
    """

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        self._config = config or CircuitBreakerConfig()
        self._lock = threading.RLock()
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._half_open_success_count = 0
        self._opened_at: float | None = None

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------
    def _now(self) -> float:
        return self._config.clock()

    def _transition_to_open(self) -> None:
        self._state = CircuitBreakerState.OPEN
        self._failure_count = 0
        self._half_open_success_count = 0
        self._opened_at = self._now()

    def _transition_to_half_open(self) -> None:
        self._state = CircuitBreakerState.HALF_OPEN
        self._half_open_success_count = 0

    def _transition_to_closed(self) -> None:
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._half_open_success_count = 0
        self._opened_at = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def state(self) -> CircuitBreakerState:
        """Returns the current breaker state."""

        with self._lock:
            self._update_state_if_needed()
            return self._state

    def call(self, func: Callable[..., _ResponseT], *args, **kwargs) -> _ResponseT:
        """Executes ``func`` if the breaker allows it, otherwise raises.

        Parameters
        ----------
        func:
            Callable representing the protected operation.
        *args, **kwargs:
            Passed straight through to ``func``.

        Raises
        ------
        CircuitBreakerError
            When the breaker is open and the cool-down period has not yet
            elapsed.
        """

        with self._lock:
            self._update_state_if_needed()
            if self._state is CircuitBreakerState.OPEN:
                raise CircuitBreakerError(
                    f"Circuit breaker '{self._config.name or id(self)}' is open"
                )

        try:
            result = func(*args, **kwargs)
        except Exception:
            self.record_failure()
            raise
        else:
            self.record_success()
            return result

    def record_success(self) -> None:
        """Records a successful call and transitions state if needed."""

        with self._lock:
            if self._state is CircuitBreakerState.HALF_OPEN:
                self._half_open_success_count += 1
                if self._half_open_success_count >= self._config.half_open_max_successes:
                    self._transition_to_closed()
            else:
                self._transition_to_closed()

    def record_failure(self) -> None:
        """Records a failed call and potentially opens the circuit."""

        with self._lock:
            if self._state is CircuitBreakerState.HALF_OPEN:
                # First failure while probing -> immediately open again.
                self._transition_to_open()
                return

            self._failure_count += 1
            if self._failure_count >= self._config.failure_threshold:
                self._transition_to_open()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _update_state_if_needed(self) -> None:
        if self._state is CircuitBreakerState.OPEN and self._opened_at is not None:
            elapsed = self._now() - self._opened_at
            if elapsed >= self._config.recovery_timeout:
                self._transition_to_half_open()

    # ------------------------------------------------------------------
    # Decorator utilities
    # ------------------------------------------------------------------
    def decorate(self, func: Callable[..., _ResponseT]) -> Callable[..., _ResponseT]:
        """Decorator form of :meth:`call` for ergonomic usage."""

        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)

        return wrapper
