"""
CalcRSI - Atomic Tool
Calculates Relative Strength Index with multi-factor confidence
"""

import time
from typing import List, Dict, Any
import numpy as np

from ..base_tool import BaseTool, ToolResult, ToolTier, ConfidenceComponents, ConfidenceCalculator


class CalcRSI(BaseTool):
    """
    Calculate RSI (Relative Strength Index) indicator.

    RSI = 100 - (100 / (1 + RS))
    where RS = Average Gain / Average Loss

    Interpretation:
    - RSI > 70: Overbought (potential sell signal)
    - RSI < 30: Oversold (potential buy signal)
    - RSI 40-60: Neutral
    """

    name = "calc_rsi"
    version = "1.0.0"
    tier = ToolTier.ATOMIC
    description = "Calculate Relative Strength Index (RSI) with confidence scoring"

    def __init__(self, period: int = 14):
        """
        Initialize RSI calculator.

        Args:
            period: RSI period (default: 14)
        """
        self.period = period

    def execute(self, prices: List[float], **kwargs) -> ToolResult:
        """
        Calculate RSI for given price series.

        Args:
            prices: List of closing prices (oldest to newest)
            **kwargs: Additional parameters (ignored)

        Returns:
            ToolResult with RSI value and confidence
        """
        start_time = time.perf_counter()

        try:
            # Validate inputs
            self.validate_inputs(prices=prices)

            # Calculate RSI
            rsi_value = self._calculate_rsi(prices)

            # Calculate confidence
            confidence_components = self._calculate_confidence(prices)
            confidence = confidence_components.calculate_confidence()

            # Determine signal
            signal = self._interpret_rsi(rsi_value)

            # Calculate latency
            latency_ms = (time.perf_counter() - start_time) * 1000

            return ToolResult(
                value={
                    'rsi': round(rsi_value, 2),
                    'signal': signal,
                    'period': self.period,
                },
                confidence=confidence,
                latency_ms=round(latency_ms, 2),
                metadata={
                    'confidence_components': confidence_components.to_dict(),
                    'samples_used': len(prices),
                    'required_samples': self.period + 1,
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

    def validate_inputs(self, prices: List[float]) -> None:
        """Validate input parameters"""
        if not prices:
            raise ValueError("Prices list cannot be empty")

        if len(prices) < self.period + 1:
            raise ValueError(
                f"Insufficient data: need {self.period + 1} prices, got {len(prices)}"
            )

        if any(p <= 0 for p in prices):
            raise ValueError("All prices must be positive")

    def _calculate_rsi(self, prices: List[float]) -> float:
        """
        Calculate RSI using Wilder's smoothing method.

        Args:
            prices: Price series

        Returns:
            RSI value (0-100)
        """
        prices_array = np.array(prices)

        # Calculate price changes
        deltas = np.diff(prices_array)

        # Separate gains and losses
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        # Calculate average gain and loss (Wilder's smoothing)
        avg_gain = np.mean(gains[:self.period])
        avg_loss = np.mean(losses[:self.period])

        # Calculate subsequent smoothed values
        for i in range(self.period, len(gains)):
            avg_gain = (avg_gain * (self.period - 1) + gains[i]) / self.period
            avg_loss = (avg_loss * (self.period - 1) + losses[i]) / self.period

        # Calculate RS and RSI
        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_confidence(self, prices: List[float]) -> ConfidenceComponents:
        """
        Calculate multi-factor confidence.

        Args:
            prices: Price series

        Returns:
            ConfidenceComponents with all factors
        """
        # Sample sufficiency
        required_samples = self.period + 1
        actual_samples = len(prices)
        sample_sufficiency = ConfidenceCalculator.sample_sufficiency(
            actual_samples, required_samples
        )

        # Volatility regime
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns) * np.sqrt(252)  # Annualized
        volatility_regime = ConfidenceCalculator.volatility_regime(volatility)

        # Data quality (check for gaps and flat periods)
        gaps = 0  # Assume no gaps for now
        flat_periods = sum(1 for i in range(1, len(prices)) if prices[i] == prices[i-1])
        data_quality = ConfidenceCalculator.data_quality(gaps, flat_periods, len(prices))

        # Indicator agreement (single indicator, so neutral)
        indicator_agreement = 0.8  # High for single indicator

        return ConfidenceComponents(
            sample_sufficiency=sample_sufficiency,
            volatility_regime=volatility_regime,
            indicator_agreement=indicator_agreement,
            data_quality=data_quality,
        )

    def _interpret_rsi(self, rsi: float) -> str:
        """
        Interpret RSI value as trading signal.

        Args:
            rsi: RSI value (0-100)

        Returns:
            Signal: 'bullish', 'bearish', or 'neutral'
        """
        if rsi > 70:
            return 'bearish'  # Overbought
        elif rsi < 30:
            return 'bullish'  # Oversold
        else:
            return 'neutral'

    def get_schema(self) -> Dict[str, Any]:
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
                        "description": f"List of closing prices (minimum {self.period + 1} values)",
                    },
                },
                "required": ["prices"],
            },
        }
