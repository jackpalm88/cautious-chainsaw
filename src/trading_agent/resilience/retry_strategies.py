"""Retry helpers with Nasdaq-style exponential backoff and jitter."""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Generator, Iterable
from dataclasses import dataclass
from typing import TypeVar

__all__ = ["RetryStrategy", "exponential_backoff", "run_with_retry", "RetryError"]

_ResultT = TypeVar("_ResultT")


class RetryError(RuntimeError):
    """Raised when the retry budget is exhausted."""


@dataclass(frozen=True)
class RetryStrategy:
    """Configuration for exponential backoff with decorrelated jitter.

    The parameters follow AWS architecture guidelines and work well for
    financial APIs that suffer from brief bursts of instability.
    """

    max_attempts: int = 5
    base_delay: float = 0.5
    max_delay: float = 30.0
    multiplier: float = 2.0
    jitter_ratio: float = 0.2

    def schedule(self) -> Generator[float, None, None]:
        """Yields the delay before each retry."""

        delay = self.base_delay
        for _attempt in range(self.max_attempts):
            # Decorrelated jitter helps avoid thundering herds when multiple
            # workers retry the same dependency simultaneously.
            jitter = random.uniform(-self.jitter_ratio, self.jitter_ratio)
            yield max(0.0, min(self.max_delay, delay * (1.0 + jitter)))
            delay = min(self.max_delay, delay * self.multiplier)


def exponential_backoff(strategy: RetryStrategy | None = None) -> Iterable[float]:
    """Convenience wrapper returning the retry delay generator."""

    return (delay for delay in (strategy or RetryStrategy()).schedule())


def run_with_retry(
    operation: Callable[[], _ResultT],
    strategy: RetryStrategy | None = None,
    on_error: Callable[[Exception, int], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> _ResultT:
    """Execute ``operation`` while applying a retry policy.

    Parameters
    ----------
    operation:
        Zero-argument callable representing the potentially flaky task.
    strategy:
        Retry configuration.  Defaults to :class:`RetryStrategy`.
    on_error:
        Optional hook invoked with the exception and attempt number whenever a
        failure occurs.  Can be used for logging or metrics.
    sleep:
        Sleep function injected for tests.
    """

    policy = strategy or RetryStrategy()
    last_error: Exception | None = None

    for attempt, delay in enumerate(policy.schedule(), start=1):
        try:
            return operation()
        except Exception as exc:  # pragma: no cover - runtime failure path
            last_error = exc
            if on_error is not None:
                on_error(exc, attempt)
            if attempt >= policy.max_attempts:
                break
            sleep(delay)

    raise RetryError("retry budget exhausted") from last_error
