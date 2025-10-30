"""
Confidence Calibration Module

Multi-factor confidence scoring combining technical analysis quality
with market context awareness (liquidity, session, news, spread).

Based on: INoT Deep Dive Architecture Decision #3 + GPT Enhancement
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class MarketContext:
    """
    Extended market regime profile for confidence adjustment.

    Captures real-time market conditions that affect signal reliability.
    """

    # Liquidity measures
    liquidity_regime: str  # "low" | "normal" | "high"
    volume_regime: str  # "low" | "normal" | "high"

    # Time factors
    session: str  # "asian" | "london" | "newyork" | "overlap"

    # Risk events
    news_proximity: int | None  # Minutes until major news (None if >60 min)

    # Market quality
    spread_percentile: float  # 0.0-1.0 (current spread vs 24h average)
    volatility_spike: bool  # Abnormal volatility detected


class EnhancedConfidenceCalculator:
    """
    Multi-factor confidence calculator.

    Combines:
    - Technical factors (INoT): sample, volatility, agreement, quality (70%)
    - Market context (GPT): liquidity, session, news, spread (30%)

    Formula:
        confidence = ∏(factor^weight) for all factors

    Uses geometric mean to penalize outliers (single bad factor → low confidence).
    """

    def __init__(self) -> None:
        # Weights optimized for v1.0 (empirical tuning in v1.1)
        self.weights = {
            # Technical factors (70% total)
            "sample": 0.25,
            "volatility": 0.15,
            "agreement": 0.20,
            "quality": 0.10,
            # Market context factors (30% total)
            "liquidity": 0.12,
            "session": 0.08,
            "news": 0.07,
            "spread": 0.03,
        }

    def calculate(
        self,
        # Technical factors (always required)
        sample_size: int,
        required_size: int,
        volatility_regime: str,
        indicator_agreement: float,
        data_quality: float,
        # Market context (optional)
        market_context: MarketContext | None = None,
    ) -> Any:
        """
        Calculate calibrated confidence score.

        Args:
            sample_size: Number of data points available
            required_size: Minimum required data points
            volatility_regime: "low" | "medium" | "high"
            indicator_agreement: 0.0-1.0 (how well indicators align)
            data_quality: 0.0-1.0 (gaps, flat periods penalty)
            market_context: Optional market conditions

        Returns:
            {
                "final": 0.0-1.0 overall confidence,
                "breakdown": {factor: score},
                "weights": factor weights
            }
        """
        # Technical factor scores
        tech_scores = {
            "sample": self._sample_sufficiency(sample_size, required_size),
            "volatility": self._volatility_adjustment(volatility_regime),
            "agreement": indicator_agreement,
            "quality": data_quality,
        }

        # Market context scores
        if market_context:
            context_scores = {
                "liquidity": self._liquidity_adjustment(market_context),
                "session": self._session_adjustment(market_context),
                "news": self._news_proximity_adjustment(market_context),
                "spread": self._spread_adjustment(market_context),
            }
        else:
            # No context → neutral scores
            context_scores = {"liquidity": 1.0, "session": 1.0, "news": 1.0, "spread": 1.0}

        # Combine all scores
        all_scores = {**tech_scores, **context_scores}

        # Weighted geometric mean (robust to outliers)
        final_confidence = 1.0
        for factor, score in all_scores.items():
            weight = self.weights[factor]
            final_confidence *= score**weight

        return {
            "final": round(final_confidence, 2),
            "breakdown": all_scores,
            "weights": self.weights,
        }

    # ============= Technical Factor Methods =============

    @staticmethod
    def _sample_sufficiency(n: int, required: int) -> float:
        """
        Sample size confidence using sigmoid curve.

        Full confidence at 1.2x required data.
        Inflection point at 0.8x (80% of required).
        """
        ratio = n / required
        return min(1.0, 1 / (1 + math.exp(-5 * (ratio - 0.8))))

    @staticmethod
    def _volatility_adjustment(regime: str) -> float:
        """
        Volatility regime multiplier.

        - Low: 0.7 penalty (no tradeable moves, choppy)
        - Medium: 1.0 baseline
        - High: 0.9 slight penalty (increased noise)
        """
        return {"low": 0.7, "medium": 1.0, "high": 0.9}[regime]

    # ============= Market Context Methods =============

    @staticmethod
    def _liquidity_adjustment(ctx: MarketContext) -> float:
        """
        Liquidity regime multiplier.

        Low liquidity → wider spreads, less reliable price discovery.
        High liquidity → tighter spreads, better fills.

        Reference: "High liquidity = tighter spreads = more reliable prices"
        """
        return {"low": 0.7, "normal": 1.0, "high": 1.05}[ctx.liquidity_regime]

    @staticmethod
    def _session_adjustment(ctx: MarketContext) -> float:
        """
        Trading session multiplier.

        - Asian: 0.9 (quieter, except JPY pairs)
        - London: 1.0 baseline
        - NY: 1.0 baseline
        - Overlap (London+NY): 1.05 (maximum liquidity)
        """
        return {"asian": 0.9, "london": 1.0, "newyork": 1.0, "overlap": 1.05}[ctx.session]

    @staticmethod
    def _news_proximity_adjustment(ctx: MarketContext) -> float:
        """
        Major news event proximity penalty.

        Before major news:
        - <5 min: 0.5 (severe penalty - unpredictable)
        - 5-15 min: 0.7 (high risk)
        - 15-30 min: 0.85 (moderate caution)
        - >30 min: 0.95 (minor penalty)
        - None: 1.0 (no upcoming news)

        Reference: "Before news... spreads excessively increase"
        """
        if ctx.news_proximity is None:
            return 1.0

        minutes = ctx.news_proximity
        if minutes < 5:
            return 0.5
        elif minutes < 15:
            return 0.7
        elif minutes < 30:
            return 0.85
        else:
            return 0.95

    @staticmethod
    def _spread_adjustment(ctx: MarketContext) -> float:
        """
        Spread anomaly adjustment.

        Wide spread (>70th percentile) → poor conditions.
        Tight spread (<30th percentile) → optimal execution.
        """
        pctl = ctx.spread_percentile
        if pctl > 0.9:
            return 0.8  # Very wide
        elif pctl > 0.7:
            return 0.9  # Wide
        elif pctl < 0.3:
            return 1.05  # Very tight
        else:
            return 1.0  # Normal


class MarketContextDetector:
    """
    Auto-detect market context from current conditions.

    Uses adapter methods to assess:
    - Liquidity (volume vs average)
    - Session (UTC time-based)
    - News proximity (economic calendar stub)
    - Spread conditions (current vs 24h average)
    """

    def detect(self, symbol: str, adapter) -> MarketContext:  # type: ignore
        """
        Analyze current market state for given symbol.

        Args:
            symbol: Symbol to analyze
            adapter: Broker adapter with market data access

        Returns:
            Market context profile
        """
        # Liquidity detection (volume-based)
        current_vol = adapter.get_current_volume(symbol)
        avg_vol = adapter.get_avg_volume(symbol, bars=24)

        if current_vol < avg_vol * 0.5:
            liquidity = "low"
            volume_regime = "low"
        elif current_vol > avg_vol * 1.5:
            liquidity = "high"
            volume_regime = "high"
        else:
            liquidity = "normal"
            volume_regime = "normal"

        # Session detection (UTC-based)
        session = self._detect_session(datetime.utcnow())

        # News proximity (stub for v1.0)
        news_proximity = self._check_economic_calendar(datetime.utcnow())

        # Spread analysis
        current_spread = adapter.get_symbol_info(symbol)["spread"]
        avg_spread = adapter.get_avg_spread(symbol, bars=24)
        spread_pctl = current_spread / avg_spread if avg_spread > 0 else 0.5

        # Volatility spike placeholder until ATR-based detection is implemented
        volatility_spike = False

        return MarketContext(
            liquidity_regime=liquidity,
            volume_regime=volume_regime,
            session=session,
            news_proximity=news_proximity,
            spread_percentile=min(1.0, spread_pctl),
            volatility_spike=volatility_spike,
        )

    @staticmethod
    def _detect_session(now: datetime) -> str:
        """
        Detect trading session from UTC time.

        Sessions (approximate):
        - Asian: 00:00-07:00 UTC (Tokyo open)
        - London: 07:00-12:00 UTC
        - Overlap: 12:00-16:00 UTC (London + NY)
        - NY: 16:00-21:00 UTC
        - Asian: 21:00-00:00 UTC
        """
        hour = now.hour

        if 0 <= hour < 7:
            return "asian"
        elif 7 <= hour < 12:
            return "london"
        elif 12 <= hour < 16:
            return "overlap"
        elif 16 <= hour < 21:
            return "newyork"
        else:
            return "asian"

    @staticmethod
    def _check_economic_calendar(now: datetime) -> int | None:
        """
        Check for upcoming high-impact news.

        v1.0: Stub (returns None - no calendar integration)
        v1.1: Integrate with ForexFactory/TradingEconomics API

        Returns:
            Minutes until next major news, or None if >60 min
        """
        # Placeholder until v1.1 integrates with a real calendar API provider
        return None


# ============= Utility Functions =============


def detect_volatility_regime(prices: list[float], window: int = 20) -> str:
    """
    Detect volatility regime from price series.

    Args:
        prices: Price history
        window: Rolling window for std dev

    Returns:
        "low" | "medium" | "high"
    """
    if len(prices) < window + 1:
        return "medium"  # Default if insufficient data

    # Calculate returns
    returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]

    # Rolling std dev
    rolling_std = []
    for i in range(window, len(returns)):
        window_returns = returns[i - window : i]
        std = math.sqrt(
            sum((r - sum(window_returns) / len(window_returns)) ** 2 for r in window_returns)
            / len(window_returns)
        )
        rolling_std.append(std)

    if not rolling_std:
        return "medium"

    # Current std vs median (baseline)
    current_std = rolling_std[-1]
    median_std = sorted(rolling_std)[len(rolling_std) // 2]

    if current_std < median_std * 0.6:
        return "low"
    elif current_std > median_std * 1.4:
        return "high"
    else:
        return "medium"


def calculate_indicator_agreement(rsi: float, macd_hist: float, bb_position: float) -> float:
    """
    Calculate agreement score between technical indicators.

    Args:
        rsi: RSI value (0-100)
        macd_hist: MACD histogram (positive = bullish)
        bb_position: Bollinger Band position (-1 to +1)

    Returns:
        Agreement score (0.0-1.0)

    1.0 = perfect alignment (all bullish or all bearish)
    0.5 = neutral/mixed signals
    0.0 = complete disagreement
    """
    # Normalize indicators to -1 (bearish) to +1 (bullish)
    rsi_signal = (rsi - 50) / 50
    macd_signal = math.tanh(macd_hist * 10)  # Squash to -1..1
    bb_signal = bb_position

    signals = [rsi_signal, macd_signal, bb_signal]

    # Calculate pairwise agreement
    pairwise = []
    for i in range(len(signals)):
        for j in range(i + 1, len(signals)):
            distance = abs(signals[i] - signals[j]) / 2  # Max distance = 2
            agreement = 1 - distance
            pairwise.append(agreement)

    # Average pairwise agreement
    return sum(pairwise) / len(pairwise) if pairwise else 0.5


def assess_data_quality(prices: list[float]) -> float:
    """
    Assess price data quality.

    Checks for:
    - Large gaps (>5% jumps)
    - Flat periods (0 movement for >3 bars)
    - Missing data

    Returns:
        Quality score (0.0-1.0)
    """
    if not prices or len(prices) < 4:
        return 0.5  # Insufficient data

    score = 1.0

    # Check for large gaps
    returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]
    large_gaps = sum(1 for r in returns if abs(r) > 0.05)
    score -= large_gaps * 0.1

    # Check for flat periods
    flat_count = sum(
        1 for i in range(3, len(prices)) if prices[i] == prices[i - 1] == prices[i - 2]
    )
    score -= flat_count * 0.05

    # Check for None/NaN (if applicable)
    if None in prices or any(p != p for p in prices):  # NaN check
        score -= 0.3

    return max(0.0, score)
