"""
Real MT5 Execution Adapter
Production adapter using MetaTrader5 Python package
"""

import MetaTrader5 as mt5
import asyncio
from typing import Dict, Tuple, Optional, List
from datetime import datetime
import logging

from .adapter_base import (
    BaseExecutionAdapter,
    SymbolInfo,
    OrderRequest,
    OrderResult,
    AccountInfo,
    PositionInfo,
    ErrorCode,
    map_mt5_error
)

logger = logging.getLogger(__name__)


class RealMT5Adapter(BaseExecutionAdapter):
    """
    Real MT5 adapter using MetaTrader5 Python package.
    
    Wraps MT5 API with unified interface for the bridge.
    Provides comprehensive error handling and validation.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize MT5 adapter.
        
        Args:
            config: Dictionary with MT5 credentials:
                {
                    'login': int,
                    'password': str,
                    'server': str,
                    'timeout': int (optional),
                    'path': str (optional, MT5 terminal path)
                }
        """
        self.config = config
        self._connected = False
    
    async def connect(self) -> bool:
        """Establish MT5 connection"""
        try:
            # Initialize MT5
            terminal_path = self.config.get('path')
            if terminal_path:
                if not mt5.initialize(path=terminal_path):
                    logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                    return False
            else:
                if not mt5.initialize():
                    logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                    return False
            
            # Login to account
            authorized = mt5.login(
                login=self.config['login'],
                password=self.config['password'],
                server=self.config['server'],
                timeout=self.config.get('timeout', 60000)
            )
            
            if not authorized:
                logger.error(f"MT5 login failed: {mt5.last_error()}")
                mt5.shutdown()
                return False
            
            # Verify account info
            account = mt5.account_info()
            if account is None:
                logger.error("Failed to get account info")
                mt5.shutdown()
                return False
            
            self._connected = True
            logger.info(f"Connected to MT5: Account {account.login} on {account.server}")
            logger.info(f"Balance: ${account.balance:.2f}, Equity: ${account.equity:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"MT5 connection error: {str(e)}")
            return False
    
    async def disconnect(self) -> None:
        """Close MT5 connection"""
        if self._connected:
            mt5.shutdown()
            self._connected = False
            logger.info("Disconnected from MT5")
    
    def is_connected(self) -> bool:
        """Check connection status"""
        return self._connected and mt5.terminal_info() is not None
    
    async def symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """Get symbol information from MT5"""
        if not self._connected:
            return None
        
        info = mt5.symbol_info(symbol)
        if info is None:
            return None
        
        # Ensure symbol is visible
        if not info.visible:
            if not mt5.symbol_select(symbol, True):
                logger.warning(f"Failed to enable symbol {symbol}")
                return None
        
        return SymbolInfo(
            symbol=symbol,
            digits=info.digits,
            point=info.point,
            min_volume=info.volume_min,
            max_volume=info.volume_max,
            volume_step=info.volume_step,
            min_stop_distance=info.trade_stops_level,
            trade_mode='FULL' if info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL else 'DISABLED'
        )
    
    async def current_price(self, symbol: str) -> Optional[Tuple[float, float]]:
        """Get current bid/ask prices"""
        if not self._connected:
            return None
        
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        
        return (tick.bid, tick.ask)
    
    async def place_order(self, request: OrderRequest) -> OrderResult:
        """
        Place order with MT5.
        
        Handles all MT5-specific order placement logic and error handling.
        """
        if not self._connected:
            return OrderResult(
                success=False,
                error_code=ErrorCode.NOT_CONNECTED,
                error_message="Not connected to MT5"
            )
        
        try:
            # Get symbol info
            symbol_info = await self.symbol_info(request.symbol)
            if symbol_info is None:
                return OrderResult(
                    success=False,
                    error_code=ErrorCode.SYMBOL_NOT_FOUND,
                    error_message=f"Symbol {request.symbol} not found"
                )
            
            # Get current price
            tick = mt5.symbol_info_tick(request.symbol)
            if tick is None:
                return OrderResult(
                    success=False,
                    error_code=ErrorCode.NO_FILL,
                    error_message="Failed to get current price"
                )
            
            # Determine order type and price
            if request.direction == 'LONG':
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            else:
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            
            # Build MT5 order request
            mt5_request = {
                'action': mt5.TRADE_ACTION_DEAL,
                'symbol': request.symbol,
                'volume': request.size,
                'type': order_type,
                'price': price,
                'deviation': request.deviation,
                'magic': request.magic,
                'comment': request.comment[:31] if request.comment else "",  # MT5 limits to 31 chars
                'type_time': mt5.ORDER_TIME_GTC,
                'type_filling': mt5.ORDER_FILLING_IOC,
            }
            
            # Add SL/TP if provided
            if request.stop_loss is not None:
                mt5_request['sl'] = request.stop_loss
            
            if request.take_profit is not None:
                mt5_request['tp'] = request.take_profit
            
            # Send order
            logger.debug(f"Sending MT5 order: {mt5_request}")
            result = mt5.order_send(mt5_request)
            
            if result is None:
                return OrderResult(
                    success=False,
                    error_code=ErrorCode.UNHANDLED,
                    error_message="order_send returned None"
                )
            
            # Check result
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_code = map_mt5_error(result.retcode)
                error_message = self._get_mt5_error_message(result.retcode)
                
                logger.warning(f"MT5 order failed: {error_message} (code: {result.retcode})")
                
                return OrderResult(
                    success=False,
                    error_code=error_code,
                    error_message=error_message
                )
            
            # Success
            logger.info(f"MT5 order executed: ID={result.order}, Fill={result.price}, Volume={result.volume}")
            
            return OrderResult(
                success=True,
                order_id=result.order,
                fill_price=result.price,
                fill_volume=result.volume,
                error_code=ErrorCode.SUCCESS
            )
            
        except Exception as e:
            logger.error(f"MT5 order exception: {str(e)}")
            return OrderResult(
                success=False,
                error_code=ErrorCode.UNHANDLED,
                error_message=str(e)
            )
    
    async def order_fill_price(self, order_id: int) -> Optional[float]:
        """Get fill price for order"""
        if not self._connected:
            return None
        
        # Try to find in history
        from_date = datetime(2020, 1, 1)  # Look back far enough
        to_date = datetime.now()
        
        deals = mt5.history_deals_get(from_date, to_date)
        if deals is None:
            return None
        
        for deal in deals:
            if deal.order == order_id:
                return deal.price
        
        return None
    
    async def account_info(self) -> Optional[AccountInfo]:
        """Get MT5 account information"""
        if not self._connected:
            return None
        
        account = mt5.account_info()
        if account is None:
            return None
        
        return AccountInfo(
            account_id=str(account.login),
            balance=account.balance,
            equity=account.equity,
            margin=account.margin,
            free_margin=account.margin_free,
            margin_level=account.margin_level,
            leverage=account.leverage
        )
    
    async def open_positions(self, symbol: Optional[str] = None) -> List[PositionInfo]:
        """Get open positions from MT5"""
        if not self._connected:
            return []
        
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
        
        if positions is None:
            return []
        
        return [
            PositionInfo(
                ticket=pos.ticket,
                symbol=pos.symbol,
                direction='LONG' if pos.type == mt5.ORDER_TYPE_BUY else 'SHORT',
                volume=pos.volume,
                price_open=pos.price_open,
                price_current=pos.price_current,
                profit=pos.profit,
                stop_loss=pos.sl if pos.sl != 0.0 else None,
                take_profit=pos.tp if pos.tp != 0.0 else None,
                open_time=datetime.fromtimestamp(pos.time)
            )
            for pos in positions
        ]
    
    async def is_market_open(self, symbol: str) -> bool:
        """Check if market is open for symbol"""
        if not self._connected:
            return False
        
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return False
        
        # Check trade mode
        if symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
            return False
        
        # Additional check: try to get tick
        tick = mt5.symbol_info_tick(symbol)
        return tick is not None
    
    def get_name(self) -> str:
        """Get adapter name"""
        return "RealMT5Adapter"
    
    def supports_feature(self, feature: str) -> bool:
        """Check if MT5 supports feature"""
        supported_features = {
            'market_orders': True,
            'limit_orders': True,
            'stop_orders': True,
            'trailing_stops': True,
            'modify_position': True,
            'partial_close': True,
        }
        return supported_features.get(feature, False)
    
    # MT5-specific helper methods
    
    def _get_mt5_error_message(self, retcode: int) -> str:
        """Translate MT5 error code to human-readable message"""
        error_map = {
            10004: 'Requote - price changed',
            10006: 'Request rejected by server',
            10007: 'Request canceled by trader',
            10008: 'Order placed successfully',
            10009: 'Request completed',
            10010: 'Only part of request completed',
            10011: 'Request processing error',
            10012: 'Request canceled by timeout',
            10013: 'Invalid request',
            10014: 'Invalid volume in request',
            10015: 'Invalid price in request',
            10016: 'Invalid stop loss/take profit',
            10017: 'Trading disabled',
            10018: 'Market closed',
            10019: 'Insufficient funds',
            10020: 'Price changed',
            10021: 'No quotes to process request',
            10022: 'Invalid order expiration',
            10023: 'Order state changed',
            10024: 'Too many requests',
            10025: 'No changes in request',
            10026: 'Autotrading disabled by server',
            10027: 'Autotrading disabled by client',
            10028: 'Request locked for processing',
            10029: 'Order/position frozen',
            10030: 'Invalid fill type',
            10031: 'No connection',
            10032: 'Operation allowed only for live accounts',
            10033: 'Pending orders limit reached',
            10034: 'Order/position volume limit reached',
            10035: 'Invalid order type',
            10036: 'Position already closed'
        }
        
        return error_map.get(retcode, f'Unknown MT5 error code: {retcode}')
