"""Fallback static test runner for environments without pytest."""

from __future__ import annotations

import compileall
import importlib
import json
import pkgutil
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
REPORTS_PATH = PROJECT_ROOT / "reports"
PACKAGE_NAME = "trading_agent"


def _discover_module_names() -> list[str]:
    """Return all module names within the trading_agent package."""

    package_path = SRC_PATH / PACKAGE_NAME
    if not package_path.exists():
        return []

    module_names = [PACKAGE_NAME]
    for module_info in pkgutil.walk_packages([str(package_path)], prefix=f"{PACKAGE_NAME}."):
        module_names.append(module_info.name)
    return module_names


def check_imports() -> dict[str, Any]:
    """Import every module in the trading_agent package tree."""

    src_str = str(SRC_PATH)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)
    failures: dict[str, str] = {}
    optional: dict[str, str] = {}
    optional_modules = {"MetaTrader5"}
    for module_name in _discover_module_names():
        try:
            importlib.import_module(module_name)
        except ModuleNotFoundError as exc:  # pragma: no cover - diagnostic path
            missing_name = getattr(exc, "name", None)
            if missing_name in optional_modules:
                optional[module_name] = missing_name or repr(exc)
                continue
            failures[module_name] = repr(exc)
        except Exception as exc:  # pragma: no cover - diagnostic path
            failures[module_name] = repr(exc)
    status = not failures
    print("check_imports: OK" if status else "check_imports: FAILED")
    return {
        "status": "OK" if status else "FAILED",
        "failures": failures,
        "optional_skipped": optional,
    }


def compile_modules() -> dict[str, Any]:
    """Byte-compile all modules under src/ to validate syntax."""

    compiled = compileall.compile_dir(str(SRC_PATH), quiet=1)
    status = bool(compiled)
    print("compile_modules: OK" if status else "compile_modules: FAILED")
    return {"status": "OK" if status else "FAILED"}


def check_docstrings() -> dict[str, Any]:
    """Ensure each module in the trading_agent package defines a docstring."""

    missing: list[str] = []
    optional: dict[str, str] = {}
    optional_modules = {"MetaTrader5"}
    for module_name in _discover_module_names():
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:  # pragma: no cover - diagnostic path
            missing_name = getattr(exc, "name", None)
            if missing_name in optional_modules:
                optional[module_name] = missing_name or repr(exc)
                continue
            missing.append(f"{module_name} (import failed: {exc!r})")
        except Exception as exc:  # pragma: no cover - diagnostic path
            missing.append(f"{module_name} (import failed: {exc!r})")
            continue
        docstring = getattr(module, "__doc__", None)
        if not docstring or not docstring.strip():
            missing.append(module_name)
    status = not missing
    print("check_docstrings: OK" if status else "check_docstrings: FAILED")
    return {
        "status": "OK" if status else "FAILED",
        "missing": missing,
        "optional_skipped": optional,
    }


def main() -> None:
    """Execute fallback checks and write a consolidated report."""

    REPORTS_PATH.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {}
    results["check_imports"] = check_imports()
    results["compile_modules"] = compile_modules()
    results["check_docstrings"] = check_docstrings()

    report_path = REPORTS_PATH / "static_test_results.json"
    report_path.write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
