"""
Mock Execution Adapter
For testing and development without real broker connection
"""

import asyncio
import random
from typing import Dict, Tuple, Optional, List
from datetime import datetime

from .adapter_base import (
    BaseExecutionAdapter,
    SymbolInfo,
    OrderRequest,
    OrderResult,
    AccountInfo,
    PositionInfo,
    ErrorCode
)


class MockAdapter(BaseExecutionAdapter):
    """
    Mock adapter for testing without real broker connection.
    
    Simulates order execution with configurable:
    - Success/failure rates
    - Latency
    - Slippage
    - Error scenarios
    """
    
    def __init__(
        self,
        success_rate: float = 0.95,
        latency_ms: float = 50.0,
        slippage_pips: float = 1.0,
        initial_balance: float = 10000.0
    ):
        """
        Initialize mock adapter.
        
        Args:
            success_rate: Probability of successful order (0.0-1.0)
            latency_ms: Simulated execution latency in milliseconds
            slippage_pips: Average slippage in pips
            initial_balance: Starting account balance
        """
        self._connected = False
        self._success_rate = success_rate
        self._latency_ms = latency_ms
        self._slippage_pips = slippage_pips
        self._next_order_id = 1000000
        
        # Account state
        self._balance = initial_balance
        self._equity = initial_balance
        self._margin = 0.0
        self._positions: Dict[int, PositionInfo] = {}
        
        # Market prices (mock)
        self._prices = {
            'EURUSD': (1.08490, 1.08500),
            'GBPUSD': (1.26480, 1.26490),
            'USDJPY': (149.990, 150.000),
            'AUDUSD': (0.65480, 0.65490),
        }
        
        # Symbol info (mock)
        self._symbols = {
            'EURUSD': SymbolInfo(
                symbol='EURUSD',
                digits=5,
                point=0.00001,
                min_volume=0.01,
                max_volume=100.0,
                volume_step=0.01,
                min_stop_distance=10,
                trade_mode='FULL'
            ),
            'GBPUSD': SymbolInfo(
                symbol='GBPUSD',
                digits=5,
                point=0.00001,
                min_volume=0.01,
                max_volume=100.0,
                volume_step=0.01,
                min_stop_distance=10,
                trade_mode='FULL'
            ),
            'USDJPY': SymbolInfo(
                symbol='USDJPY',
                digits=3,
                point=0.001,
                min_volume=0.01,
                max_volume=100.0,
                volume_step=0.01,
                min_stop_distance=10,
                trade_mode='FULL'
            ),
        }
    
    async def connect(self) -> bool:
        """Simulate connection"""
        await asyncio.sleep(0.01)  # Simulate network latency
        self._connected = True
        return True
    
    async def disconnect(self) -> None:
        """Simulate disconnection"""
        self._connected = False
    
    def is_connected(self) -> bool:
        """Check connection status"""
        return self._connected
    
    async def symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """Get mock symbol info"""
        if not self._connected:
            return None
        
        await asyncio.sleep(0.001)  # Simulate latency
        return self._symbols.get(symbol)
    
    async def current_price(self, symbol: str) -> Optional[Tuple[float, float]]:
        """Get mock current prices"""
        if not self._connected:
            return None
        
        await asyncio.sleep(0.001)
        
        # Simulate price movement
        if symbol in self._prices:
            bid, ask = self._prices[symbol]
            # Add small random fluctuation
            spread = ask - bid
            movement = random.uniform(-0.0001, 0.0001)
            bid += movement
            ask = bid + spread
            self._prices[symbol] = (bid, ask)
            return (bid, ask)
        
        return None
    
    async def place_order(self, request: OrderRequest) -> OrderResult:
        """
        Simulate order execution.
        
        Randomly succeeds/fails based on success_rate.
        Applies simulated latency and slippage.
        """
        if not self._connected:
            return OrderResult(
                success=False,
                error_code=ErrorCode.NOT_CONNECTED,
                error_message="Not connected to execution provider"
            )
        
        # Simulate latency
        latency_variation = random.uniform(0.8, 1.2)
        actual_latency = self._latency_ms * latency_variation / 1000.0
        await asyncio.sleep(actual_latency)
        
        # Check if order succeeds
        if random.random() > self._success_rate:
            # Simulate failure
            error_scenarios = [
                (ErrorCode.SPREAD_TOO_WIDE, "Spread exceeds maximum"),
                (ErrorCode.MARGIN_INSUFFICIENT, "Insufficient margin"),
                (ErrorCode.ORDER_REJECTED, "Order rejected by server"),
                (ErrorCode.REQUOTE, "Price changed, requote needed"),
            ]
            error_code, error_message = random.choice(error_scenarios)
            
            return OrderResult(
                success=False,
                error_code=error_code,
                error_message=error_message
            )
        
        # Success - simulate execution
        symbol_info = await self.symbol_info(request.symbol)
        if symbol_info is None:
            return OrderResult(
                success=False,
                error_code=ErrorCode.SYMBOL_NOT_FOUND,
                error_message=f"Symbol {request.symbol} not found"
            )
        
        prices = await self.current_price(request.symbol)
        if prices is None:
            return OrderResult(
                success=False,
                error_code=ErrorCode.NO_FILL,
                error_message="Unable to get current price"
            )
        
        bid, ask = prices
        
        # Determine fill price with slippage
        if request.direction == 'LONG':
            base_price = ask
            slippage = random.gauss(self._slippage_pips, self._slippage_pips * 0.3) * symbol_info.point * 10
            fill_price = base_price + abs(slippage)  # Slippage against us
        else:
            base_price = bid
            slippage = random.gauss(self._slippage_pips, self._slippage_pips * 0.3) * symbol_info.point * 10
            fill_price = base_price - abs(slippage)  # Slippage against us
        
        # Generate order ID
        order_id = self._next_order_id
        self._next_order_id += 1
        
        # Create position
        position = PositionInfo(
            ticket=order_id,
            symbol=request.symbol,
            direction=request.direction,
            volume=request.size,
            price_open=fill_price,
            price_current=fill_price,
            profit=0.0,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            open_time=datetime.now()
        )
        self._positions[order_id] = position
        
        # Update account (simple margin calculation)
        margin_per_lot = 1000.0  # Simplified
        self._margin += request.size * margin_per_lot
        
        return OrderResult(
            success=True,
            order_id=order_id,
            fill_price=fill_price,
            fill_volume=request.size,
            error_code=ErrorCode.SUCCESS
        )
    
    async def order_fill_price(self, order_id: int) -> Optional[float]:
        """Get fill price for order"""
        if not self._connected:
            return None
        
        position = self._positions.get(order_id)
        if position:
            return position.price_open
        
        return None
    
    async def account_info(self) -> Optional[AccountInfo]:
        """Get mock account info"""
        if not self._connected:
            return None
        
        # Calculate equity (simplified - just balance + unrealized P&L)
        unrealized_pnl = sum(pos.profit for pos in self._positions.values())
        self._equity = self._balance + unrealized_pnl
        
        free_margin = self._balance - self._margin
        margin_level = (self._equity / self._margin * 100) if self._margin > 0 else 0.0
        
        return AccountInfo(
            account_id="MOCK_12345678",
            balance=self._balance,
            equity=self._equity,
            margin=self._margin,
            free_margin=free_margin,
            margin_level=margin_level,
            leverage=100
        )
    
    async def open_positions(self, symbol: Optional[str] = None) -> List[PositionInfo]:
        """Get open positions"""
        if not self._connected:
            return []
        
        positions = list(self._positions.values())
        
        if symbol:
            positions = [p for p in positions if p.symbol == symbol]
        
        # Update current prices and P&L
        for pos in positions:
            prices = await self.current_price(pos.symbol)
            if prices:
                bid, ask = prices
                pos.price_current = bid if pos.direction == 'LONG' else ask
                
                # Simple P&L calculation (10 USD per pip for standard lot)
                symbol_info = await self.symbol_info(pos.symbol)
                if symbol_info:
                    pip_size = symbol_info.point * 10
                    pip_value = 10.0  # USD per pip for standard lot
                    
                    if pos.direction == 'LONG':
                        pips = (pos.price_current - pos.price_open) / pip_size
                    else:
                        pips = (pos.price_open - pos.price_current) / pip_size
                    
                    pos.profit = pips * pip_value * pos.volume
        
        return positions
    
    async def is_market_open(self, symbol: str) -> bool:
        """Mock market always open"""
        if not self._connected:
            return False
        
        symbol_info = await self.symbol_info(symbol)
        if symbol_info is None:
            return False
        
        return symbol_info.is_tradeable()
    
    def get_name(self) -> str:
        """Get adapter name"""
        return "MockAdapter"
    
    # Configuration methods for testing
    
    def set_success_rate(self, rate: float):
        """Set order success rate (0.0-1.0)"""
        self._success_rate = max(0.0, min(1.0, rate))
    
    def set_latency(self, latency_ms: float):
        """Set simulated latency in milliseconds"""
        self._latency_ms = max(0.0, latency_ms)
    
    def set_slippage(self, slippage_pips: float):
        """Set average slippage in pips"""
        self._slippage_pips = max(0.0, slippage_pips)
    
    def add_symbol(self, symbol_info: SymbolInfo):
        """Add custom symbol for testing"""
        self._symbols[symbol_info.symbol] = symbol_info
        # Set default price
        self._prices[symbol_info.symbol] = (1.0000, 1.0010)
    
    def set_price(self, symbol: str, bid: float, ask: float):
        """Set mock price for symbol"""
        self._prices[symbol] = (bid, ask)
    
    def close_position(self, order_id: int):
        """Close position (for testing)"""
        if order_id in self._positions:
            pos = self._positions[order_id]
            # Update balance with P&L
            self._balance += pos.profit
            # Free margin
            margin_per_lot = 1000.0
            self._margin -= pos.volume * margin_per_lot
            # Remove position
            del self._positions[order_id]
