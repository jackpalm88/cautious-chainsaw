"""Aggregate repository integrity signals into a single JSON report."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

STATIC_RESULTS_PATH = Path("reports/static_test_results.json")
LINT_LOG_PATH = Path("reports/lint_results.json")
OUTPUT_PATH = Path("reports/repo_integrity.json")


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Required input file missing: {path}")

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive fallback
        raise ValueError(f"Invalid JSON content in {path}: {exc}") from exc


def _extract_lint_error_count(lint_payload: Any) -> int:
    """Return the total number of lint errors from the Ruff payload."""
    if lint_payload is None:
        return 0

    if isinstance(lint_payload, list):
        return len(lint_payload)

    if isinstance(lint_payload, dict):
        summary = lint_payload.get("summary")
        if isinstance(summary, dict) and "error" in summary:
            return int(summary.get("error", 0))

        messages = lint_payload.get("messages")
        if isinstance(messages, list):
            return len(messages)

    raise ValueError("Unsupported Ruff log structure; expected list or dict with summary/messages.")


def _status_is_ok(section: dict[str, Any]) -> bool:
    return str(section.get("status", "")).strip().upper() == "OK"


def main() -> None:
    static_results = _load_json(STATIC_RESULTS_PATH)
    lint_results = _load_json(LINT_LOG_PATH)

    if not isinstance(static_results, dict):
        raise ValueError("Static test results must be a JSON object.")

    imports_ok = _status_is_ok(static_results.get("check_imports", {}))
    syntax_passed = _status_is_ok(static_results.get("compile_modules", {}))

    lint_errors = _extract_lint_error_count(lint_results)

    recommendation = (
        "ready_for_merge" if lint_errors == 0 and syntax_passed and imports_ok else "requires_manual_fix"
    )

    payload = {
        "lint_errors": lint_errors,
        "syntax_passed": syntax_passed,
        "imports_ok": imports_ok,
        "recommendation": recommendation,
    }

    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
