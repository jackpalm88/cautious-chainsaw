from __future__ import annotations

import sys
from pathlib import Path

# Pievienojam repo/src Python ceļu (absolūti, priekšplānā), lai importi strādātu serverless vidē.
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from fastapi import FastAPI  # noqa: E402

from backend.app import create_api_app  # noqa: E402

# Izmantojam tikai HTTP FastAPI app (bez Socket.IO) — Vercel Serverless Functions nebalsta klasiskos websockets.
app: FastAPI = create_api_app()


# Ātrs ping zem /api
@app.get("/")
def root() -> dict[str, object]:
    return {"ok": True, "service": "cautious-chainsaw", "path": "/api"}
