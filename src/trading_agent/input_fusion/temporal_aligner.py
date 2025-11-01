"""
Temporal Aligner - Synchronizes events from multiple streams
Ensures events are aligned within a time window
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from .data_stream import StreamEvent


class TemporalAligner:
    """Aligns events from multiple streams within a time window"""

    def __init__(self, sync_window_ms: int = 100, max_buffer_size: int = 1000):
        """
        Initialize temporal aligner

        Args:
            sync_window_ms: Synchronization window in milliseconds
            max_buffer_size: Maximum buffer size per stream
        """
        self.sync_window = timedelta(milliseconds=sync_window_ms)
        self.max_buffer_size = max_buffer_size
        self.buffers: dict[str, list[StreamEvent]] = defaultdict(list)
        self.latest_timestamps: dict[str, datetime] = {}
        self.aligned_count = 0
        self.dropped_count = 0

    def add_event(self, event: StreamEvent) -> None:
        """
        Add event to buffer

        Args:
            event: Stream event to add
        """
        stream_id = event.stream_id

        # Update latest timestamp
        self.latest_timestamps[stream_id] = event.timestamp

        # Add to buffer
        self.buffers[stream_id].append(event)

        # Trim buffer if too large
        if len(self.buffers[stream_id]) > self.max_buffer_size:
            self.buffers[stream_id].pop(0)
            self.dropped_count += 1

    def get_aligned_events(
        self, reference_time: datetime | None = None
    ) -> dict[str, StreamEvent]:
        """
        Get aligned events within sync window

        Args:
            reference_time: Reference timestamp (defaults to latest)

        Returns:
            Dict mapping stream_id to aligned event
        """
        if not self.buffers:
            return {}

        # Use latest timestamp as reference if not provided
        if reference_time is None:
            if not self.latest_timestamps:
                return {}
            reference_time = max(self.latest_timestamps.values())

        aligned: dict[str, StreamEvent] = {}

        # Find closest event in each stream within sync window
        for stream_id, events in self.buffers.items():
            if not events:
                continue

            # Find event closest to reference time within window
            best_event = None
            best_delta = None

            for event in events:
                delta = abs((event.timestamp - reference_time).total_seconds())

                if delta <= self.sync_window.total_seconds():
                    if best_delta is None or delta < best_delta:
                        best_event = event
                        best_delta = delta

            if best_event:
                aligned[stream_id] = best_event

        if aligned:
            self.aligned_count += 1

        return aligned

    def cleanup_old_events(self, cutoff_time: datetime) -> int:
        """
        Remove events older than cutoff time

        Args:
            cutoff_time: Cutoff timestamp

        Returns:
            Number of events removed
        """
        removed = 0

        for stream_id in list(self.buffers.keys()):
            original_len = len(self.buffers[stream_id])

            # Keep only events newer than cutoff
            self.buffers[stream_id] = [
                e for e in self.buffers[stream_id] if e.timestamp >= cutoff_time
            ]

            removed += original_len - len(self.buffers[stream_id])

        return removed

    def get_stats(self) -> dict[str, Any]:
        """Get aligner statistics"""
        total_buffered = sum(len(events) for events in self.buffers.values())

        return {
            "sync_window_ms": self.sync_window.total_seconds() * 1000,
            "streams": len(self.buffers),
            "total_buffered": total_buffered,
            "aligned_count": self.aligned_count,
            "dropped_count": self.dropped_count,
            "latest_timestamps": {
                sid: ts.isoformat() for sid, ts in self.latest_timestamps.items()
            },
        }
