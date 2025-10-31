"""
Demo: GenerateOrder Execution Tool
Demonstrates order generation and execution via MT5 Bridge
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.trading_agent.adapters.adapter_mock import MockAdapter
from src.trading_agent.adapters.bridge import MT5ExecutionBridge
from src.trading_agent.tools.execution.generate_order import GenerateOrder


def demo_long_order():
    """Demo LONG order execution"""
    print("=" * 60)
    print("LONG ORDER EXECUTION")
    print("=" * 60)

    # Setup adapter and bridge
    adapter = MockAdapter()
    asyncio.run(adapter.connect())
    bridge = MT5ExecutionBridge(adapter=adapter)

    # Create tool
    tool = GenerateOrder(bridge=bridge)

    # Execute LONG order
    result = tool.execute(
        symbol="EURUSD",
        direction="LONG",
        size=0.5,
        stop_loss=1.0900,
        take_profit=1.1100,
        confidence=0.85,
        reasoning="RSI oversold + MACD bullish crossover"
    )

    print("\n📊 ORDER DETAILS:")
    print("  Symbol: EURUSD")
    print("  Direction: LONG")
    print("  Size: 0.5 lots")
    print("  Stop Loss: 1.0900")
    print("  Take Profit: 1.1100")
    print(f"  Confidence: {result.confidence:.2f}")

    if result.value and result.value['success']:
        print("\n✅ EXECUTION SUCCESS:")
        print(f"  Order ID: {result.value['order_id']}")
        print(f"  Fill Price: {result.value['fill_price']:.5f}")
        print(f"  Fill Volume: {result.value['fill_volume']} lots")
        print(f"  Slippage: {result.value.get('slippage_pips', 0):.2f} pips")
        print(f"  Status: {result.value['status']}")
    else:
        print("\n❌ EXECUTION FAILED:")
        print(f"  Error: {result.error}")

    print("\n⚡ PERFORMANCE:")
    print(f"  Latency: {result.latency_ms:.2f}ms")
    print(f"  Execution Time: {result.metadata.get('execution_time_ms', 0):.2f}ms")


def demo_short_order():
    """Demo SHORT order execution"""
    print("\n" + "=" * 60)
    print("SHORT ORDER EXECUTION")
    print("=" * 60)

    adapter = MockAdapter()
    asyncio.run(adapter.connect())
    bridge = MT5ExecutionBridge(adapter=adapter)
    tool = GenerateOrder(bridge=bridge)

    result = tool.execute(
        symbol="GBPUSD",
        direction="SHORT",
        size=0.3,
        stop_loss=1.2700,
        take_profit=1.2500,
        confidence=0.75,
        reasoning="Bearish divergence + resistance rejection"
    )

    print("\n📊 ORDER DETAILS:")
    print("  Symbol: GBPUSD")
    print("  Direction: SHORT")
    print("  Size: 0.3 lots")
    print(f"  Confidence: {result.confidence:.2f}")

    if result.value and result.value['success']:
        print("\n✅ EXECUTION SUCCESS:")
        print(f"  Order ID: {result.value['order_id']}")
        print(f"  Fill Price: {result.value['fill_price']:.5f}")
    else:
        print("\n❌ EXECUTION FAILED:")
        print(f"  Error: {result.error}")


def demo_multiple_orders():
    """Demo multiple order executions"""
    print("\n" + "=" * 60)
    print("MULTIPLE ORDER EXECUTIONS")
    print("=" * 60)

    adapter = MockAdapter()
    asyncio.run(adapter.connect())
    bridge = MT5ExecutionBridge(adapter=adapter)
    tool = GenerateOrder(bridge=bridge)

    orders = [
        {"symbol": "EURUSD", "direction": "LONG", "size": 0.1},
        {"symbol": "GBPUSD", "direction": "SHORT", "size": 0.2},
        {"symbol": "USDJPY", "direction": "LONG", "size": 0.15},
    ]

    print(f"\nExecuting {len(orders)} orders...")
    results = []

    for order in orders:
        result = tool.execute(
            symbol=order['symbol'],
            direction=order['direction'],
            size=order['size'],
            confidence=0.8
        )
        results.append(result)

    print("\n📊 RESULTS:")
    for i, (order, result) in enumerate(zip(orders, results, strict=False), 1):
        status = "✅" if result.value and result.value['success'] else "❌"
        order_id = result.value.get('order_id', 'N/A') if result.value else 'N/A'
        print(f"  {i}. {status} {order['symbol']} {order['direction']} {order['size']} lots - Order ID: {order_id}")

    success_count = sum(1 for r in results if r.value and r.value['success'])
    print("\n📈 SUMMARY:")
    print(f"  Total Orders: {len(orders)}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {len(orders) - success_count}")
    print(f"  Success Rate: {success_count / len(orders) * 100:.1f}%")


def demo_validation_errors():
    """Demo validation errors"""
    print("\n" + "=" * 60)
    print("VALIDATION ERRORS")
    print("=" * 60)

    adapter = MockAdapter()
    asyncio.run(adapter.connect())
    bridge = MT5ExecutionBridge(adapter=adapter)
    tool = GenerateOrder(bridge=bridge)

    # Test invalid direction
    print("\n1️⃣ Invalid Direction:")
    result = tool.execute(
        symbol="EURUSD",
        direction="BUY",  # Should be LONG or SHORT
        size=0.1
    )
    print(f"  Error: {result.error}")

    # Test invalid size
    print("\n2️⃣ Invalid Size:")
    result = tool.execute(
        symbol="EURUSD",
        direction="LONG",
        size=-0.1  # Negative
    )
    print(f"  Error: {result.error}")

    # Test invalid confidence
    print("\n3️⃣ Invalid Confidence:")
    result = tool.execute(
        symbol="EURUSD",
        direction="LONG",
        size=0.1,
        confidence=1.5  # Out of range
    )
    print(f"  Error: {result.error}")

    # Test empty symbol
    print("\n4️⃣ Empty Symbol:")
    result = tool.execute(
        symbol="",
        direction="LONG",
        size=0.1
    )
    print(f"  Error: {result.error}")


def demo_schema():
    """Demo JSON schema for LLM function calling"""
    print("\n" + "=" * 60)
    print("JSON SCHEMA FOR LLM FUNCTION CALLING")
    print("=" * 60)

    adapter = MockAdapter()
    asyncio.run(adapter.connect())
    bridge = MT5ExecutionBridge(adapter=adapter)
    tool = GenerateOrder(bridge=bridge)

    schema = tool.get_schema()

    print("\n📋 SCHEMA:")
    print(f"  Name: {schema['name']}")
    print(f"  Description: {schema['description']}")

    print("\n📝 REQUIRED PARAMETERS:")
    for param in schema['parameters']['required']:
        print(f"  - {param}")

    print("\n📝 OPTIONAL PARAMETERS:")
    all_params = set(schema['parameters']['properties'].keys())
    required_params = set(schema['parameters']['required'])
    optional_params = all_params - required_params
    for param in optional_params:
        print(f"  - {param}")

    print("\n📝 DIRECTION ENUM:")
    direction_enum = schema['parameters']['properties']['direction']['enum']
    print(f"  {direction_enum}")


def main():
    """Run all demos"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "GENERATEORDER EXECUTION TOOL DEMO" + " " * 15 + "║")
    print("╚" + "=" * 58 + "╝")

    demo_long_order()
    demo_short_order()
    demo_multiple_orders()
    demo_validation_errors()
    demo_schema()

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\n✅ GenerateOrder Execution Tool:")
    print("  - LONG/SHORT order execution: ✅")
    print("  - Pre-trade validation: ✅")
    print("  - MT5 Bridge integration: ✅")
    print("  - Error handling: ✅")
    print("  - LLM function calling schema: ✅")
    print()


if __name__ == '__main__':
    main()
