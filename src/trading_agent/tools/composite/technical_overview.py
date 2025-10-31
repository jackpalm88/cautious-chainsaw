"""
TechnicalOverview - Composite Tool
Aggregates multiple technical indicators into unified analysis
"""

import time
from typing import Any

from ..atomic.calc_bollinger_bands import CalcBollingerBands
from ..atomic.calc_macd import CalcMACD
from ..atomic.calc_rsi import CalcRSI
from ..base_tool import BaseTool, ToolResult, ToolTier


class TechnicalOverview(BaseTool):
    """
    Composite tool that aggregates RSI, MACD, and Bollinger Bands.

    Provides unified technical analysis with:
    - Individual indicator signals
    - Aggregated signal (consensus)
    - Indicator agreement score
    - Combined confidence

    Signal aggregation logic:
    - All bullish → bullish
    - All bearish → bearish
    - Mixed → neutral (with agreement score)
    """

    name = "technical_overview"
    version = "1.0.0"
    tier = ToolTier.COMPOSITE
    description = "Aggregate RSI, MACD, and Bollinger Bands into unified technical analysis"

    def __init__(
        self,
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        bb_period: int = 20,
        bb_std: float = 2.0,
    ):
        """
        Initialize technical overview.

        Args:
            rsi_period: RSI period (default: 14)
            macd_fast: MACD fast EMA (default: 12)
            macd_slow: MACD slow EMA (default: 26)
            macd_signal: MACD signal line (default: 9)
            bb_period: Bollinger Bands period (default: 20)
            bb_std: Bollinger Bands std multiplier (default: 2.0)
        """
        self.rsi_tool = CalcRSI(period=rsi_period)
        self.macd_tool = CalcMACD(fast_period=macd_fast, slow_period=macd_slow, signal_period=macd_signal)
        self.bb_tool = CalcBollingerBands(period=bb_period, std_multiplier=bb_std)

    def execute(self, prices: list[float], **kwargs) -> ToolResult:
        """
        Execute technical overview analysis.

        Args:
            prices: List of closing prices (oldest to newest)
            **kwargs: Additional parameters

        Returns:
            ToolResult with aggregated analysis
        """
        start_time = time.perf_counter()

        try:
            # Validate inputs
            self.validate_inputs(prices=prices)

            # Execute individual tools
            rsi_result = self.rsi_tool.execute(prices=prices)
            macd_result = self.macd_tool.execute(prices=prices)
            bb_result = self.bb_tool.execute(prices=prices)

            # Check for errors
            if rsi_result.error or macd_result.error or bb_result.error:
                errors = []
                if rsi_result.error:
                    errors.append(f"RSI: {rsi_result.error}")
                if macd_result.error:
                    errors.append(f"MACD: {macd_result.error}")
                if bb_result.error:
                    errors.append(f"BB: {bb_result.error}")

                raise ValueError("; ".join(errors))

            # Extract signals
            signals = {
                'rsi': rsi_result.value['signal'],
                'macd': macd_result.value['trading_signal'],
                'bollinger_bands': bb_result.value['signal'],
            }

            # Calculate indicator agreement
            agreement_score = self._calculate_agreement(signals)

            # Aggregate signals
            aggregated_signal = self._aggregate_signals(signals, agreement_score)

            # Calculate combined confidence
            combined_confidence = self._combine_confidence(
                rsi_result.confidence,
                macd_result.confidence,
                bb_result.confidence,
                agreement_score
            )

            # Calculate latency
            latency_ms = (time.perf_counter() - start_time) * 1000

            return ToolResult(
                value={
                    'aggregated_signal': aggregated_signal,
                    'agreement_score': round(agreement_score, 3),
                    'individual_signals': signals,
                    'indicators': {
                        'rsi': {
                            'value': rsi_result.value['rsi'],
                            'signal': rsi_result.value['signal'],
                            'confidence': rsi_result.confidence,
                        },
                        'macd': {
                            'macd': macd_result.value['macd'],
                            'signal_line': macd_result.value['signal'],
                            'histogram': macd_result.value['histogram'],
                            'signal': macd_result.value['trading_signal'],
                            'confidence': macd_result.confidence,
                        },
                        'bollinger_bands': {
                            'upper': bb_result.value['upper_band'],
                            'middle': bb_result.value['middle_band'],
                            'lower': bb_result.value['lower_band'],
                            'position': bb_result.value['band_position'],
                            'signal': bb_result.value['signal'],
                            'confidence': bb_result.confidence,
                        },
                    },
                },
                confidence=combined_confidence,
                latency_ms=round(latency_ms, 2),
                metadata={
                    'individual_confidences': {
                        'rsi': rsi_result.confidence,
                        'macd': macd_result.confidence,
                        'bollinger_bands': bb_result.confidence,
                    },
                    'individual_latencies': {
                        'rsi': rsi_result.latency_ms,
                        'macd': macd_result.latency_ms,
                        'bollinger_bands': bb_result.latency_ms,
                    },
                    'samples_used': len(prices),
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

    def validate_inputs(self, prices: list[float]) -> None:
        """Validate input parameters"""
        if not prices:
            raise ValueError("Prices list cannot be empty")

        # Need enough data for all indicators
        min_required = max(
            self.rsi_tool.period,
            self.macd_tool.slow_period + self.macd_tool.signal_period,
            self.bb_tool.period
        )

        if len(prices) < min_required:
            raise ValueError(
                f"Insufficient data: need {min_required} prices, got {len(prices)}"
            )

    def _calculate_agreement(self, signals: dict[str, str]) -> float:
        """
        Calculate indicator agreement score.

        Args:
            signals: Dict of indicator signals

        Returns:
            Agreement score (0.0 to 1.0)
        """
        signal_values = list(signals.values())

        # Count bullish, bearish, neutral
        bullish_count = sum(1 for s in signal_values if s == 'bullish')
        bearish_count = sum(1 for s in signal_values if s == 'bearish')
        neutral_count = sum(1 for s in signal_values if s == 'neutral')

        total = len(signal_values)

        # Perfect agreement
        if bullish_count == total or bearish_count == total:
            return 1.0

        # All neutral
        if neutral_count == total:
            return 0.5

        # Partial agreement
        max_agreement = max(bullish_count, bearish_count, neutral_count)
        return max_agreement / total

    def _aggregate_signals(
        self,
        signals: dict[str, str],
        agreement_score: float
    ) -> str:
        """
        Aggregate individual signals into unified signal.

        Args:
            signals: Dict of indicator signals
            agreement_score: Indicator agreement score

        Returns:
            Aggregated signal: 'bullish', 'bearish', or 'neutral'
        """
        signal_values = list(signals.values())

        # Count signals
        bullish_count = sum(1 for s in signal_values if s == 'bullish')
        bearish_count = sum(1 for s in signal_values if s == 'bearish')

        # Strong agreement required (≥2 out of 3)
        if bullish_count >= 2:
            return 'bullish'
        elif bearish_count >= 2:
            return 'bearish'
        else:
            return 'neutral'

    def _combine_confidence(
        self,
        rsi_conf: float,
        macd_conf: float,
        bb_conf: float,
        agreement_score: float
    ) -> float:
        """
        Combine individual confidences with agreement score.

        Args:
            rsi_conf: RSI confidence
            macd_conf: MACD confidence
            bb_conf: Bollinger Bands confidence
            agreement_score: Indicator agreement score

        Returns:
            Combined confidence (0.0 to 1.0)
        """
        # Weighted average of individual confidences
        avg_confidence = (rsi_conf + macd_conf + bb_conf) / 3

        # Boost confidence if indicators agree
        # Agreement weight: 0.2 (20% influence)
        combined = (avg_confidence * 0.8) + (agreement_score * 0.2)

        return min(1.0, combined)

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
                        "description": "List of closing prices (minimum 35 values for all indicators)",
                    },
                },
                "required": ["prices"],
            },
        }
