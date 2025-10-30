"""
Base Execution Adapter Interface
Defines contract for all execution providers (MT5, IBKR, Binance, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class ErrorCode(Enum):
    """Unified error codes across all execution providers"""
    
    # Input validation errors
    INPUT_INVALID = "INPUT_INVALID"
    CONFIDENCE_OUT_OF_RANGE = "CONFIDENCE_OUT_OF_RANGE"
    SIZE_INVALID = "SIZE_INVALID"
    SYMBOL_NOT_FOUND = "SYMBOL_NOT_FOUND"
    
    # Pre-flight errors
    SPREAD_TOO_WIDE = "SPREAD_TOO_WIDE"
    MARKET_CLOSED = "MARKET_CLOSED"
    MARGIN_INSUFFICIENT = "MARGIN_INSUFFICIENT"
    STOPLOSS_TOO_CLOSE = "STOPLOSS_TOO_CLOSE"
    TAKEPROFIT_TOO_CLOSE = "TAKEPROFIT_TOO_CLOSE"
    
    # Execution errors
    ORDER_REJECTED = "ORDER_REJECTED"
    NO_FILL = "NO_FILL"
    TIMEOUT = "TIMEOUT"
    REQUOTE = "REQUOTE"
    PARTIAL_FILL = "PARTIAL_FILL"
    
    # Connection errors
    NOT_CONNECTED = "NOT_CONNECTED"
    CONNECTION_LOST = "CONNECTION_LOST"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    
    # Success
    SUCCESS = "SUCCESS"
    
    # Catch-all
    UNHANDLED = "UNHANDLED"


@dataclass
class SymbolInfo:
    """Symbol information from execution provider"""
    symbol: str
    digits: int  # Decimal places
    point: float  # Minimum price change
    min_volume: float  # Minimum lot size
    max_volume: float  # Maximum lot size
    volume_step: float  # Lot size increment
    min_stop_distance: int  # Minimum stop distance in points
    trade_mode: str  # 'FULL', 'DISABLED', 'CLOSEONLY'
    
    def is_tradeable(self) -> bool:
        """Check if symbol is available for trading"""
        return self.trade_mode == 'FULL'


@dataclass
class OrderRequest:
    """Unified order request structure"""
    symbol: str
    direction: str  # 'LONG' or 'SHORT'
    size: float  # Position size in lots
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    deviation: int = 10  # Max slippage in points
    comment: str = ""
    magic: int = 0  # Magic number for order identification


@dataclass
class OrderResult:
    """Result of order execution"""
    success: bool
    order_id: Optional[int] = None
    fill_price: Optional[float] = None
    fill_volume: Optional[float] = None
    error_code: Optional[ErrorCode] = None
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class AccountInfo:
    """Account information from execution provider"""
    account_id: str
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    leverage: int


@dataclass
class PositionInfo:
    """Open position information"""
    ticket: int
    symbol: str
    direction: str  # 'LONG' or 'SHORT'
    volume: float
    price_open: float
    price_current: float
    profit: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    open_time: datetime


class BaseExecutionAdapter(ABC):
    """
    Abstract base class for execution adapters.
    
    All execution providers (MT5, IBKR, Binance, etc.) must implement this interface.
    This allows the bridge to work with any provider without code changes.
    """
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to execution provider.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close connection to execution provider.
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if currently connected to execution provider.
        
        Returns:
            True if connected, False otherwise
        """
        pass
    
    @abstractmethod
    async def symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """
        Get symbol information.
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            
        Returns:
            SymbolInfo if symbol exists, None otherwise
        """
        pass
    
    @abstractmethod
    async def current_price(self, symbol: str) -> Optional[Tuple[float, float]]:
        """
        Get current bid/ask prices for symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Tuple of (bid, ask) prices, or None if not available
        """
        pass
    
    @abstractmethod
    async def place_order(self, request: OrderRequest) -> OrderResult:
        """
        Place order with execution provider.
        
        Args:
            request: OrderRequest with all order parameters
            
        Returns:
            OrderResult with execution details or error
        """
        pass
    
    @abstractmethod
    async def order_fill_price(self, order_id: int) -> Optional[float]:
        """
        Get fill price for executed order.
        
        Args:
            order_id: Order ID from place_order()
            
        Returns:
            Fill price if order executed, None otherwise
        """
        pass
    
    @abstractmethod
    async def account_info(self) -> Optional[AccountInfo]:
        """
        Get current account information.
        
        Returns:
            AccountInfo if available, None otherwise
        """
        pass
    
    @abstractmethod
    async def open_positions(self, symbol: Optional[str] = None) -> List[PositionInfo]:
        """
        Get list of open positions.
        
        Args:
            symbol: Optional symbol filter. If None, return all positions.
            
        Returns:
            List of PositionInfo for open positions
        """
        pass
    
    @abstractmethod
    async def is_market_open(self, symbol: str) -> bool:
        """
        Check if market is currently open for trading.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if market open, False otherwise
        """
        pass
    
    # Optional methods with default implementations
    
    def get_name(self) -> str:
        """
        Get adapter name for logging/identification.
        
        Returns:
            Human-readable adapter name
        """
        return self.__class__.__name__
    
    def supports_feature(self, feature: str) -> bool:
        """
        Check if adapter supports specific feature.
        
        Args:
            feature: Feature name (e.g., 'limit_orders', 'trailing_stops')
            
        Returns:
            True if feature supported, False otherwise
        """
        # Base implementation - override in subclasses
        return False


# MT5-specific error code mapping
MT5_ERROR_CODE_MAP = {
    10004: ErrorCode.REQUOTE,
    10006: ErrorCode.ORDER_REJECTED,
    10013: ErrorCode.INPUT_INVALID,
    10014: ErrorCode.SIZE_INVALID,
    10015: ErrorCode.INPUT_INVALID,
    10016: ErrorCode.STOPLOSS_TOO_CLOSE,
    10017: ErrorCode.MARKET_CLOSED,
    10018: ErrorCode.MARKET_CLOSED,
    10019: ErrorCode.MARGIN_INSUFFICIENT,
    10021: ErrorCode.NO_FILL,
    10024: ErrorCode.TIMEOUT,
    10031: ErrorCode.NOT_CONNECTED,
}


def map_mt5_error(retcode: int) -> ErrorCode:
    """
    Map MT5 return code to unified ErrorCode.
    
    Args:
        retcode: MT5 return code
        
    Returns:
        Corresponding ErrorCode
    """
    return MT5_ERROR_CODE_MAP.get(retcode, ErrorCode.UNHANDLED)
