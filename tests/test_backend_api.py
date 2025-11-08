"""Smoke tests for the FastAPI surface area."""

from __future__ import annotations

import importlib
import importlib.util
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

if importlib.util.find_spec("fastapi") is None:  # pragma: no cover - optional dependency
    pytest.skip("fastapi not installed", allow_module_level=True)

_fastapi_testclient = importlib.import_module("fastapi.testclient")
_backend_app = importlib.import_module("backend.app")
TestClient = _fastapi_testclient.TestClient
create_api_app = _backend_app.create_api_app


def get_client() -> TestClient:
    return TestClient(create_api_app())


def test_health_endpoint() -> None:
    client = get_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_redirects_to_docs() -> None:
    client = get_client()
    response = client.get("/", follow_redirects=False)
    assert response.status_code in {301, 302, 303, 307, 308}
    assert response.headers["location"].endswith("/docs")


def test_favicon_returns_no_content() -> None:
    client = get_client()
    response = client.get("/favicon.ico")
    assert response.status_code == 204
    assert response.content == b""


def test_list_strategies() -> None:
    client = get_client()
    response = client.get("/api/strategies")
    assert response.status_code == 200
    strategies = response.json()
    assert isinstance(strategies, list)
    assert any(strategy["id"] == "momentum-pulse-v5" for strategy in strategies)


def test_run_backtest() -> None:
    client = get_client()
    payload = {"strategyId": "momentum-pulse-v5", "symbol": "EURUSD", "bars": 120}
    response = client.post("/api/backtests/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["strategy"] == "momentum-pulse-v5"
    assert len(data["equityCurve"]) == 120
    assert data["metrics"]["trades"] >= 0


def test_list_decisions() -> None:
    client = get_client()
    response = client.get("/api/decisions")
    assert response.status_code == 200
    decisions = response.json()
    assert isinstance(decisions, list)
    assert decisions, "Should return at least one decision"
    required_keys = {"id", "timestamp", "action", "symbol", "confidence"}
    assert required_keys.issubset(decisions[0].keys())
