"""Service dependency helpers for the backend API."""

from functools import lru_cache

from backend.config import get_settings
from backend.services.backtest_service import BacktestService
from backend.services.decision_service import DecisionService


@lru_cache(maxsize=1)
def get_backtest_service() -> BacktestService:
    return BacktestService()


@lru_cache(maxsize=1)
def get_decision_service() -> DecisionService:
    settings = get_settings()
    return DecisionService(history_limit=settings.decision_history_limit)


__all__ = ["get_backtest_service", "get_decision_service"]
