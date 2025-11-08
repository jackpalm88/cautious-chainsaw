"""Expose the FastAPI application for Vercel."""

from src.backend.app import create_api_app

app = create_api_app()
