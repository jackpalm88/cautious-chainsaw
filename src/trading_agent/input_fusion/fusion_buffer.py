"""
Fusion Buffer - Memory-efficient circular buffer for fused data
Stores aligned events with automatic archival
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class FusedSnapshot:
    """Snapshot of fused data from multiple streams"""

    timestamp: datetime
    data: dict[str, Any]  # stream_id -> event data
    metadata: dict[str, Any] | None = None


class FusionBuffer:
    """Circular buffer for fused data snapshots"""

    def __init__(self, capacity: int = 1000, archive_size: int = 100):
        """
        Initialize fusion buffer

        Args:
            capacity: Maximum number of snapshots in active buffer
            archive_size: Number of snapshots to keep in archive
        """
        self.capacity = capacity
        self.archive_size = archive_size
        self.buffer: deque[FusedSnapshot] = deque(maxlen=capacity)
        self.archive: deque[FusedSnapshot] = deque(maxlen=archive_size)
        self.total_snapshots = 0
        self.archived_count = 0

    def add_snapshot(self, snapshot: FusedSnapshot) -> None:
        """
        Add snapshot to buffer

        Args:
            snapshot: Fused snapshot to add
        """
        # If buffer is full, archive oldest snapshot
        if len(self.buffer) >= self.capacity:
            oldest = self.buffer[0]
            self.archive.append(oldest)
            self.archived_count += 1

        self.buffer.append(snapshot)
        self.total_snapshots += 1

    def get_latest(self, count: int = 1) -> list[FusedSnapshot]:
        """
        Get latest N snapshots

        Args:
            count: Number of snapshots to retrieve

        Returns:
            List of latest snapshots (newest first)
        """
        if count <= 0:
            return []

        # Return latest snapshots in reverse order (newest first)
        return list(reversed(list(self.buffer)[-count:]))

    def get_range(self, start_time: datetime, end_time: datetime) -> list[FusedSnapshot]:
        """
        Get snapshots within time range

        Args:
            start_time: Start timestamp
            end_time: End timestamp

        Returns:
            List of snapshots in time range
        """
        return [s for s in self.buffer if start_time <= s.timestamp <= end_time]

    def get_by_index(self, index: int) -> FusedSnapshot | None:
        """
        Get snapshot by index (0 = oldest, -1 = newest)

        Args:
            index: Buffer index

        Returns:
            Snapshot or None if index out of range
        """
        try:
            return self.buffer[index]
        except IndexError:
            return None

    def clear(self) -> None:
        """Clear buffer (keeps archive)"""
        self.buffer.clear()

    def clear_all(self) -> None:
        """Clear buffer and archive"""
        self.buffer.clear()
        self.archive.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get buffer statistics"""
        return {
            "capacity": self.capacity,
            "current_size": len(self.buffer),
            "archive_size": len(self.archive),
            "total_snapshots": self.total_snapshots,
            "archived_count": self.archived_count,
            "utilization": len(self.buffer) / self.capacity if self.capacity > 0 else 0,
        }

    def get_memory_usage(self) -> dict[str, Any]:
        """Estimate memory usage"""
        import sys

        buffer_bytes = sys.getsizeof(self.buffer)
        archive_bytes = sys.getsizeof(self.archive)

        # Rough estimate of snapshot sizes
        if self.buffer:
            sample_snapshot = self.buffer[-1]
            snapshot_bytes = sys.getsizeof(sample_snapshot)
            total_buffer_bytes = buffer_bytes + (snapshot_bytes * len(self.buffer))
            total_archive_bytes = archive_bytes + (snapshot_bytes * len(self.archive))
        else:
            total_buffer_bytes = buffer_bytes
            total_archive_bytes = archive_bytes

        return {
            "buffer_bytes": total_buffer_bytes,
            "archive_bytes": total_archive_bytes,
            "total_bytes": total_buffer_bytes + total_archive_bytes,
            "buffer_mb": total_buffer_bytes / (1024 * 1024),
            "archive_mb": total_archive_bytes / (1024 * 1024),
            "total_mb": (total_buffer_bytes + total_archive_bytes) / (1024 * 1024),
        }
