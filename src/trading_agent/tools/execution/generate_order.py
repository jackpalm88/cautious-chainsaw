"""
GenerateOrder - Execution Tool
Generates and executes trading orders via MT5 Bridge
"""

import time
from typing import Any

from ...adapters.bridge import (
    ExecutionResult,
    MT5ExecutionBridge,
    OrderDirection,
    Signal,
)
from ..base_tool import BaseTool, ToolResult, ToolTier


class GenerateOrder(BaseTool):
    """
    Generate and execute trading order via MT5 Bridge.

    This is an execution-tier tool that:
    - Creates Signal from trading decision
    - Validates signal via MT5 Bridge
    - Executes order via adapter
    - Returns execution result with order ID

    Requires MT5ExecutionBridge with connected adapter.
    """

    name = "generate_order"
    version = "1.0.0"
    tier = ToolTier.EXECUTION
    description = "Generate and execute trading order with pre-trade validation"

    def __init__(self, bridge: MT5ExecutionBridge | None = None):
        """
        Initialize order generator.

        Args:
            bridge: MT5ExecutionBridge instance with connected adapter
                   If None, tool will return error (requires bridge)
        """
        self.bridge = bridge

    def execute(
        self,
        symbol: str,
        direction: str,
        size: float,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        confidence: float = 0.0,
        reasoning: str = "",
        **kwargs
    ) -> ToolResult:
        """
        Execute trading order.

        Args:
            symbol: Trading symbol (e.g., "EURUSD")
            direction: Order direction ("LONG" or "SHORT")
            size: Position size in lots
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
            confidence: Signal confidence (0.0 to 1.0)
            reasoning: Trading reasoning/rationale
            **kwargs: Additional parameters

        Returns:
            ToolResult with execution result
        """
        start_time = time.perf_counter()

        try:
            # Validate inputs
            self.validate_inputs(
                symbol=symbol,
                direction=direction,
                size=size,
                confidence=confidence
            )

            # Check bridge availability
            if self.bridge is None:
                raise ValueError("MT5ExecutionBridge not initialized")

            if not self.bridge.adapter.is_connected():
                raise ValueError("Adapter not connected")

            # Parse direction
            try:
                order_direction = OrderDirection[direction.upper()]
            except KeyError as e:
                raise ValueError(f"Invalid direction: {direction}. Must be 'LONG' or 'SHORT'") from e

            # Create signal
            signal = Signal(
                symbol=symbol,
                direction=order_direction,
                size=size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=confidence,
                reasoning=reasoning,
                metadata={
                    'tool': self.name,
                    'version': self.version,
                }
            )

            # Execute via bridge (synchronous wrapper for async)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            execution_result = loop.run_until_complete(
                self._execute_signal(signal)
            )

            # Calculate latency
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Build result
            if execution_result.success:
                return ToolResult(
                    value={
                        'success': True,
                        'order_id': execution_result.order_id,
                        'fill_price': execution_result.fill_price,
                        'fill_volume': execution_result.fill_volume,
                        'slippage_pips': execution_result.slippage_pips,
                        'status': execution_result.status.value,
                    },
                    confidence=confidence,  # Use signal confidence
                    latency_ms=round(latency_ms, 2),
                    metadata={
                        'signal_id': execution_result.signal_id,
                        'execution_time_ms': execution_result.execution_time_ms,
                        'symbol': symbol,
                        'direction': direction,
                        'size': size,
                    }
                )
            else:
                # Execution failed
                return ToolResult(
                    value={
                        'success': False,
                        'status': execution_result.status.value,
                        'error_code': execution_result.error_code.value if execution_result.error_code else None,
                        'error_message': execution_result.error_message,
                    },
                    confidence=0.0,  # Failed execution = 0 confidence
                    latency_ms=round(latency_ms, 2),
                    error=execution_result.error_message
                )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                value=None,
                confidence=0.0,
                latency_ms=round(latency_ms, 2),
                error=str(e)
            )

    async def _execute_signal(self, signal: Signal) -> ExecutionResult:
        """
        Execute signal via bridge (async).

        Args:
            signal: Trading signal

        Returns:
            ExecutionResult
        """
        # Queue signal for execution
        signal_id = self.bridge.receive_signal(signal)

        # Execute order via bridge
        result = await self.bridge.execute_order(signal_id, signal)

        return result

    def validate_inputs(
        self,
        symbol: str,
        direction: str,
        size: float,
        confidence: float
    ) -> None:
        """Validate input parameters"""
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")

        if direction.upper() not in ['LONG', 'SHORT']:
            raise ValueError("Direction must be 'LONG' or 'SHORT'")

        if size <= 0:
            raise ValueError("Size must be positive")

        if not 0.0 <= confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

    def get_schema(self) -> dict[str, Any]:
        """Get JSON-Schema for LLM function calling"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Trading symbol (e.g., 'EURUSD', 'BTCUSD')",
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["LONG", "SHORT"],
                        "description": "Order direction: 'LONG' for buy, 'SHORT' for sell",
                    },
                    "size": {
                        "type": "number",
                        "description": "Position size in lots",
                    },
                    "stop_loss": {
                        "type": "number",
                        "description": "Stop loss price (optional)",
                    },
                    "take_profit": {
                        "type": "number",
                        "description": "Take profit price (optional)",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Signal confidence (0.0 to 1.0)",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Trading reasoning/rationale",
                    },
                },
                "required": ["symbol", "direction", "size"],
            },
        }
