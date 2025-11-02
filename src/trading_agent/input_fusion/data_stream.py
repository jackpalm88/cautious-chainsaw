"""
Data Stream - Base class for async data streams
Provides foundation for real-time data ingestion
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class StreamStatus(Enum):
    """Stream status"""

    IDLE = "idle"
    CONNECTING = "connecting"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    CLOSED = "closed"


@dataclass
class StreamEvent:
    """Event from data stream"""

    stream_id: str
    event_type: str
    timestamp: datetime
    data: dict[str, Any]
    metadata: dict[str, Any] | None = None


class DataStream(ABC):
    """Abstract base class for data streams"""

    def __init__(self, stream_id: str, buffer_size: int = 1000):
        self.stream_id = stream_id
        self.buffer_size = buffer_size
        self.status = StreamStatus.IDLE
        self.event_queue: asyncio.Queue[StreamEvent] = asyncio.Queue(maxsize=buffer_size)
        self.error_count = 0
        self.event_count = 0
        self._task: asyncio.Task | None = None

    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to data source

        Returns:
            True if connected successfully
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from data source"""
        pass

    @abstractmethod
    async def _fetch_data(self) -> StreamEvent | None:
        """
        Fetch data from source (implementation-specific)

        Returns:
            StreamEvent or None if no data available
        """
        pass

    async def start(self) -> None:
        """Start streaming data"""
        if self.status == StreamStatus.ACTIVE:
            return

        # Connect if not connected
        if self.status == StreamStatus.IDLE:
            connected = await self.connect()
            if not connected:
                self.status = StreamStatus.ERROR
                return

        self.status = StreamStatus.ACTIVE
        self._task = asyncio.create_task(self._stream_loop())

    async def stop(self) -> None:
        """Stop streaming data"""
        self.status = StreamStatus.PAUSED

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def close(self) -> None:
        """Close stream and cleanup"""
        await self.stop()
        await self.disconnect()
        self.status = StreamStatus.CLOSED

    async def _stream_loop(self) -> None:
        """Main streaming loop"""
        while self.status == StreamStatus.ACTIVE:
            try:
                # Fetch data
                event = await self._fetch_data()

                if event:
                    # Put event in queue (non-blocking)
                    try:
                        self.event_queue.put_nowait(event)
                        self.event_count += 1
                    except asyncio.QueueFull:
                        # Drop oldest event if queue is full
                        try:
                            self.event_queue.get_nowait()
                            self.event_queue.put_nowait(event)
                        except Exception:
                            pass

                # Small delay to prevent busy loop
                await asyncio.sleep(0.001)

            except Exception:
                self.error_count += 1
                if self.error_count > 10:
                    self.status = StreamStatus.ERROR
                    break
                await asyncio.sleep(1.0)  # Back off on error

    async def get_event(self, timeout: float = 1.0) -> StreamEvent | None:
        """
        Get next event from queue

        Args:
            timeout: Timeout in seconds

        Returns:
            StreamEvent or None if timeout
        """
        try:
            return await asyncio.wait_for(self.event_queue.get(), timeout=timeout)
        except TimeoutError:
            return None

    def get_stats(self) -> dict[str, Any]:
        """Get stream statistics"""
        return {
            "stream_id": self.stream_id,
            "status": self.status.value,
            "event_count": self.event_count,
            "error_count": self.error_count,
            "queue_size": self.event_queue.qsize(),
            "queue_capacity": self.buffer_size,
        }
