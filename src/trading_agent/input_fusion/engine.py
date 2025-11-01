"""
Input Fusion Engine - Main orchestrator for multi-stream data fusion
Coordinates streams, alignment, and buffering
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from .data_stream import DataStream
from .fusion_buffer import FusedSnapshot, FusionBuffer
from .temporal_aligner import TemporalAligner


class InputFusionEngine:
    """Main engine for input fusion"""

    def __init__(
        self,
        sync_window_ms: int = 100,
        buffer_capacity: int = 1000,
        archive_size: int = 100,
        cleanup_interval_s: int = 60,
    ):
        """
        Initialize input fusion engine

        Args:
            sync_window_ms: Temporal alignment window in milliseconds
            buffer_capacity: Fusion buffer capacity
            archive_size: Archive buffer size
            cleanup_interval_s: Cleanup interval in seconds
        """
        self.sync_window_ms = sync_window_ms
        self.aligner = TemporalAligner(sync_window_ms=sync_window_ms)
        self.buffer = FusionBuffer(capacity=buffer_capacity, archive_size=archive_size)
        self.streams: dict[str, DataStream] = {}
        self.cleanup_interval = cleanup_interval_s
        self.is_running = False
        self._fusion_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None
        self.fusion_count = 0

    def add_stream(self, stream: DataStream) -> None:
        """
        Add data stream to engine

        Args:
            stream: DataStream to add
        """
        self.streams[stream.stream_id] = stream

    def remove_stream(self, stream_id: str) -> None:
        """
        Remove data stream from engine

        Args:
            stream_id: Stream ID to remove
        """
        if stream_id in self.streams:
            del self.streams[stream_id]

    async def start(self) -> None:
        """Start fusion engine"""
        if self.is_running:
            return

        # Start all streams
        for stream in self.streams.values():
            await stream.start()

        self.is_running = True

        # Start fusion loop
        self._fusion_task = asyncio.create_task(self._fusion_loop())

        # Start cleanup loop
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop fusion engine"""
        self.is_running = False

        # Cancel tasks
        if self._fusion_task:
            self._fusion_task.cancel()
            try:
                await self._fusion_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Stop all streams
        for stream in self.streams.values():
            await stream.stop()

    async def close(self) -> None:
        """Close engine and cleanup"""
        await self.stop()

        # Close all streams
        for stream in self.streams.values():
            await stream.close()

        self.streams.clear()

    async def _fusion_loop(self) -> None:
        """Main fusion loop"""
        while self.is_running:
            try:
                # Collect events from all streams
                tasks = [
                    stream.get_event(timeout=0.1) for stream in self.streams.values()
                ]

                if tasks:
                    events = await asyncio.gather(*tasks, return_exceptions=True)

                    # Add events to aligner
                    for event in events:
                        if event and not isinstance(event, Exception):
                            self.aligner.add_event(event)

                    # Get aligned events
                    aligned = self.aligner.get_aligned_events()

                    if aligned:
                        # Create fused snapshot
                        snapshot = self._create_snapshot(aligned)
                        self.buffer.add_snapshot(snapshot)
                        self.fusion_count += 1

                # Small delay
                await asyncio.sleep(0.01)

            except Exception:
                # Log error but continue
                await asyncio.sleep(1.0)

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup loop"""
        while self.is_running:
            try:
                # Wait for cleanup interval
                await asyncio.sleep(self.cleanup_interval)

                # Cleanup old events from aligner
                cutoff_time = datetime.now() - timedelta(seconds=self.cleanup_interval)
                removed = self.aligner.cleanup_old_events(cutoff_time)

            except Exception:
                pass

    def _create_snapshot(self, aligned_events: dict[str, Any]) -> FusedSnapshot:
        """
        Create fused snapshot from aligned events

        Args:
            aligned_events: Dict of stream_id -> event

        Returns:
            FusedSnapshot
        """
        # Extract data from events
        data = {}
        for stream_id, event in aligned_events.items():
            data[stream_id] = event.data

        # Use latest timestamp
        timestamps = [event.timestamp for event in aligned_events.values()]
        latest_timestamp = max(timestamps) if timestamps else datetime.now()

        snapshot = FusedSnapshot(
            timestamp=latest_timestamp,
            data=data,
            metadata={
                "stream_count": len(aligned_events),
                "stream_ids": list(aligned_events.keys()),
            },
        )

        return snapshot

    def get_latest_snapshot(self) -> FusedSnapshot | None:
        """Get latest fused snapshot"""
        snapshots = self.buffer.get_latest(count=1)
        return snapshots[0] if snapshots else None

    def get_latest_snapshots(self, count: int = 10) -> list[FusedSnapshot]:
        """Get latest N snapshots"""
        return self.buffer.get_latest(count=count)

    def get_stats(self) -> dict[str, Any]:
        """Get engine statistics"""
        stream_stats = {
            stream_id: stream.get_stats()
            for stream_id, stream in self.streams.items()
        }

        return {
            "is_running": self.is_running,
            "stream_count": len(self.streams),
            "fusion_count": self.fusion_count,
            "sync_window_ms": self.sync_window_ms,
            "streams": stream_stats,
            "aligner": self.aligner.get_stats(),
            "buffer": self.buffer.get_stats(),
            "memory": self.buffer.get_memory_usage(),
        }
