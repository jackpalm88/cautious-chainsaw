"""
Demo: Input Fusion MVP
Real-time data streaming with temporal alignment
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trading_agent.input_fusion import InputFusionEngine, PriceStream


async def main():
    print("=" * 70)
    print("INPUT FUSION MVP DEMO")
    print("=" * 70)

    # Create fusion engine
    engine = InputFusionEngine(
        sync_window_ms=100,  # 100ms alignment window
        buffer_capacity=1000,
        archive_size=100,
    )

    print("\n1️⃣ CREATING PRICE STREAMS")
    print("-" * 70)

    # Add price streams for multiple symbols
    symbols = ["EURUSD", "GBPUSD", "USDJPY"]
    initial_prices = [1.1, 1.3, 150.0]

    for symbol, price in zip(symbols, initial_prices, strict=False):
        stream = PriceStream(
            symbol=symbol,
            mode="mock",
            initial_price=price,
            volatility=0.0005,  # 0.05% volatility
            update_interval_ms=50,  # 50ms updates
        )
        engine.add_stream(stream)
        print(f"  ✅ Added {symbol} stream (initial: {price:.5f})")

    print(f"\n  Total streams: {len(engine.streams)}")

    print("\n2️⃣ STARTING FUSION ENGINE")
    print("-" * 70)

    await engine.start()
    print("  ✅ Engine started")
    print("  ⏱️  Collecting data...")

    # Let it run for 2 seconds
    await asyncio.sleep(2.0)

    print("\n3️⃣ LATEST FUSED SNAPSHOT")
    print("-" * 70)

    snapshot = engine.get_latest_snapshot()
    if snapshot:
        print(f"  Timestamp: {snapshot.timestamp.strftime('%H:%M:%S.%f')[:-3]}")
        print(f"  Streams: {snapshot.metadata.get('stream_count', 0)}")
        print("\n  📊 PRICES:")
        for _stream_id, data in snapshot.data.items():
            symbol = data["symbol"]
            bid = data["bid"]
            ask = data["ask"]
            spread = data["spread"]
            print(f"    {symbol:8s} Bid: {bid:.5f}  Ask: {ask:.5f}  Spread: {spread:.5f}")
    else:
        print("  ⚠️  No snapshot available")

    print("\n4️⃣ LATEST 5 SNAPSHOTS")
    print("-" * 70)

    snapshots = engine.get_latest_snapshots(count=5)
    print(f"  Retrieved {len(snapshots)} snapshots\n")

    for i, snap in enumerate(snapshots, 1):
        time_str = snap.timestamp.strftime('%H:%M:%S.%f')[:-3]
        stream_count = snap.metadata.get('stream_count', 0)
        print(f"  {i}. {time_str} - {stream_count} streams")

    print("\n5️⃣ ENGINE STATISTICS")
    print("-" * 70)

    stats = engine.get_stats()

    print(f"  Running: {stats['is_running']}")
    print(f"  Fusion Count: {stats['fusion_count']}")
    print(f"  Sync Window: {stats['sync_window_ms']}ms")

    print("\n  📈 BUFFER:")
    buffer_stats = stats['buffer']
    print(f"    Capacity: {buffer_stats['capacity']}")
    print(f"    Current Size: {buffer_stats['current_size']}")
    print(f"    Archive Size: {buffer_stats['archive_size']}")
    print(f"    Total Snapshots: {buffer_stats['total_snapshots']}")
    print(f"    Utilization: {buffer_stats['utilization']:.1%}")

    print("\n  🔄 ALIGNER:")
    aligner_stats = stats['aligner']
    print(f"    Aligned Count: {aligner_stats['aligned_count']}")
    print(f"    Dropped Count: {aligner_stats['dropped_count']}")
    print(f"    Total Buffered: {aligner_stats['total_buffered']}")

    print("\n  💾 MEMORY:")
    memory = stats['memory']
    print(f"    Buffer: {memory['buffer_mb']:.2f} MB")
    print(f"    Archive: {memory['archive_mb']:.2f} MB")
    print(f"    Total: {memory['total_mb']:.2f} MB")

    print("\n  📡 STREAMS:")
    for stream_id, stream_stats in stats['streams'].items():
        print(f"\n    {stream_id}:")
        print(f"      Status: {stream_stats['status']}")
        print(f"      Events: {stream_stats['event_count']}")
        print(f"      Errors: {stream_stats['error_count']}")
        print(f"      Queue: {stream_stats['queue_size']}/{stream_stats['queue_capacity']}")

    print("\n6️⃣ PERFORMANCE METRICS")
    print("-" * 70)

    # Calculate metrics
    if stats['fusion_count'] > 0:
        fusion_rate = stats['fusion_count'] / 2.0  # 2 seconds runtime
        avg_latency = 2000 / stats['fusion_count']  # ms per fusion

        print(f"  Fusion Rate: {fusion_rate:.1f} fusions/sec")
        print(f"  Avg Latency: {avg_latency:.2f}ms per fusion")
        print(f"  Stream Utilization: {len(stats['streams'])} streams")

    print("\n7️⃣ STOPPING ENGINE")
    print("-" * 70)

    await engine.stop()
    print("  ✅ Engine stopped")

    await engine.close()
    print("  ✅ Engine closed")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
