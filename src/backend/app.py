"""FastAPI + Socket.IO application entrypoint."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import routes
from backend.config import get_settings
from backend.services import get_decision_service
from backend.services.fusion_service import FusionSocketService

if TYPE_CHECKING:
    import socketio


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
    app.include_router(routes.health.router, prefix="")
    app.include_router(routes.strategies.router, prefix=api_prefix)
    app.include_router(routes.backtests.router, prefix=api_prefix)
    app.include_router(routes.decisions.router, prefix=api_prefix)
    return app


def create_app() -> socketio.ASGIApp:
    """Create ASGI application exposing both HTTP API and Socket.IO.

    Lazy-import ``socketio`` so REST-only deployments (e.g. Vercel /api)
    do not require ``python-socketio`` to be installed.
    """

    import socketio  # defer import until required

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
