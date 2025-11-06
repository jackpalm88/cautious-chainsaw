"""Smoke tests for the FastAPI surface area."""

import pytest

fastapi = pytest.importorskip('fastapi')

from backend.app import create_api_app
from fastapi.testclient import TestClient


def get_client() -> TestClient:
    return TestClient(create_api_app())


def test_health_endpoint() -> None:
    client = get_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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
