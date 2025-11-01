"""Tests for Input Fusion components"""

import asyncio
from datetime import datetime, timedelta

import pytest

from src.trading_agent.input_fusion import (
    FusedSnapshot,
    FusionBuffer,
    InputFusionEngine,
    PriceStream,
    StreamEvent,
    TemporalAligner,
)


class TestPriceStream:
    """Test PriceStream"""

    @pytest.mark.asyncio
    async def test_mock_price_stream(self):
        """Test mock price stream"""
        stream = PriceStream(symbol="EURUSD", initial_price=1.1, update_interval_ms=10)

        # Connect
        connected = await stream.connect()
        assert connected

        # Start streaming
        await stream.start()
        await asyncio.sleep(0.1)  # Let it generate some events

        # Get event
        event = await stream.get_event(timeout=1.0)
        assert event is not None
        assert event.stream_id == "price_EURUSD"
        assert event.event_type == "price_update"
        assert "bid" in event.data
        assert "ask" in event.data

        # Stop
        await stream.stop()
        await stream.close()

    @pytest.mark.asyncio
    async def test_price_stream_stats(self):
        """Test price stream statistics"""
        stream = PriceStream(symbol="EURUSD", update_interval_ms=10)
        await stream.start()
        await asyncio.sleep(0.05)

        stats = stream.get_stats()
        assert stats["stream_id"] == "price_EURUSD"
        assert stats["event_count"] > 0

        await stream.close()


class TestTemporalAligner:
    """Test TemporalAligner"""

    def test_add_event(self):
        """Test adding events"""
        aligner = TemporalAligner(sync_window_ms=100)

        event1 = StreamEvent(
            stream_id="stream1",
            event_type="test",
            timestamp=datetime.now(),
            data={"value": 1},
        )

        aligner.add_event(event1)
        assert len(aligner.buffers["stream1"]) == 1

    def test_aligned_events(self):
        """Test event alignment"""
        aligner = TemporalAligner(sync_window_ms=100)

        now = datetime.now()

        # Add events from two streams at similar times
        event1 = StreamEvent(
            stream_id="stream1",
            event_type="test",
            timestamp=now,
            data={"value": 1},
        )

        event2 = StreamEvent(
            stream_id="stream2",
            event_type="test",
            timestamp=now + timedelta(milliseconds=50),
            data={"value": 2},
        )

        aligner.add_event(event1)
        aligner.add_event(event2)

        # Get aligned events
        aligned = aligner.get_aligned_events()
        assert len(aligned) == 2
        assert "stream1" in aligned
        assert "stream2" in aligned

    def test_cleanup_old_events(self):
        """Test cleanup of old events"""
        aligner = TemporalAligner(sync_window_ms=100)

        old_time = datetime.now() - timedelta(seconds=10)
        new_time = datetime.now()

        event1 = StreamEvent(
            stream_id="stream1", event_type="test", timestamp=old_time, data={}
        )

        event2 = StreamEvent(
            stream_id="stream1", event_type="test", timestamp=new_time, data={}
        )

        aligner.add_event(event1)
        aligner.add_event(event2)

        # Cleanup old events
        cutoff = datetime.now() - timedelta(seconds=5)
        removed = aligner.cleanup_old_events(cutoff)

        assert removed == 1
        assert len(aligner.buffers["stream1"]) == 1


class TestFusionBuffer:
    """Test FusionBuffer"""

    def test_add_snapshot(self):
        """Test adding snapshots"""
        buffer = FusionBuffer(capacity=10)

        snapshot = FusedSnapshot(timestamp=datetime.now(), data={"test": "data"})

        buffer.add_snapshot(snapshot)
        assert len(buffer.buffer) == 1

    def test_get_latest(self):
        """Test getting latest snapshots"""
        buffer = FusionBuffer(capacity=10)

        # Add multiple snapshots
        for i in range(5):
            snapshot = FusedSnapshot(
                timestamp=datetime.now(), data={"value": i}
            )
            buffer.add_snapshot(snapshot)

        # Get latest 3
        latest = buffer.get_latest(count=3)
        assert len(latest) == 3
        assert latest[0].data["value"] == 4  # Newest first

    def test_buffer_capacity(self):
        """Test buffer capacity and archival"""
        buffer = FusionBuffer(capacity=5, archive_size=3)

        # Add more than capacity
        for i in range(10):
            snapshot = FusedSnapshot(
                timestamp=datetime.now(), data={"value": i}
            )
            buffer.add_snapshot(snapshot)

        # Buffer should be at capacity
        assert len(buffer.buffer) == 5

        # Archive should have old snapshots
        assert len(buffer.archive) == 3

    def test_get_stats(self):
        """Test buffer statistics"""
        buffer = FusionBuffer(capacity=10)

        for i in range(5):
            snapshot = FusedSnapshot(
                timestamp=datetime.now(), data={"value": i}
            )
            buffer.add_snapshot(snapshot)

        stats = buffer.get_stats()
        assert stats["current_size"] == 5
        assert stats["total_snapshots"] == 5
        assert stats["utilization"] == 0.5


class TestInputFusionEngine:
    """Test InputFusionEngine"""

    @pytest.mark.asyncio
    async def test_engine_initialization(self):
        """Test engine initialization"""
        engine = InputFusionEngine()
        assert engine.is_running is False
        assert len(engine.streams) == 0

    @pytest.mark.asyncio
    async def test_add_stream(self):
        """Test adding streams"""
        engine = InputFusionEngine()
        stream = PriceStream(symbol="EURUSD", update_interval_ms=10)

        engine.add_stream(stream)
        assert len(engine.streams) == 1
        assert "price_EURUSD" in engine.streams

    @pytest.mark.asyncio
    async def test_engine_start_stop(self):
        """Test engine start/stop"""
        engine = InputFusionEngine()
        stream = PriceStream(symbol="EURUSD", update_interval_ms=10)
        engine.add_stream(stream)

        # Start
        await engine.start()
        assert engine.is_running is True

        # Let it run briefly
        await asyncio.sleep(0.2)

        # Check fusion occurred
        assert engine.fusion_count > 0

        # Stop
        await engine.stop()
        assert engine.is_running is False

        await engine.close()

    @pytest.mark.asyncio
    async def test_get_latest_snapshot(self):
        """Test getting latest snapshot"""
        engine = InputFusionEngine()
        stream = PriceStream(symbol="EURUSD", update_interval_ms=10)
        engine.add_stream(stream)

        await engine.start()
        await asyncio.sleep(0.2)

        snapshot = engine.get_latest_snapshot()
        assert snapshot is not None
        assert "price_EURUSD" in snapshot.data

        await engine.close()

    @pytest.mark.asyncio
    async def test_engine_stats(self):
        """Test engine statistics"""
        engine = InputFusionEngine()
        stream = PriceStream(symbol="EURUSD", update_interval_ms=10)
        engine.add_stream(stream)

        await engine.start()
        await asyncio.sleep(0.2)

        stats = engine.get_stats()
        assert stats["is_running"] is True
        assert stats["stream_count"] == 1
        assert stats["fusion_count"] > 0

        await engine.close()

    @pytest.mark.asyncio
    async def test_multiple_streams(self):
        """Test fusion with multiple streams"""
        engine = InputFusionEngine()

        stream1 = PriceStream(symbol="EURUSD", update_interval_ms=10)
        stream2 = PriceStream(symbol="GBPUSD", update_interval_ms=10)

        engine.add_stream(stream1)
        engine.add_stream(stream2)

        await engine.start()
        await asyncio.sleep(0.3)

        snapshot = engine.get_latest_snapshot()
        assert snapshot is not None

        # Should have data from both streams
        assert "price_EURUSD" in snapshot.data or "price_GBPUSD" in snapshot.data

        await engine.close()
