"""
MT5 Bridge Hybrid v2.0 - Core Module

Production-ready execution bridge with Adapter Pattern.
Swap execution providers (MT5, IBKR, Binance, etc.) without changing bridge code.
"""

# Adapter Base (Interface + Error Codes)
from .adapter_base import (
    BaseExecutionAdapter,
    ErrorCode,
    SymbolInfo,
    OrderRequest,
    OrderResult,
    AccountInfo,
    PositionInfo
)

# Concrete Adapters
from .adapter_mock import MockAdapter

# RealMT5Adapter is optional (requires MetaTrader5 package)
try:
    from .adapter_mt5 import RealMT5Adapter
    _HAS_MT5 = True
except ImportError:
    RealMT5Adapter = None
    _HAS_MT5 = False

# Bridge
from .bridge import (
    MT5ExecutionBridge,
    Signal,
    OrderDirection,
    ExecutionResult,
    ExecutionStatus
)

# Version
__version__ = '2.0.0'

# Export all public APIs
__all__ = [
    # Adapters
    'BaseExecutionAdapter',
    'MockAdapter',
    'RealMT5Adapter',
    
    # Bridge
    'MT5ExecutionBridge',
    
    # Data Structures
    'Signal',
    'OrderDirection',
    'OrderRequest',
    'OrderResult',
    'SymbolInfo',
    'AccountInfo',
    'PositionInfo',
    'ExecutionResult',
    'ExecutionStatus',
    
    # Error Handling
    'ErrorCode',
    
    # Version
    '__version__'
]
