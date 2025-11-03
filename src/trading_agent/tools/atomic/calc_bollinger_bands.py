"""
CalcBollingerBands - Atomic Tool
Calculates Bollinger Bands with multi-factor confidence
"""

import time
from typing import Any

import numpy as np

from ..base_tool import BaseTool, ConfidenceCalculator, ConfidenceComponents, ToolResult, ToolTier


class CalcBollingerBands(BaseTool):
    """
    Calculate Bollinger Bands indicator.

    BB = SMA ± (StdDev × multiplier)

    Components:
    - Upper Band = SMA + (StdDev × 2)
    - Middle Band = SMA
    - Lower Band = SMA - (StdDev × 2)

    Interpretation:
    - Price near upper band: Overbought (potential sell)
    - Price near lower band: Oversold (potential buy)
    - Bands widening: Increasing volatility
    - Bands narrowing: Decreasing volatility (squeeze)
    """

    name = "calc_bollinger_bands"
    version = "1.0.0"
    tier = ToolTier.ATOMIC
    description = "Calculate Bollinger Bands with volatility analysis"

    def __init__(self, period: int = 20, std_multiplier: float = 2.0):
        """
        Initialize Bollinger Bands calculator.

        Args:
            period: SMA period (default: 20)
            std_multiplier: Standard deviation multiplier (default: 2.0)
        """
        self.period = period
        self.std_multiplier = std_multiplier

    def execute(self, prices: list[float], **kwargs) -> ToolResult:
        """
        Calculate Bollinger Bands for given price series.

        Args:
            prices: List of closing prices (oldest to newest)
            **kwargs: Additional parameters

        Returns:
            ToolResult with BB values and confidence
        """
        start_time = time.perf_counter()

        try:
            # Validate inputs
            self.validate_inputs(prices=prices)

            # Calculate Bollinger Bands
            upper, middle, lower = self._calculate_bands(prices)

            # Calculate current position relative to bands
            current_price = prices[-1]
            band_position = self._calculate_band_position(current_price, upper, middle, lower)

            # Calculate bandwidth (volatility measure)
            bandwidth = (upper - lower) / middle

            # Calculate confidence
            confidence_components = self._calculate_confidence(prices)
            confidence = confidence_components.calculate_confidence()

            # Determine signal
            signal = self._interpret_bands(band_position, bandwidth)

            # Calculate latency
            latency_ms = (time.perf_counter() - start_time) * 1000

            return ToolResult(
                value={
                    'upper_band': round(upper, 5),
                    'middle_band': round(middle, 5),
                    'lower_band': round(lower, 5),
                    'current_price': round(current_price, 5),
                    'band_position': round(band_position, 3),  # -1 to 1
                    'bandwidth': round(bandwidth, 4),
                    'signal': signal,
                },
                confidence=confidence,
                latency_ms=round(latency_ms, 2),
                metadata={
                    'confidence_components': confidence_components.to_dict(),
                    'samples_used': len(prices),
                    'required_samples': self.period,
                    'period': self.period,
                    'std_multiplier': self.std_multiplier,
                },
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                value=None, confidence=0.0, latency_ms=round(latency_ms, 2), error=str(e)
            )

    def validate_inputs(self, prices: list[float]) -> None:
        """Validate input parameters"""
        if not prices:
            raise ValueError("Prices list cannot be empty")

        if len(prices) < self.period:
            raise ValueError(f"Insufficient data: need {self.period} prices, got {len(prices)}")

        if any(p <= 0 for p in prices):
            raise ValueError("All prices must be positive")

    def _calculate_bands(self, prices: list[float]) -> tuple[float, float, float]:
        """
        Calculate Bollinger Bands.

        Args:
            prices: Price series

        Returns:
            Tuple of (upper_band, middle_band, lower_band)
        """
        prices_array = np.array(prices)

        # Calculate SMA (middle band)
        sma = np.mean(prices_array[-self.period :])

        # Calculate standard deviation
        std = np.std(prices_array[-self.period :])

        # Calculate bands
        upper_band = sma + (std * self.std_multiplier)
        lower_band = sma - (std * self.std_multiplier)

        return upper_band, sma, lower_band

    def _calculate_band_position(
        self, price: float, upper: float, middle: float, lower: float
    ) -> float:
        """
        Calculate price position relative to bands.

        Returns:
            -1.0: At lower band
             0.0: At middle band
             1.0: At upper band
        """
        if upper == lower:
            return 0.0

        # Normalize to [-1, 1]
        position = (price - middle) / (upper - middle)

        # Clamp to [-1, 1]
        return max(-1.0, min(1.0, position))

    def _calculate_confidence(self, prices: list[float]) -> ConfidenceComponents:
        """
        Calculate multi-factor confidence.

        Args:
            prices: Price series

        Returns:
            ConfidenceComponents with all factors
        """
        # Sample sufficiency
        required_samples = self.period
        actual_samples = len(prices)
        sample_sufficiency = ConfidenceCalculator.sample_sufficiency(
            actual_samples, required_samples
        )

        # Volatility regime
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns) * np.sqrt(252)  # Annualized
        volatility_regime = ConfidenceCalculator.volatility_regime(volatility)

        # Data quality
        gaps = 0
        flat_periods = sum(1 for i in range(1, len(prices)) if prices[i] == prices[i - 1])
        data_quality = ConfidenceCalculator.data_quality(gaps, flat_periods, len(prices))

        # Indicator agreement (single indicator)
        indicator_agreement = 0.8

        return ConfidenceComponents(
            sample_sufficiency=sample_sufficiency,
            volatility_regime=volatility_regime,
            indicator_agreement=indicator_agreement,
            data_quality=data_quality,
        )

    def _interpret_bands(self, band_position: float, bandwidth: float) -> str:
        """
        Interpret Bollinger Bands as trading signal.

        Args:
            band_position: Position relative to bands (-1 to 1)
            bandwidth: Band width (volatility measure)

        Returns:
            Signal: 'bullish', 'bearish', or 'neutral'
        """
        # Near lower band (oversold)
        if band_position < -0.8:
            return 'bullish'

        # Near upper band (overbought)
        elif band_position > 0.8:
            return 'bearish'

        # Squeeze (low volatility) - neutral
        elif bandwidth < 0.02:
            return 'neutral'

        # Middle range
        else:
            return 'neutral'

    def get_schema(self) -> dict[str, Any]:
        """Get JSON-Schema for LLM function calling"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "prices": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": f"List of closing prices (minimum {self.period} values)",
                    },
                },
                "required": ["prices"],
            },
        }
