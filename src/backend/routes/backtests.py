"""Backtest related HTTP endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.services import get_backtest_service
from backend.services.backtest_service import BacktestService

router = APIRouter(prefix="/backtests", tags=["backtests"])


class BacktestRunRequest(BaseModel):
    strategy_id: str = Field(alias="strategyId")
    symbol: str = "EURUSD"
    bars: int = Field(default=240, ge=50, le=2000)


class BacktestRunResponse(BaseModel):
    id: str
    strategy: str
    symbol: str
    generatedAt: datetime
    metrics: dict
    equityCurve: list[dict]
    drawdownCurve: list[dict]
    trades: list[dict]


@router.post("/run", response_model=BacktestRunResponse, summary="Run a backtest")
def run_backtest(
    payload: BacktestRunRequest,
    service: BacktestService = Depends(get_backtest_service),
) -> BacktestRunResponse:
    """Trigger a backtest execution."""

    result = service.run_backtest(
        strategy_id=payload.strategy_id,
        symbol=payload.symbol,
        bars=payload.bars,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Backtest failed to generate results")

    return BacktestRunResponse(**result)
