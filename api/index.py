"""Vercel Serverless Function entrypoint exposing the FastAPI app under /api."""

import os
import sys
from typing import Any

# Ensure the src/ directory is importable so ``backend`` resolves on Vercel.
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from backend.app import create_api_app

app = create_api_app()


@app.get("/")
def root() -> dict[str, Any]:
    """Provide a simple ping so /api responds with a JSON payload."""

    return {"ok": True, "message": "FastAPI on Vercel is live.", "health": "/api/health"}
