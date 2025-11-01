"""Utility helpers for validating external LLM integrations.

The original project ships a large notebook-style script that users can run
locally to sanity check whether their environment has everything required to
call third-party LLM APIs.  For the purposes of the kata we keep the module
lightweight but still preserve the spirit of the checks:

* avoid importing heavy optional dependencies eagerly – they may not be
  installed for contributors who are only working on the core trading logic;
* surface actionable messages to the caller instead of raising cryptic
  `ImportError` exceptions; and
* perform lightweight network connectivity checks without using additional
  third-party dependencies such as :mod:`requests`.

The functions below are intentionally side-effect free, making them easy to
unit test.  A higher-level CLI or notebook can build on top of them and decide
how to present any issues to the user.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from typing import Iterable
from urllib.error import URLError
from urllib.request import Request, urlopen

ANTHROPIC_PACKAGE_NAME = "anthropic"
ANTHROPIC_HEALTHCHECK_URL = "https://api.anthropic.com"


@dataclass(frozen=True)
class CheckMessage:
    """Structured result emitted by the environment diagnostics."""

    level: str
    message: str


def _package_available(package_name: str) -> bool:
    """Return ``True`` when *package_name* is importable.

    Using :func:`importlib.util.find_spec` avoids importing the package eagerly
    which keeps the diagnostics lightweight and suppresses "imported but
    unused" warnings from static analysers such as ``ruff``.
    """

    return find_spec(package_name) is not None


def check_anthropic_dependencies() -> list[CheckMessage]:
    """Validate local support required to talk to the Anthropic API."""

    messages: list[CheckMessage] = []

    if _package_available(ANTHROPIC_PACKAGE_NAME):
        messages.append(CheckMessage("info", "✅ Anthropic package installed"))
    else:
        messages.append(
            CheckMessage(
                "warning",
                "⚠️ Anthropic package is missing – install trading-agent[llm]",
            )
        )

    request = Request(ANTHROPIC_HEALTHCHECK_URL, method="HEAD")
    try:
        with urlopen(request, timeout=5):
            messages.append(CheckMessage("info", "✅ Connectivity to Anthropic API"))
    except URLError as exc:  # pragma: no cover - network failures are hard to simulate
        messages.append(
            CheckMessage(
                "warning",
                "⚠️ Cannot reach Anthropic API (check network)",
            )
        )
        if exc.reason:
            messages.append(
                CheckMessage("debug", f"ℹ️ Connectivity check failed: {exc.reason}")
            )

    return messages


def summarise(messages: Iterable[CheckMessage]) -> str:
    """Return a newline separated string suitable for CLI printing."""

    return "\n".join(message.message for message in messages)


__all__ = [
    "CheckMessage",
    "check_anthropic_dependencies",
    "summarise",
]
