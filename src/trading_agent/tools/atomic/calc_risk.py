"""
RiskFixedFractional - Atomic Tool
Position sizing based on fixed fractional risk with symbol normalization
"""

import time
from typing import Dict, Any, Optional
from ..base_tool import BaseTool, ToolResult, ToolTier


class RiskFixedFractional(BaseTool):
    """
    Calculate position size using fixed fractional risk method.
    
    Formula:
        position_size = (account_balance × risk_pct) / stop_loss_value
    
    Where stop_loss_value is normalized across different asset types:
    - FX majors: 1 pip = 0.0001
    - FX JPY pairs: 1 pip = 0.01
    - CFD indices: 1 point = direct value
    - Crypto: tick value varies with price
    
    This tool uses symbol normalization to ensure accurate risk calculation
    across different brokers and asset types.
    """
    
    name = "risk_fixed_fractional"
    version = "1.0.0"
    tier = ToolTier.ATOMIC
    description = "Calculate position size using fixed fractional risk with multi-broker normalization"
    
    def __init__(self, normalizer: Optional[Any] = None):
        """
        Initialize risk calculator.
        
        Args:
            normalizer: SymbolNormalizer instance for multi-broker support
                       If None, uses simplified calculation (FX majors only)
        """
        self.normalizer = normalizer
    
    def execute(
        self,
        balance: float,
        risk_pct: float,
        stop_loss_pips: float,
        symbol: str,
        **kwargs
    ) -> ToolResult:
        """
        Calculate position size.
        
        Args:
            balance: Account balance
            risk_pct: Risk percentage (e.g., 0.01 for 1%)
            stop_loss_pips: Stop loss distance in pips
            symbol: Trading symbol (e.g., "EURUSD", "BTCUSD")
            **kwargs: Additional parameters
            
        Returns:
            ToolResult with position size and confidence
        """
        start_time = time.perf_counter()
        
        try:
            # Validate inputs
            self.validate_inputs(
                balance=balance,
                risk_pct=risk_pct,
                stop_loss_pips=stop_loss_pips,
                symbol=symbol
            )
            
            # Calculate risk amount
            risk_amount = balance * risk_pct
            
            # Calculate stop loss value (normalized)
            if self.normalizer:
                # Use normalizer for accurate multi-broker calculation
                sl_value = self.normalizer.to_risk_units(
                    symbol, stop_loss_pips, "pips"
                )
            else:
                # Simplified calculation (FX majors only)
                sl_value = self._simplified_sl_calculation(symbol, stop_loss_pips)
            
            # Calculate position size
            if sl_value == 0:
                raise ValueError("Stop loss value cannot be zero")
            
            position_size = risk_amount / sl_value
            
            # Round to valid lot size (if normalizer available)
            if self.normalizer:
                position_size = self._round_to_lot_size(symbol, position_size)
            else:
                # Standard rounding to 0.01 lots
                position_size = round(position_size, 2)
            
            # Calculate latency
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            return ToolResult(
                value={
                    'position_size': position_size,
                    'risk_amount': round(risk_amount, 2),
                    'stop_loss_value': round(sl_value, 2),
                    'symbol': symbol,
                    'risk_pct': risk_pct,
                },
                confidence=0.95,  # High confidence - deterministic calculation
                latency_ms=round(latency_ms, 2),
                metadata={
                    'calculation_method': 'normalized' if self.normalizer else 'simplified',
                    'balance': balance,
                    'stop_loss_pips': stop_loss_pips,
                }
            )
            
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                value=None,
                confidence=0.0,
                latency_ms=round(latency_ms, 2),
                error=str(e)
            )
    
    def validate_inputs(
        self,
        balance: float,
        risk_pct: float,
        stop_loss_pips: float,
        symbol: str
    ) -> None:
        """Validate input parameters"""
        if balance <= 0:
            raise ValueError("Balance must be positive")
        
        if not 0 < risk_pct <= 0.1:  # Max 10% risk
            raise ValueError("Risk percentage must be between 0 and 0.1 (10%)")
        
        if stop_loss_pips <= 0:
            raise ValueError("Stop loss must be positive")
        
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")
    
    def _simplified_sl_calculation(self, symbol: str, stop_loss_pips: float) -> float:
        """
        Simplified stop loss calculation for FX majors.
        
        This is a fallback when no normalizer is available.
        Assumes standard lot size (100,000 units) and FX major conventions.
        
        Args:
            symbol: Trading symbol
            stop_loss_pips: Stop loss in pips
            
        Returns:
            Stop loss value in account currency
        """
        # Check if JPY pair
        if symbol.endswith("JPY"):
            # JPY pairs: 1 pip = 0.01
            pip_value = 10.0  # $10 per pip for standard lot
            pip_distance = stop_loss_pips * 0.01
        else:
            # FX majors: 1 pip = 0.0001
            pip_value = 10.0  # $10 per pip for standard lot
            pip_distance = stop_loss_pips * 0.0001
        
        # For standard lot (100,000 units)
        sl_value = stop_loss_pips * pip_value
        
        return sl_value
    
    def _round_to_lot_size(self, symbol: str, position_size: float) -> float:
        """
        Round position size to valid lot size.
        
        Args:
            symbol: Trading symbol
            position_size: Calculated position size
            
        Returns:
            Rounded position size
        """
        if not self.normalizer:
            return round(position_size, 2)
        
        try:
            # Get symbol info from normalizer
            info = self.normalizer.get_normalized_info(symbol)
            
            # Apply constraints
            min_lot = info.get('min_size', 0.01)
            max_lot = info.get('max_size', 100.0)
            lot_step = info.get('size_step', 0.01)
            
            # Clamp to min/max
            position_size = max(min_lot, min(position_size, max_lot))
            
            # Round to lot step
            position_size = round(position_size / lot_step) * lot_step
            
            return position_size
            
        except Exception:
            # Fallback to standard rounding
            return round(position_size, 2)
    
    def get_schema(self) -> Dict[str, Any]:
        """Get JSON-Schema for LLM function calling"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "balance": {
                        "type": "number",
                        "description": "Account balance in base currency",
                    },
                    "risk_pct": {
                        "type": "number",
                        "description": "Risk percentage as decimal (e.g., 0.01 for 1%)",
                    },
                    "stop_loss_pips": {
                        "type": "number",
                        "description": "Stop loss distance in pips",
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Trading symbol (e.g., 'EURUSD', 'BTCUSD')",
                    },
                },
                "required": ["balance", "risk_pct", "stop_loss_pips", "symbol"],
            },
        }
