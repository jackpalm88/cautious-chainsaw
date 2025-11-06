"""Decision feed endpoints."""

from fastapi import APIRouter, Depends

from backend.services import get_decision_service
from backend.services.decision_service import DecisionService

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("", summary="List recent decisions")
def list_decisions(service: DecisionService = Depends(get_decision_service)) -> list[dict]:
    """Return recent decisions."""

    return service.list_decisions()
