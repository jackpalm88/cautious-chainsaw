"""Socket.IO powered fusion stream emitting market, sentiment, and event data."""

from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime

import socketio

from backend.config import get_settings
from backend.services.decision_service import DecisionService


class FusionSocketService:
    """Manage live socket connections and emit fused payloads."""

    def __init__(self, sio: socketio.AsyncServer, decisions: DecisionService) -> None:
        self._sio = sio
        self._decisions = decisions
        self._tasks: dict[str, asyncio.Task] = {}
        self._settings = get_settings()

    # ------------------------------------------------------------------ Socket
    def register_handlers(self) -> None:
        """Attach socket event handlers."""

        @self._sio.event
        async def connect(sid: str, environ: dict) -> None:  # type: ignore[override]
            await self._sio.emit("connection_status", {"status": "connected"}, to=sid)

        @self._sio.on("subscribe_fusion")
        async def subscribe_fusion(sid: str, data: dict | None = None) -> None:
            symbol = (data or {}).get("symbol", self._settings.fusion_default_symbol)
            await self._start_stream(sid=sid, symbol=symbol)

        @self._sio.event
        async def disconnect(sid: str) -> None:  # type: ignore[override]
            await self._stop_stream(sid)

    # ----------------------------------------------------------------- Internals
    async def _start_stream(self, *, sid: str, symbol: str) -> None:
        await self._stop_stream(sid)
        task = asyncio.create_task(self._emit_loop(sid=sid, symbol=symbol))
        self._tasks[sid] = task

    async def _stop_stream(self, sid: str) -> None:
        task: asyncio.Task | None = self._tasks.pop(sid, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _emit_loop(self, *, sid: str, symbol: str) -> None:
        rng = random.Random(f"{sid}:{symbol}")
        price = 1.08 + rng.random() * 0.01
        sentiment = rng.uniform(-0.1, 0.1)
        article_count = rng.randint(3, 12)
        latency = 60

        try:
            while True:
                timestamp = datetime.now(UTC).timestamp()
                price_change = rng.normalvariate(0, 0.0005)
                price = max(0.2, price + price_change)
                high = price + abs(rng.normalvariate(0, 0.0007))
                low = price - abs(rng.normalvariate(0, 0.0007))
                close = price + rng.normalvariate(0, 0.0003)
                volume = max(100, int(15_000 + rng.normalvariate(0, 2500)))
                sentiment = max(-1.0, min(1.0, sentiment + rng.normalvariate(0, 0.05)))
                article_count = max(0, article_count + rng.randint(-1, 2))
                latency = max(40, min(600, int(latency + rng.normalvariate(0, 20))))

                events = []
                if rng.random() < 0.15:
                    events.append(
                        {
                            "id": f"evt-{uuid_hex(rng)}",
                            "name": rng.choice(
                                [
                                    "ECB Commentary",
                                    "US Initial Claims",
                                    "PMI Flash",
                                    "Fed Speaker",
                                ]
                            ),
                            "impact": rng.choice(["low", "medium", "high"]),
                            "actual": f"{rng.uniform(-0.3, 0.7):.2f}",
                            "forecast": f"{rng.uniform(-0.3, 0.7):.2f}",
                            "timestamp": int(timestamp),
                        }
                    )

                payload = {
                    "symbol": symbol,
                    "timestamp": int(timestamp),
                    "latencyMs": latency,
                    "price": {
                        "open": round(price, 5),
                        "high": round(high, 5),
                        "low": round(low, 5),
                        "close": round(close, 5),
                        "volume": volume,
                    },
                    "sentiment": {
                        "score": round(sentiment, 2),
                        "articleCount": article_count,
                        "latestHeadline": rng.choice(
                            [
                                "Macro flows consolidate around growth outlook",
                                "Liquidity sweep triggers rapid repricing",
                                "Carry dispersion widens amid policy divergence",
                            ]
                        ),
                    },
                    "events": events,
                }

                await self._sio.emit("fusion_update", payload, to=sid)

                if rng.random() < 0.08:
                    decision = self._decisions.create_decision(symbol=symbol)
                    await self._sio.emit("decision_update", decision, to=sid)

                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            return


def uuid_hex(rng: random.Random) -> str:
    """Return a deterministic pseudo-UUID using provided RNG."""

    return f"{rng.getrandbits(64):016x}"


__all__ = ["FusionSocketService"]
