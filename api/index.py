"""Minimal Vercel Python Function exposing FastAPI app at /api."""

import os
import sys

from fastapi import APIRouter

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from backend.app import create_api_app

app = create_api_app()

_root = APIRouter()


@_root.get("/")
def root() -> dict[str, str | bool]:
    return {"ok": True, "where": "/api", "health": "/api/health"}


app.include_router(_root, prefix="")
