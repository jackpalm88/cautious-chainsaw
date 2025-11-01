"""
MarketContext Tool - Tirgus režīma un volatilitātes analīze

Nosaka:
- Tirgus režīmu (trending, ranging, volatile)
- Volatilitāti (ATR - Average True Range)
- Trend stiprumu (ADX aproksimācija)
"""

import numpy as np

from ..base_tool import BaseTool, ToolResult, ToolTier


class MarketContext(BaseTool):
    """
    Analizē tirgus kontekstu no cenu datiem.

    Outputs:
    - regime: "trending", "ranging", "volatile"
    - volatility: ATR vērtība (normalized)
    - trend_strength: 0.0-1.0 (cik spēcīgs trends)
    - confidence: Pārliecība par režīma noteikšanu
    """

    name = "market_context"
    version = "1.0.0"
    tier = ToolTier.ATOMIC
    description = "Determines market regime and volatility"

    def __init__(self, atr_period: int = 14, regime_lookback: int = 50):
        """
        Args:
            atr_period: ATR aprēķina periods
            regime_lookback: Cik daudz sveces izmantot režīma noteikšanai
        """
        self.atr_period = atr_period
        self.regime_lookback = regime_lookback

    def validate_inputs(self, **kwargs) -> tuple[bool, str]:
        """Validate input parameters"""
        if "prices" not in kwargs:
            return False, "Missing required parameter: prices"

        prices = kwargs["prices"]

        if not isinstance(prices, (list, np.ndarray)):
            return False, "prices must be a list or numpy array"

        if len(prices) < max(self.atr_period, self.regime_lookback):
            return False, (
                f"Need at least {max(self.atr_period, self.regime_lookback)} "
                f"prices, got {len(prices)}"
            )

        return True, ""

    def execute(self, prices: list[float], **kwargs) -> ToolResult:
        """
        Analyze market context.

        Args:
            prices: List of closing prices (chronological order)

        Returns:
            ToolResult with market context data
        """
        import time
        start_time = time.perf_counter()

        prices = np.array(prices)

        # Calculate ATR (volatility)
        atr = self._calculate_atr(prices)
        atr_normalized = atr / prices[-1]  # Normalize by current price

        # Detect regime
        regime, regime_confidence = self._detect_regime(prices)

        # Calculate trend strength
        trend_strength = self._calculate_trend_strength(prices)

        # Overall confidence
        confidence = self._calculate_confidence(
            regime_confidence,
            len(prices),
            atr_normalized
        )

        # Calculate latency
        latency_ms = (time.perf_counter() - start_time) * 1000

        return ToolResult(
            value={
                "regime": regime,
                "volatility": float(atr),
                "volatility_normalized": float(atr_normalized),
                "trend_strength": float(trend_strength),
            },
            confidence=confidence,
            latency_ms=round(latency_ms, 2),
            metadata={
                "atr_period": self.atr_period,
                "regime_lookback": self.regime_lookback,
                "sample_size": len(prices),
            }
        )

    def _calculate_atr(self, prices: np.ndarray) -> float:
        """
        Calculate Average True Range (simplified version).

        Uses high-low range as proxy for true range.
        """
        # Calculate price changes (proxy for true range)
        price_changes = np.abs(np.diff(prices))

        # Take last N periods
        recent_changes = price_changes[-self.atr_period:]

        # Average
        atr = np.mean(recent_changes)

        return atr

    def _detect_regime(self, prices: np.ndarray) -> tuple[str, float]:
        """
        Detect market regime.

        Logic:
        - trending: Strong directional movement
        - ranging: Price oscillates in a range
        - volatile: High volatility with no clear direction

        Returns:
            (regime, confidence)
        """
        # Use last N candles
        recent_prices = prices[-self.regime_lookback:]

        # Calculate metrics
        price_mean = recent_prices.mean()
        price_std = recent_prices.std()

        # Trend direction
        linear_fit = np.polyfit(range(len(recent_prices)), recent_prices, 1)
        slope = linear_fit[0]
        slope_normalized = slope / price_mean  # Normalize by price level

        # Volatility
        volatility = price_std / price_mean

        # Decision logic
        # Prioritize trend detection over volatility
        if abs(slope_normalized) > 0.005:  # Lowered threshold
            # Strong slope = trending (even with some volatility)
            regime = "trending"
            confidence = min(abs(slope_normalized) * 100, 0.95)

        elif volatility > 0.04:  # Raised threshold
            # Very high volatility = volatile
            regime = "volatile"
            confidence = min(volatility * 20, 0.90)

        else:
            # Default = ranging
            regime = "ranging"
            confidence = 0.70

        return regime, confidence

    def _calculate_trend_strength(self, prices: np.ndarray) -> float:
        """
        Calculate trend strength (0.0 = no trend, 1.0 = strong trend).

        Uses linear regression R² as proxy.
        """
        recent_prices = prices[-self.regime_lookback:]

        # Linear regression
        x = np.arange(len(recent_prices))
        coeffs = np.polyfit(x, recent_prices, 1)
        fitted = np.polyval(coeffs, x)

        # R² (coefficient of determination)
        ss_res = np.sum((recent_prices - fitted) ** 2)
        ss_tot = np.sum((recent_prices - recent_prices.mean()) ** 2)

        if ss_tot == 0:
            return 0.0

        r_squared = 1 - (ss_res / ss_tot)

        # Clamp to [0, 1]
        return max(0.0, min(1.0, r_squared))

    def _calculate_confidence(
        self,
        regime_confidence: float,
        sample_size: int,
        volatility_normalized: float
    ) -> float:
        """
        Calculate overall confidence in market context analysis.

        Factors:
        - Regime detection confidence
        - Sample size sufficiency
        - Volatility stability
        """
        # Sample size factor (need at least 50 candles)
        sample_factor = min(sample_size / 100, 1.0) ** 0.3

        # Volatility stability (lower volatility = higher confidence)
        volatility_factor = max(0.5, 1.0 - volatility_normalized * 10)

        # Combine
        confidence = (
            regime_confidence ** 0.5 *
            sample_factor ** 0.3 *
            volatility_factor ** 0.2
        )

        return min(confidence, 0.95)

    def get_schema(self) -> dict:
        """Get JSON-Schema for LLM function calling"""
        return {
            "name": "market_context",
            "description": (
                "Analyzes market regime and volatility. "
                "Returns regime (trending/ranging/volatile), "
                "volatility (ATR), and trend strength."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prices": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "List of closing prices (chronological)",
                    }
                },
                "required": ["prices"],
            },
        }

    def to_llm_function(self) -> dict:
        """Convert to LLM function calling format (alias for get_schema)"""
        return self.get_schema()
