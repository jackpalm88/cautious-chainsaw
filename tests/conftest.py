"""Pytest configuration helpers for the test suite."""

from __future__ import annotations

import asyncio
import inspect

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers used across the suite."""
    config.addinivalue_line(
        "markers", "asyncio: Tests that require asynchronous event loop support"
    )


@pytest.fixture
def event_loop() -> asyncio.AbstractEventLoop:
    """Provide an isolated event loop for async tests."""
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """Allow running async test functions without external plugins."""
    if inspect.iscoroutinefunction(pyfuncitem.obj):
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(pyfuncitem.obj(**pyfuncitem.funcargs))
        finally:
            loop.close()
        return True
    return None
