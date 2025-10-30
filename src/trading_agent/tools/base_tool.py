"""
Base Tool Interface
Defines contract for all trading agent tools (atomic, composite, execution)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
from datetime import datetime
from enum import Enum


class ToolTier(Enum):
    """Tool classification by complexity"""
    ATOMIC = "atomic"  # Single-purpose, deterministic functions
    COMPOSITE = "composite"  # Multi-tool aggregation
    EXECUTION = "execution"  # External system interaction


@dataclass
class ToolResult:
    """
    Standardized result format for all tools.

    Attributes:
        value: Tool output (dict, float, str, etc.)
        confidence: Confidence score (0.0-1.0) based on 8-factor model
        latency_ms: Execution time in milliseconds
        metadata: Optional additional information
        error: Optional error message if execution failed
    """
    value: Any
    confidence: float
    latency_ms: float
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

        # Validate confidence range
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0.0, 1.0], got {self.confidence}")

    @property
    def success(self) -> bool:
        """Check if tool execution was successful"""
        return self.error is None

    @property
    def is_high_confidence(self) -> bool:
        """Check if confidence meets trading threshold (≥0.7)"""
        return self.confidence >= 0.7


class BaseTool(ABC):
    """
    Abstract base class for all trading tools.

    All tools must implement:
    - execute(): Core logic
    - get_schema(): JSON-Schema for LLM function calling
    """

    # Class attributes (override in subclasses)
    name: str = "base_tool"
    version: str = "1.0.0"
    tier: ToolTier = ToolTier.ATOMIC
    description: str = "Base tool (override in subclass)"

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute tool logic.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            ToolResult with value, confidence, and metadata
        """
        pass

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Get JSON-Schema for LLM function calling.

        Returns:
            Dict with OpenAI function calling schema format:
            {
                "name": "tool_name",
                "description": "What this tool does",
                "parameters": {
                    "type": "object",
                    "properties": {...},
                    "required": [...]
                }
            }
        """
        pass

    def validate_inputs(self, **kwargs) -> None:
        """
        Validate input parameters.

        Raises:
            ValueError: If inputs are invalid
        """
        # Default implementation - override for custom validation
        pass

    def __str__(self) -> str:
        return f"{self.name} v{self.version} ({self.tier.value})"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"


@dataclass
class ConfidenceComponents:
    """
    8-factor confidence model components.

    Based on Tool Stack Action Plan specification.
    """
    sample_sufficiency: float  # 0.0-1.0
    volatility_regime: float  # 0.0-1.0 (low=0.7, medium=1.0, high=0.9)
    indicator_agreement: float  # 0.0-1.0
    data_quality: float  # 0.0-1.0
    liquidity_regime: float = 1.0  # 0.0-1.0 (future)
    session_factor: float = 1.0  # 0.0-1.0 (future)
    news_proximity: float = 1.0  # 0.0-1.0 (future)
    spread_anomaly: float = 1.0  # 0.0-1.0 (future)

    def calculate_confidence(self) -> float:
        """
        Calculate weighted geometric mean confidence.

        Formula (from PRD):
        confidence = (
            sample_sufficiency^0.25 *
            volatility_regime^0.15 *
            indicator_agreement^0.20 *
            data_quality^0.10 *
            liquidity_regime^0.12 *
            session_factor^0.08 *
            news_proximity^0.07 *
            spread_anomaly^0.03
        )

        Returns:
            Confidence score (0.0-1.0)
        """
        confidence = (
            self.sample_sufficiency ** 0.25 *
            self.volatility_regime ** 0.15 *
            self.indicator_agreement ** 0.20 *
            self.data_quality ** 0.10 *
            self.liquidity_regime ** 0.12 *
            self.session_factor ** 0.08 *
            self.news_proximity ** 0.07 *
            self.spread_anomaly ** 0.03
        )

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, confidence))

    def to_dict(self) -> Dict[str, float]:
        """Export components as dict for logging/debugging"""
        return {
            'sample_sufficiency': self.sample_sufficiency,
            'volatility_regime': self.volatility_regime,
            'indicator_agreement': self.indicator_agreement,
            'data_quality': self.data_quality,
            'liquidity_regime': self.liquidity_regime,
            'session_factor': self.session_factor,
            'news_proximity': self.news_proximity,
            'spread_anomaly': self.spread_anomaly,
        }


class ConfidenceCalculator:
    """
    Helper class for calculating confidence components.

    Implements heuristics from Tool Stack Action Plan.
    """

    @staticmethod
    def sample_sufficiency(actual_samples: int, required_samples: int) -> float:
        """
        Calculate sample sufficiency using sigmoid curve.

        Full confidence at 1.2x required samples.

        Args:
            actual_samples: Number of data points available
            required_samples: Minimum required for analysis

        Returns:
            Sufficiency score (0.0-1.0)
        """
        if required_samples <= 0:
            return 1.0

        ratio = actual_samples / required_samples

        # Sigmoid curve: full confidence at 1.2x
        if ratio >= 1.2:
            return 1.0
        elif ratio >= 1.0:
            # Linear interpolation 1.0-1.2 → 0.9-1.0
            return 0.9 + (ratio - 1.0) / 0.2 * 0.1
        elif ratio >= 0.8:
            # Linear interpolation 0.8-1.0 → 0.7-0.9
            return 0.7 + (ratio - 0.8) / 0.2 * 0.2
        else:
            # Below 0.8 → low confidence
            return ratio * 0.875  # 0.8 → 0.7

    @staticmethod
    def volatility_regime(volatility: float, low_threshold: float = 0.5, high_threshold: float = 2.0) -> float:
        """
        Classify volatility regime and return confidence factor.

        Low volatility (flat market) → 0.7 penalty
        Medium volatility → 1.0 (optimal)
        High volatility (breakout) → 0.9

        Args:
            volatility: Current volatility measure (e.g., ATR)
            low_threshold: Threshold for low volatility
            high_threshold: Threshold for high volatility

        Returns:
            Regime confidence factor (0.7-1.0)
        """
        if volatility < low_threshold:
            return 0.7  # Flat market penalty
        elif volatility > high_threshold:
            return 0.9  # High volatility slight penalty
        else:
            return 1.0  # Medium volatility optimal

    @staticmethod
    def indicator_agreement(indicators: Dict[str, str]) -> float:
        """
        Calculate agreement between technical indicators.

        Args:
            indicators: Dict of indicator signals, e.g.:
                {'rsi': 'bullish', 'macd': 'bullish', 'bb': 'neutral'}

        Returns:
            Agreement score (0.0-1.0)
        """
        if not indicators:
            return 0.5  # No indicators → neutral

        signals = list(indicators.values())
        bullish_count = signals.count('bullish')
        bearish_count = signals.count('bearish')
        neutral_count = signals.count('neutral')
        total = len(signals)

        # Perfect agreement (all bullish or all bearish)
        if bullish_count == total or bearish_count == total:
            return 1.0

        # Strong agreement (majority)
        majority = max(bullish_count, bearish_count)
        if majority >= total * 0.75:
            return 0.85
        elif majority >= total * 0.6:
            return 0.7
        else:
            # Mixed signals
            return 0.5

    @staticmethod
    def data_quality(gaps: int, flat_periods: int, total_bars: int) -> float:
        """
        Assess data quality based on gaps and flat periods.

        Args:
            gaps: Number of missing bars
            flat_periods: Number of periods with no price change
            total_bars: Total number of bars in dataset

        Returns:
            Quality score (0.0-1.0)
        """
        if total_bars <= 0:
            return 0.0

        gap_ratio = gaps / total_bars
        flat_ratio = flat_periods / total_bars

        # Penalize gaps and flat periods
        quality = 1.0 - (gap_ratio * 0.5 + flat_ratio * 0.3)

        return max(0.0, min(1.0, quality))
