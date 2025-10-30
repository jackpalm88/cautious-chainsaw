"""
MT5 Execution Bridge - Hybrid Version with Adapter Pattern
Accepts any execution adapter (MT5, IBKR, Mock, etc.)
"""

import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from .adapter_base import (
    BaseExecutionAdapter,
    OrderRequest,
    OrderResult,
    ErrorCode
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OrderDirection(Enum):
    """Order direction types"""
    LONG = "LONG"
    SHORT = "SHORT"


class ExecutionStatus(Enum):
    """Execution result status"""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"


@dataclass
class Signal:
    """Trading signal from AI agent"""
    symbol: str
    direction: OrderDirection
    size: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float = 0.0
    reasoning: str = ""
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if 'generated_at' not in self.metadata:
            self.metadata['generated_at'] = datetime.now().isoformat()


@dataclass
class ExecutionResult:
    """Result of order execution"""
    success: bool
    signal_id: str
    status: ExecutionStatus
    order_id: Optional[int] = None
    fill_price: Optional[float] = None
    fill_volume: Optional[float] = None
    execution_time_ms: Optional[float] = None
    slippage_pips: Optional[float] = None
    error_code: Optional[ErrorCode] = None
    error_message: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        result = asdict(self)
        result['status'] = self.status.value
        if self.error_code:
            result['error_code'] = self.error_code.value
        return result


class MT5ExecutionBridge:
    """
    Hybrid execution bridge accepting any execution adapter.
    
    Provides:
    - 3-layer architecture (Reception â†’ Execution â†’ Confirmation)
    - Comprehensive validation
    - Statistics tracking
    - Callback system
    - Error handling
    
    Works with any adapter: MockAdapter, RealMT5Adapter, or custom adapters.
    """
    
    def __init__(
        self,
        adapter: BaseExecutionAdapter,
        max_spread_points: int = 30,
        deviation: int = 10,
        magic: int = 123456
    ):
        """
        Initialize bridge with execution adapter.
        
        Args:
            adapter: Execution adapter (MockAdapter, RealMT5Adapter, etc.)
            max_spread_points: Maximum allowed spread in points
            deviation: Maximum slippage in points
            magic: Magic number for order identification
        """
        self.adapter = adapter
        self.max_spread_points = max_spread_points
        self.deviation = deviation
        self.magic = magic
        
        self.order_queue = asyncio.Queue()
        self.confirmation_callbacks: List[Callable] = []
        self.execution_history: List[ExecutionResult] = []
        
        logger.info(f"Initialized bridge with {adapter.get_name()}")
    
    # ========== LAYER 1: SIGNAL RECEPTION & VALIDATION ==========
    
    async def validate_signal(self, signal: Signal) -> tuple[bool, str]:
        """
        Validate signal before execution.
        
        Performs 3-stage validation:
        1. Input validation (basic checks)
        2. Symbol validation (exists, tradeable)
        3. Market validation (open, prices available)
        
        Returns:
            (is_valid, error_message)
        """
        # Stage 1: Input validation
        if not 0.0 <= signal.confidence <= 1.0:
            return False, f"Confidence {signal.confidence} out of range [0, 1]"
        
        if signal.size <= 0:
            return False, f"Invalid position size: {signal.size}"
        
        # Stage 2: Symbol validation
        if not self.adapter.is_connected():
            return False, "Adapter not connected"
        
        symbol_info = await self.adapter.symbol_info(signal.symbol)
        if symbol_info is None:
            return False, f"Symbol {signal.symbol} not found"
        
        if not symbol_info.is_tradeable():
            return False, f"Symbol {signal.symbol} not tradeable (mode: {symbol_info.trade_mode})"
        
        # Check size limits
        if signal.size < symbol_info.min_volume:
            return False, f"Size {signal.size} below minimum {symbol_info.min_volume}"
        
        if signal.size > symbol_info.max_volume:
            return False, f"Size {signal.size} above maximum {symbol_info.max_volume}"
        
        # Stage 3: Market validation
        if not await self.adapter.is_market_open(signal.symbol):
            return False, f"Market closed for {signal.symbol}"
        
        prices = await self.adapter.current_price(signal.symbol)
        if prices is None:
            return False, "Unable to get current price"
        
        bid, ask = prices
        spread_points = (ask - bid) / symbol_info.point
        
        if spread_points > self.max_spread_points:
            return False, f"Spread {spread_points:.1f} points exceeds maximum {self.max_spread_points}"
        
        # Validate SL/TP distance
        current_price = ask if signal.direction == OrderDirection.LONG else bid
        
        if signal.stop_loss is not None:
            sl_distance_points = abs(current_price - signal.stop_loss) / symbol_info.point
            if sl_distance_points < symbol_info.min_stop_distance:
                return False, f"Stop loss too close: {sl_distance_points:.1f} < {symbol_info.min_stop_distance} points"
        
        if signal.take_profit is not None:
            tp_distance_points = abs(current_price - signal.take_profit) / symbol_info.point
            if tp_distance_points < symbol_info.min_stop_distance:
                return False, f"Take profit too close: {tp_distance_points:.1f} < {symbol_info.min_stop_distance} points"
        
        return True, "Signal valid"
    
    def receive_signal(self, signal: Signal) -> str:
        """
        Receive and queue signal for execution.
        
        Args:
            signal: Trading signal
            
        Returns:
            signal_id for tracking
            
        Raises:
            ValueError: If signal validation fails
        """
        # Generate signal ID
        signal_id = f"{signal.symbol}_{int(time.time() * 1000)}"
        
        # Queue signal (validation happens during execution)
        self.order_queue.put_nowait({
            'signal_id': signal_id,
            'signal': signal,
            'received_at': datetime.now()
        })
        
        logger.info(f"Signal {signal_id} queued: {signal.direction.value} {signal.size} {signal.symbol}")
        
        return signal_id
    
    # ========== LAYER 2: ORDER EXECUTION ==========
    
    async def execute_order(self, signal_id: str, signal: Signal) -> ExecutionResult:
        """
        Execute order via adapter.
        
        Args:
            signal_id: Unique signal identifier
            signal: Trading signal
            
        Returns:
            ExecutionResult with fill details or error
        """
        start_time = time.time()
        
        try:
            # Pre-execution validation
            valid, error_msg = await self.validate_signal(signal)
            if not valid:
                return ExecutionResult(
                    success=False,
                    signal_id=signal_id,
                    status=ExecutionStatus.FAILED,
                    error_code=ErrorCode.INPUT_INVALID,
                    error_message=error_msg,
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Get symbol info for slippage calculation
            symbol_info = await self.adapter.symbol_info(signal.symbol)
            if symbol_info is None:
                return ExecutionResult(
                    success=False,
                    signal_id=signal_id,
                    status=ExecutionStatus.FAILED,
                    error_code=ErrorCode.SYMBOL_NOT_FOUND,
                    error_message=f"Symbol {signal.symbol} not found",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Get price before execution for slippage calculation
            prices_before = await self.adapter.current_price(signal.symbol)
            if prices_before is None:
                return ExecutionResult(
                    success=False,
                    signal_id=signal_id,
                    status=ExecutionStatus.FAILED,
                    error_code=ErrorCode.NO_FILL,
                    error_message="Failed to get price",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            bid_before, ask_before = prices_before
            requested_price = ask_before if signal.direction == OrderDirection.LONG else bid_before
            
            # Build order request
            request = OrderRequest(
                symbol=signal.symbol,
                direction=signal.direction.value,
                size=signal.size,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                deviation=self.deviation,
                comment=f"AI_{signal.confidence:.2f}",
                magic=self.magic
            )
            
            # Execute via adapter
            logger.info(f"Executing {signal_id} via {self.adapter.get_name()}")
            order_result = await self.adapter.place_order(request)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Build execution result
            if order_result.success:
                # Calculate slippage
                slippage_pips = None
                if order_result.fill_price:
                    pip_size = symbol_info.point * (10 if symbol_info.digits in [3, 5] else 1)
                    slippage = abs(order_result.fill_price - requested_price)
                    slippage_pips = slippage / pip_size
                
                exec_result = ExecutionResult(
                    success=True,
                    signal_id=signal_id,
                    status=ExecutionStatus.SUCCESS,
                    order_id=order_result.order_id,
                    fill_price=order_result.fill_price,
                    fill_volume=order_result.fill_volume,
                    execution_time_ms=execution_time_ms,
                    slippage_pips=slippage_pips,
                    error_code=ErrorCode.SUCCESS
                )
                
                logger.info(f"Signal {signal_id} executed: Order={order_result.order_id}, "
                          f"Fill={order_result.fill_price}, Slippage={slippage_pips:.2f if slippage_pips else 0} pips")
            else:
                exec_result = ExecutionResult(
                    success=False,
                    signal_id=signal_id,
                    status=ExecutionStatus.FAILED,
                    execution_time_ms=execution_time_ms,
                    error_code=order_result.error_code,
                    error_message=order_result.error_message
                )
                
                logger.warning(f"Signal {signal_id} failed: {order_result.error_message}")
            
            # Store in history
            self.execution_history.append(exec_result)
            
            # Trigger callbacks
            for callback in self.confirmation_callbacks:
                try:
                    callback(exec_result)
                except Exception as e:
                    logger.error(f"Callback error: {str(e)}")
            
            return exec_result
            
        except Exception as e:
            logger.error(f"Execution exception for {signal_id}: {str(e)}")
            return ExecutionResult(
                success=False,
                signal_id=signal_id,
                status=ExecutionStatus.FAILED,
                execution_time_ms=(time.time() - start_time) * 1000,
                error_code=ErrorCode.UNHANDLED,
                error_message=str(e)
            )
    
    # ========== LAYER 3: CONFIRMATION & FEEDBACK ==========
    
    def register_confirmation_callback(self, callback: Callable):
        """Register callback for execution confirmations"""
        self.confirmation_callbacks.append(callback)
        logger.info(f"Registered callback: {callback.__name__}")
    
    def get_execution_history(self, limit: int = 100) -> List[ExecutionResult]:
        """Get recent execution history"""
        return self.execution_history[-limit:]
    
    def get_execution_statistics(self) -> Dict:
        """Get execution performance statistics"""
        if not self.execution_history:
            return {
                'total_executions': 0,
                'success_rate': 0.0,
                'avg_execution_time_ms': 0.0,
                'avg_slippage_pips': 0.0
            }
        
        successful = [e for e in self.execution_history if e.success]
        failed = [e for e in self.execution_history if not e.success]
        
        exec_times = [e.execution_time_ms for e in self.execution_history if e.execution_time_ms]
        avg_time = sum(exec_times) / len(exec_times) if exec_times else 0.0
        
        slippages = [e.slippage_pips for e in successful if e.slippage_pips is not None]
        avg_slippage = sum(slippages) / len(slippages) if slippages else 0.0
        
        return {
            'adapter': self.adapter.get_name(),
            'total_executions': len(self.execution_history),
            'successful_executions': len(successful),
            'failed_executions': len(failed),
            'success_rate': len(successful) / len(self.execution_history) * 100,
            'avg_execution_time_ms': avg_time,
            'avg_slippage_pips': avg_slippage,
            'p95_execution_time_ms': self._percentile(exec_times, 95) if exec_times else 0.0
        }
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    # ========== HELPER METHODS ==========
    
    async def get_account_info(self):
        """Get current account information"""
        return await self.adapter.account_info()
    
    async def get_open_positions(self, symbol: Optional[str] = None):
        """Get open positions"""
        positions = await self.adapter.open_positions(symbol)
        
        # Convert to dict format for compatibility
        return [
            {
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': pos.direction,
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'profit': pos.profit,
                'sl': pos.stop_loss,
                'tp': pos.take_profit,
                'time': pos.open_time
            }
            for pos in positions
        ]


# ========== ASYNC EXECUTION ENGINE ==========

class AsyncExecutionEngine:
    """Async engine for background queue processing"""
    
    def __init__(self, bridge: MT5ExecutionBridge):
        self.bridge = bridge
        self.is_running = False
        self._task = None
    
    async def start(self):
        """Start processing order queue"""
        if self.is_running:
            logger.warning("Execution engine already running")
            return
        
        self.is_running = True
        logger.info("Starting async execution engine")
        self._task = asyncio.create_task(self._process_queue())
    
    async def stop(self):
        """Stop processing"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped async execution engine")
    
    async def _process_queue(self):
        """Process orders from queue"""
        while self.is_running:
            try:
                # Get next order (wait max 1 second)
                try:
                    order_data = await asyncio.wait_for(
                        self.bridge.order_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                signal_id = order_data['signal_id']
                signal = order_data['signal']
                
                logger.info(f"Processing signal {signal_id} from queue")
                
                # Execute
                result = await self.bridge.execute_order(signal_id, signal)
                
                # Log result
                if result.success:
                    logger.info(f"Signal {signal_id} executed successfully")
                else:
                    logger.warning(f"Signal {signal_id} execution failed: {result.error_message}")
                
            except Exception as e:
                logger.error(f"Queue processing error: {str(e)}")
                await asyncio.sleep(1)
