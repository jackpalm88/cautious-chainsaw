"""Fallback helpers to gracefully degrade functionality."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

__all__ = ["FallbackHandler", "FallbackRegistry", "FallbackError"]


class FallbackError(RuntimeError):
    """Raised when no fallback handler is registered."""


@dataclass
class FallbackHandler:
    """Metadata describing a fallback callable."""

    name: str
    handler: Callable[..., Any]
    description: str = ""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.handler(*args, **kwargs)


class FallbackRegistry:
    """Mapping from a capability identifier to fallback handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, FallbackHandler] = {}

    def register(self, capability: str, handler: Callable[..., Any], description: str = "") -> None:
        self._handlers[capability] = FallbackHandler(capability, handler, description)

    def unregister(self, capability: str) -> None:
        self._handlers.pop(capability, None)

    def get(self, capability: str) -> FallbackHandler:
        try:
            return self._handlers[capability]
        except KeyError as exc:  # pragma: no cover - runtime guard
            raise FallbackError(f"no fallback registered for '{capability}'") from exc

    def execute(self, capability: str, *args: Any, **kwargs: Any) -> Any:
        handler = self.get(capability)
        return handler(*args, **kwargs)

    def describe(self, capability: str) -> str | None:
        handler = self._handlers.get(capability)
        if handler is None:
            return None
        return handler.description
