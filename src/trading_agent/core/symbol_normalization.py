"""
Symbol Normalization Module

Multi-broker symbol information normalization for consistent risk calculations
across MT5, Binance, IBKR, and other platforms.

Based on: INoT Deep Dive Architecture Decision #1
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BinanceAdapterProtocol(Protocol):
    def get_current_price(self, symbol: str) -> float: ...

    def get_symbol_info(self, symbol: str) -> dict: ...


@dataclass(frozen=True)
class NormalizedSymbolInfo:
    """
    Broker-agnostic symbol information.

    All brokers normalize to this unified format, enabling consistent
    risk calculations regardless of underlying API differences.
    """

    symbol: str
    category: str  # "forex" | "crypto" | "cfd" | "stock" | "futures"
    base_currency: str
    quote_currency: str

    # Lot size constraints
    min_size: float
    max_size: float
    size_step: float

    # Price precision
    price_precision: int  # Decimal places
    min_price_move: float  # Tick size

    # Value calculation
    value_per_tick: float  # Monetary value of 1 tick movement
    contract_multiplier: float  # Contract size (e.g., 100,000 for FX standard lot)

    def __post_init__(self) -> None:
        """Validate symbol info consistency"""
        if self.min_size <= 0:
            raise ValueError(f"min_size must be positive, got {self.min_size}")
        if self.max_size < self.min_size:
            raise ValueError(f"max_size {self.max_size} < min_size {self.min_size}")
        if self.size_step <= 0:
            raise ValueError(f"size_step must be positive, got {self.size_step}")
        if self.min_price_move <= 0:
            raise ValueError(f"min_price_move must be positive, got {self.min_price_move}")


@runtime_checkable
class BrokerNormalizer(Protocol):
    adapter: Any
    """
    Protocol for broker-specific symbol normalization.

    Each broker adapter implements this to convert their native
    symbol info format to NormalizedSymbolInfo.
    """

    @abstractmethod
    def parse_symbol_info(self, raw_info: dict) -> NormalizedSymbolInfo:
        """
        Convert broker-specific symbol info to normalized format.

        Args:
            raw_info: Native symbol info from broker API

        Returns:
            Normalized symbol information

        Raises:
            ValueError: If raw_info is invalid or incomplete
        """
        ...

    @abstractmethod
    def calculate_pip_value(self, symbol: str, lot_size: float) -> float:
        """
        Calculate monetary value of pip/tick movement.

        Args:
            symbol: Symbol identifier (e.g., "EURUSD", "BTCUSDT")
            lot_size: Position size in lots

        Returns:
            Monetary value per pip/tick
        """
        ...


class MT5Normalizer:
    """
    MetaTrader 5 symbol normalizer.

    MT5 provides comprehensive symbol info through SymbolInfo structure.
    Reference: https://www.mql5.com/en/docs/python_metatrader5/mt5symbolinfo_py
    """

    def __init__(self, adapter) -> None:  # type: ignore
        """
        Args:
            adapter: MT5 adapter instance with get_symbol_info() method
        """
        self.adapter = adapter

    def parse_symbol_info(self, raw_info: dict) -> NormalizedSymbolInfo:
        """
        Parse MT5 SymbolInfo to normalized format.

        MT5 fields:
        - trade_contract_size: Contract multiplier (100,000 for standard lot)
        - trade_tick_value: Monetary value per tick
        - volume_min/max/step: Lot constraints
        - point: Minimum price change (0.0001 for EUR/USD)
        - digits: Price decimal places
        """
        return NormalizedSymbolInfo(
            symbol=raw_info["name"],
            category=self._detect_category(raw_info),
            base_currency=raw_info["currency_base"],
            quote_currency=raw_info["currency_profit"],
            min_size=raw_info["volume_min"],
            max_size=raw_info["volume_max"],
            size_step=raw_info["volume_step"],
            price_precision=raw_info["digits"],
            min_price_move=raw_info["point"],
            value_per_tick=raw_info["trade_tick_value"],
            contract_multiplier=raw_info["trade_contract_size"],
        )

    def calculate_pip_value(self, symbol: str, lot_size: float) -> float:
        """Calculate pip value for MT5 symbol"""
        info = self.parse_symbol_info(self.adapter.get_symbol_info(symbol))
        return info.value_per_tick * lot_size

    @staticmethod
    def _detect_category(raw_info: dict) -> str:
        """Detect instrument category from MT5 symbol properties"""
        # MT5 doesn't have explicit category field
        # Heuristic: check symbol path or name patterns
        path = raw_info.get("path", "")
        name = raw_info["name"]

        if "Forex" in path or len(name) == 6:
            return "forex"
        elif "CFD" in path or "Index" in path:
            return "cfd"
        elif "Crypto" in path or "BTC" in name or "ETH" in name:
            return "crypto"
        else:
            return "forex"  # Default assumption


class BinanceNormalizer:
    """
    Binance symbol normalizer.

    Binance uses filters to define lot size and price constraints.
    Reference: https://developers.binance.com/docs/binance-spot-api-docs/filters
    """

    def __init__(self, adapter: BinanceAdapterProtocol) -> None:
        self.adapter = adapter

    def parse_symbol_info(self, raw_info: dict) -> NormalizedSymbolInfo:
        """
        Parse Binance exchangeInfo symbol to normalized format.

        Binance filters:
        - LOT_SIZE: {minQty, maxQty, stepSize}
        - PRICE_FILTER: {tickSize}
        """
        # Extract filters
        lot_filter = next((f for f in raw_info["filters"] if f["filterType"] == "LOT_SIZE"), None)
        price_filter = next(
            (f for f in raw_info["filters"] if f["filterType"] == "PRICE_FILTER"), None
        )

        if not lot_filter or not price_filter:
            raise ValueError(f"Missing required filters for {raw_info['symbol']}")

        tick_size = float(price_filter["tickSize"])

        # Crypto tick value varies with price - must fetch current price
        current_price = self.adapter.get_current_price(raw_info["symbol"])

        return NormalizedSymbolInfo(
            symbol=raw_info["symbol"],
            category="crypto",
            base_currency=raw_info["baseAsset"],
            quote_currency=raw_info["quoteAsset"],
            min_size=float(lot_filter["minQty"]),
            max_size=float(lot_filter["maxQty"]),
            size_step=float(lot_filter["stepSize"]),
            price_precision=len(price_filter["tickSize"].split(".")[-1]),
            min_price_move=tick_size,
            value_per_tick=tick_size * current_price,  # Dynamic!
            contract_multiplier=1.0,  # Spot crypto is 1:1
        )

    def calculate_pip_value(self, symbol: str, lot_size: float) -> float:
        """
        Calculate tick value for Binance crypto.

        Note: Crypto tick value changes with price, so we recalculate each time.
        """
        info = self.parse_symbol_info(self.adapter.get_symbol_info(symbol))
        # Refresh price for accurate calculation
        current_price = self.adapter.get_current_price(symbol)
        return info.min_price_move * current_price * lot_size


class IBKRNormalizer:
    """
    Interactive Brokers normalizer.

    Status: Stub for v1.0 (full implementation in v1.1)
    """

    def __init__(self, adapter) -> None:  # type: ignore
        self.adapter = adapter

    def parse_symbol_info(self, raw_info: dict) -> NormalizedSymbolInfo:
        raise NotImplementedError("IBKR normalizer scheduled for v1.1")

    def calculate_pip_value(self, symbol: str, lot_size: float) -> float:
        raise NotImplementedError("IBKR normalizer scheduled for v1.1")


class NormalizerFactory:
    """Factory for creating broker-specific normalizers"""

    @staticmethod
    def create(broker_type: str, adapter) -> BrokerNormalizer:  # type: ignore
        """
        Create normalizer for specified broker.

        Args:
            broker_type: "mt5" | "binance" | "ibkr"
            adapter: Broker adapter instance

        Returns:
            Appropriate normalizer

        Raises:
            ValueError: If broker_type not supported
        """
        if broker_type == "mt5":
            return MT5Normalizer(adapter)
        elif broker_type == "binance":
            return BinanceNormalizer(adapter)
        elif broker_type == "ibkr":
            return IBKRNormalizer(adapter)
        else:
            raise ValueError(f"Unsupported broker type: {broker_type}")


class UniversalSymbolNormalizer:
    """
    Broker-agnostic facade for symbol normalization.

    This is the primary interface used by risk calculation tools.
    """

    def __init__(self, broker_normalizer: BrokerNormalizer):
        self.broker = broker_normalizer

    def to_risk_units(self, symbol: str, distance: float, unit_type: str = "pips") -> float:
        """
        Convert user distance (pips/ticks) to monetary risk value.

        Args:
            symbol: Symbol identifier
            distance: Distance in user units (e.g., 20 pips)
            unit_type: "pips" | "ticks" | "points"

        Returns:
            Monetary value of the distance per lot

        Example:
            >>> normalizer.to_risk_units("EURUSD", 20, "pips")
            200.0  # $200 per lot for 20 pips
        """
        info = self.broker.parse_symbol_info(self.broker.adapter.get_symbol_info(symbol))

        # Convert distance to price units
        price_distance = self._convert_to_price_distance(info, distance, unit_type)

        # Calculate monetary value
        if info.category == "crypto":
            # For crypto, value_per_tick is dynamic (price * tick_size)
            # and contract_multiplier is 1.
            num_ticks = price_distance / info.min_price_move
            monetary_value = num_ticks * info.value_per_tick
        else:
            # For Forex/CFD, value_per_tick is often fixed per lot.
            monetary_value = price_distance * info.contract_multiplier * info.value_per_tick

        return monetary_value

    def get_normalized_info(self, symbol: str) -> NormalizedSymbolInfo:
        """Get normalized symbol info directly"""
        return self.broker.parse_symbol_info(self.broker.adapter.get_symbol_info(symbol))

    @staticmethod
    def _convert_to_price_distance(
        info: NormalizedSymbolInfo, distance: float, unit_type: str
    ) -> float:
        """
        Convert user distance to price change.

        Handles special cases:
        - FX JPY pairs: 1 pip = 0.01 (not 0.0001)
        - FX majors: 1 pip = 0.0001
        - Other: use tick size
        """
        if unit_type == "pips":
            if info.category == "forex":
                # Special case: JPY pairs
                if info.quote_currency == "JPY":
                    return distance * 0.01
                else:
                    return distance * 0.0001
            else:
                # Non-FX: "pips" = ticks
                return distance * info.min_price_move

        elif unit_type in ("ticks", "points"):
            return distance * info.min_price_move

        else:
            raise ValueError(f"Unknown unit_type: {unit_type}")

    def round_to_lot_size(self, symbol: str, raw_lots: float) -> float:
        """
        Round position size to valid lot size for symbol.

        Args:
            symbol: Symbol identifier
            raw_lots: Calculated position size

        Returns:
            Valid lot size (respects min/max/step)
        """
        info = self.get_normalized_info(symbol)

        # Clamp to min/max
        lots = max(info.min_size, min(raw_lots, info.max_size))

        # Round to step size
        lots = round(lots / info.size_step) * info.size_step

        return lots
