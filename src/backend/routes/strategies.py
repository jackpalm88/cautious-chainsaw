"""Strategy catalog endpoints."""

from fastapi import APIRouter, Depends

from backend.services import get_backtest_service
from backend.services.backtest_service import BacktestService

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("", summary="List available strategies")
def list_strategies(service: BacktestService = Depends(get_backtest_service)) -> list[dict]:
    """Return available backtest strategies."""

    return service.list_strategies()
