"""Smoke tests for the FastAPI surface area."""

from __future__ import annotations

import asyncio
import contextlib
import importlib
import importlib.util
import socket
import threading
import time
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

if importlib.util.find_spec("fastapi") is None:  # pragma: no cover - optional dependency
    pytest.skip("fastapi not installed", allow_module_level=True)

if importlib.util.find_spec("socketio") is None:  # pragma: no cover - optional dependency
    pytest.skip("python-socketio not installed", allow_module_level=True)

if importlib.util.find_spec("uvicorn") is None:  # pragma: no cover - optional dependency
    pytest.skip("uvicorn not installed", allow_module_level=True)

import socketio

_fastapi_testclient = importlib.import_module("fastapi.testclient")
_backend_app = importlib.import_module("backend.app")
_uvicorn = importlib.import_module("uvicorn")
TestClient = _fastapi_testclient.TestClient
create_api_app = _backend_app.create_api_app
create_app = _backend_app.create_app


@contextlib.asynccontextmanager
async def run_uvicorn_app(host: str = "127.0.0.1", port: int | None = None):
    app = create_app()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, port or 0))
        assigned_port = sock.getsockname()[1]

    config = _uvicorn.Config(app=app, host=host, port=assigned_port, log_level="error")
    server = _uvicorn.Server(config=config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    for _ in range(50):
        if getattr(server, "started", False):
            break
        await asyncio.sleep(0.1)
    else:
        raise RuntimeError("Socket server failed to start in time")

    try:
        yield f"http://{host}:{assigned_port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def get_client() -> TestClient:
    return TestClient(create_api_app())


def test_health_endpoint() -> None:
    client = get_client()
    start = time.perf_counter()
    response = client.get("/health")
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert elapsed < 0.2


def test_list_strategies() -> None:
    client = get_client()
    start = time.perf_counter()
    response = client.get("/api/strategies")
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    strategies = response.json()
    assert isinstance(strategies, list)
    assert any(strategy["id"] == "momentum-pulse-v5" for strategy in strategies)
    assert elapsed < 0.2


def test_run_backtest() -> None:
    client = get_client()
    payload = {"strategyId": "momentum-pulse-v5", "symbol": "EURUSD", "bars": 120}
    start = time.perf_counter()
    response = client.post("/api/backtests/run", json=payload)
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    data = response.json()
    assert data["strategy"] == "momentum-pulse-v5"
    assert len(data["equityCurve"]) == 120
    assert data["metrics"]["trades"] >= 0
    assert elapsed < 0.2


def test_list_decisions() -> None:
    client = get_client()
    start = time.perf_counter()
    response = client.get("/api/decisions")
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    decisions = response.json()
    assert isinstance(decisions, list)
    assert decisions, "Should return at least one decision"
    required_keys = {"id", "timestamp", "action", "symbol", "confidence"}
    assert required_keys.issubset(decisions[0].keys())
    assert elapsed < 0.2


@pytest.mark.asyncio
async def test_fusion_stream_produces_updates() -> None:
    updates: list[dict] = []
    decision_updates: list[dict] = []

    async with run_uvicorn_app() as base_url:
        client = socketio.AsyncClient()

        update_event = asyncio.Event()
        decision_event = asyncio.Event()

        @client.event
        async def fusion_update(payload: dict) -> None:
            updates.append(payload)
            if len(updates) >= 2:
                update_event.set()

        @client.event
        async def decision_update(payload: dict) -> None:
            decision_updates.append(payload)
            decision_event.set()

        await client.connect(base_url, transports=["websocket"])
        await client.emit("subscribe_fusion", {"symbol": "EURUSD"})

        await asyncio.wait_for(update_event.wait(), timeout=6)
        # Decision updates are stochastic; give a window but do not fail test if absent.
        try:
            await asyncio.wait_for(decision_event.wait(), timeout=6)
        except TimeoutError:
            pass

        await client.disconnect()

    assert updates, "Expected fusion updates to arrive"
    assert updates[0]["symbol"] == "EURUSD"
    assert updates[0]["price"]["close"] > 0
    assert all("timestamp" in update for update in updates)
    if decision_updates:
        assert decision_updates[0]["symbol"] == "EURUSD"
