"""
RiskFixedFractional - Atomic Tool
Position sizing based on fixed fractional risk with full symbol normalization
"""

import time
from typing import Any

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

    This tool uses UniversalSymbolNormalizer for accurate risk calculation
    across different brokers and asset types.
    """

    name = "risk_fixed_fractional"
    version = "2.0.0"
    tier = ToolTier.ATOMIC
    description = "Calculate position size using fixed fractional risk with full multi-broker normalization"

    def __init__(self, normalizer: Any | None = None):
        """
        Initialize risk calculator.

        Args:
            normalizer: UniversalSymbolNormalizer instance for multi-broker support
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
                sl_value_per_lot = self.normalizer.to_risk_units(
                    symbol, stop_loss_pips, "pips"
                )
            else:
                # Simplified calculation (FX majors only)
                sl_value_per_lot = self._simplified_sl_calculation(symbol, stop_loss_pips)

            # Calculate position size
            if sl_value_per_lot == 0:
                raise ValueError("Stop loss value cannot be zero")

            raw_position_size = risk_amount / sl_value_per_lot

            # Round to valid lot size
            if self.normalizer:
                position_size = self.normalizer.round_to_lot_size(symbol, raw_position_size)
            else:
                # Standard rounding to 0.01 lots
                position_size = round(raw_position_size, 2)

            # Get symbol info for metadata
            symbol_info = None
            if self.normalizer:
                try:
                    symbol_info = self.normalizer.get_normalized_info(symbol)
                except Exception:
                    pass

            # Calculate latency
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Build metadata
            metadata = {
                'calculation_method': 'normalized' if self.normalizer else 'simplified',
                'balance': balance,
                'stop_loss_pips': stop_loss_pips,
                'raw_position_size': round(raw_position_size, 4),
                'sl_value_per_lot': round(sl_value_per_lot, 2),
            }

            if symbol_info:
                metadata['symbol_info'] = {
                    'category': symbol_info.category,
                    'base_currency': symbol_info.base_currency,
                    'quote_currency': symbol_info.quote_currency,
                    'min_size': symbol_info.min_size,
                    'max_size': symbol_info.max_size,
                    'size_step': symbol_info.size_step,
                }

            return ToolResult(
                value={
                    'position_size': position_size,
                    'risk_amount': round(risk_amount, 2),
                    'stop_loss_value': round(sl_value_per_lot, 2),
                    'symbol': symbol,
                    'risk_pct': risk_pct,
                },
                confidence=0.95,  # High confidence - deterministic calculation
                latency_ms=round(latency_ms, 2),
                metadata=metadata
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
            Stop loss value in account currency per lot
        """
        # Check if JPY pair
        if symbol.endswith("JPY"):
            # JPY pairs: 1 pip = 0.01
            pip_value = 10.0  # $10 per pip for standard lot
        else:
            # FX majors: 1 pip = 0.0001
            pip_value = 10.0  # $10 per pip for standard lot

        # For standard lot (100,000 units)
        sl_value = stop_loss_pips * pip_value

        return sl_value

    def get_schema(self) -> dict[str, Any]:
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
