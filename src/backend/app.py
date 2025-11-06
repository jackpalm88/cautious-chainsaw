"""FastAPI + Socket.IO application entrypoint."""

from __future__ import annotations

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.routes import backtests, chat, decisions, health, strategies
from backend.routes import backtests, decisions, health, strategies
from backend.services import get_decision_service
from backend.services.fusion_service import FusionSocketService


def create_api_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Cautious Chainsaw API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_prefix = settings.api_prefix
    app.include_router(health.router, prefix="")
    app.include_router(strategies.router, prefix=api_prefix)
    app.include_router(backtests.router, prefix=api_prefix)
    app.include_router(decisions.router, prefix=api_prefix)
    app.include_router(chat.router, prefix=api_prefix)
    return app


def create_app() -> socketio.ASGIApp:
    """Create ASGI application exposing both HTTP API and Socket.IO."""

    settings = get_settings()
    api_app = create_api_app()
    sio = socketio.AsyncServer(
        async_mode="asgi",
        cors_allowed_origins=settings.allowed_origins,
        ping_interval=settings.socket_ping_interval,
        ping_timeout=settings.socket_ping_timeout,
    )

    fusion = FusionSocketService(sio=sio, decisions=get_decision_service())
    fusion.register_handlers()

    return socketio.ASGIApp(sio, other_asgi_app=api_app)


app = create_app()
api_app = create_api_app()
__all__ = ["app", "api_app"]
