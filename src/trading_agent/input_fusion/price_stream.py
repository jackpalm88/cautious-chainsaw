"""
Price Stream - Real-time price data stream
Supports mock and WebSocket modes
"""

import asyncio
import random
from datetime import datetime
from typing import Any

from .data_stream import DataStream, StreamEvent


class PriceStream(DataStream):
    """Real-time price data stream"""

    def __init__(
        self,
        symbol: str,
        mode: str = "mock",
        initial_price: float = 1.0,
        volatility: float = 0.001,
        update_interval_ms: int = 100,
        **kwargs,
    ):
        """
        Initialize price stream

        Args:
            symbol: Trading symbol (e.g., "EURUSD")
            mode: "mock" or "websocket"
            initial_price: Starting price (mock mode)
            volatility: Price volatility (mock mode)
            update_interval_ms: Update interval in milliseconds
            **kwargs: Additional args for DataStream
        """
        super().__init__(stream_id=f"price_{symbol}", **kwargs)
        self.symbol = symbol
        self.mode = mode
        self.initial_price = initial_price
        self.volatility = volatility
        self.update_interval = update_interval_ms / 1000.0  # Convert to seconds
        self.current_price = initial_price
        self.websocket = None

    async def connect(self) -> bool:
        """Connect to price source"""
        if self.mode == "mock":
            # Mock mode - always succeeds
            self.current_price = self.initial_price
            return True
        elif self.mode == "websocket":
            # WebSocket mode - would connect to real broker
            # For MVP, we'll simulate connection
            await asyncio.sleep(0.1)
            return True
        else:
            return False

    async def disconnect(self) -> None:
        """Disconnect from price source"""
        if self.websocket:
            # Close WebSocket connection
            await self.websocket.close()
            self.websocket = None

    async def _fetch_data(self) -> StreamEvent | None:
        """Fetch price data"""
        if self.mode == "mock":
            return await self._fetch_mock_price()
        elif self.mode == "websocket":
            return await self._fetch_websocket_price()
        return None

    async def _fetch_mock_price(self) -> StreamEvent:
        """Generate mock price data"""
        # Wait for update interval
        await asyncio.sleep(self.update_interval)

        # Generate price change
        change = random.gauss(0, self.volatility)
        self.current_price *= 1 + change

        # Create price event
        bid = self.current_price
        ask = bid + (bid * 0.0001)  # 1 pip spread

        event = StreamEvent(
            stream_id=self.stream_id,
            event_type="price_update",
            timestamp=datetime.now(),
            data={
                "symbol": self.symbol,
                "bid": bid,
                "ask": ask,
                "mid": (bid + ask) / 2,
                "spread": ask - bid,
            },
            metadata={"mode": "mock", "volatility": self.volatility},
        )

        return event

    async def _fetch_websocket_price(self) -> StreamEvent | None:
        """Fetch price from WebSocket (placeholder for MVP)"""
        # For MVP, simulate WebSocket with mock data
        return await self._fetch_mock_price()

    def get_current_price(self) -> dict[str, Any]:
        """Get current price snapshot"""
        bid = self.current_price
        ask = bid + (bid * 0.0001)

        return {
            "symbol": self.symbol,
            "bid": bid,
            "ask": ask,
            "mid": (bid + ask) / 2,
            "timestamp": datetime.now(),
        }
