"""Vercel entrypoint exposing the FastAPI application."""

from __future__ import annotations

from pathlib import Path
import sys

# Ensure the src/ directory is available on sys.path so the backend package
# can be imported when running on Vercel's serverless runtime.
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.app import create_api_app

app = create_api_app()
