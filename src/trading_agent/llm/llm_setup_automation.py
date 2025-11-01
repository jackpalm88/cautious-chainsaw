"""Automation helpers for preparing optional LLM tooling.

The production project exposes a richer CLI that provisions API keys, installs
optional extras, and runs smoke tests.  Recreating that end-to-end flow is
outside the scope of the exercises here; instead we provide a compact module
that demonstrates the same ideas in a testable manner.

The helper focuses on communicating *what* is missing from a developer's
machine so that follow-up actions are straightforward.  The checks are
extensible – simply add new callables to :attr:`LLMSetupAutomation.extra_checks`
when additional diagnostics are required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib.util import find_spec
from typing import Callable, Iterable, Sequence

OptionalCheck = Callable[[], list[str]]


def _missing_modules(modules: Iterable[str]) -> list[str]:
    """Return a sorted list of importable module names that are absent."""

    return sorted(module for module in modules if find_spec(module) is None)


def check_standard_library() -> list[str]:
    """Validate that the Python standard modules we rely on are available."""

    # The modules are part of the standard library on every supported Python
    # version.  The function remains defensive to keep the behaviour consistent
    # with the original script which surfaced actionable error messages.
    missing = _missing_modules(["dataclasses", "json", "typing"])
    if missing:
        return [f"⚠️ Standard library modules missing: {', '.join(missing)}"]
    return ["✅ Standard libraries available"]


def check_llm_clients() -> list[str]:
    """Verify that optional third-party SDKs are installed."""

    missing = _missing_modules(["anthropic", "openai"])
    if missing:
        extras = ", ".join(missing)
        return [
            "⚠️ Optional LLM SDKs missing: "
            f"{extras} (install trading-agent[llm] to enable integrations)",
        ]
    return ["✅ Optional LLM SDKs detected"]


@dataclass
class LLMSetupAutomation:
    """Collect and execute environment checks used by onboarding scripts."""

    extra_checks: Sequence[OptionalCheck] = field(default_factory=tuple)
    logger: Callable[[str], None] = print

    def run(self) -> list[str]:
        """Execute the configured diagnostics and return human friendly lines."""

        issues: list[str] = []

        for check in (check_standard_library, check_llm_clients, *self.extra_checks):
            for message in check():
                issues.append(message)
                self.logger(message)

        return issues


__all__ = [
    "LLMSetupAutomation",
    "check_llm_clients",
    "check_standard_library",
]
