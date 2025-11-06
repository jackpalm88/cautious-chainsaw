"""Simple health endpoints for the API."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
def health_check() -> dict:
    """Return basic health information."""

    return {"status": "ok"}
