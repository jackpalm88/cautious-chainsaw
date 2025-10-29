"""
LLM Orchestration Module

Hybrid orchestration supporting both passive (user-driven)
and active (autonomous multi-tool) modes.

Based on: INoT Deep Dive Architecture Decision #2
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any


class OrchestrationMode(Enum):
    """Tool orchestration modes"""

    PASSIVE = "passive"  # Single tool, user-specified
    ACTIVE = "active"  # Multi-tool chain, autonomous
    HYBRID = "hybrid"  # Context-dependent (default)


@dataclass
class ToolCallResult:
    """Result from a single tool execution"""

    tool_name: str
    success: bool
    value: Any
    confidence: float
    latency_ms: float
    error: str | None = None
    meta: dict | None = None


@dataclass
class ChainExecutionResult:
    """Result from multi-tool chain execution"""

    success: bool
    mode: OrchestrationMode
    chain_length: int
    execution_time: float
    results: list[ToolCallResult]
    final_recommendation: str
    final_confidence: float
    abort_reason: str | None = None


class QueryClassifier:
    """
    Classify user queries to determine orchestration mode.

    v1.0: Rule-based heuristics
    v1.1: Upgrade to LLM-based intent detection
    """

    PASSIVE_TRIGGERS = [
        # Explicit tool requests
        "what is",
        "calculate",
        "show me",
        "display",
        "tell me",
        # Specific indicators
        "rsi",
        "macd",
        "bollinger",
        "spread",
        "price",
    ]

    ACTIVE_TRIGGERS = [
        # Strategic questions
        "should i",
        "can i",
        "is it good to",
        # Analysis requests
        "analyze",
        "find",
        "recommend",
        "suggest",
        # Trading actions
        "trade",
        "buy",
        "sell",
        "short",
        "long",
        "opportunity",
        "entry",
        "signal",
    ]

    @classmethod
    def classify(cls, query: str) -> OrchestrationMode:
        """
        Classify query intent.

        Args:
            query: User query string

        Returns:
            Orchestration mode (PASSIVE, ACTIVE, or HYBRID)
        """
        query_lower = query.lower()

        # Check passive triggers
        if any(trigger in query_lower for trigger in cls.PASSIVE_TRIGGERS):
            return OrchestrationMode.PASSIVE

        # Check active triggers
        if any(trigger in query_lower for trigger in cls.ACTIVE_TRIGGERS):
            return OrchestrationMode.ACTIVE

        # Default: HYBRID (let orchestrator decide based on context)
        return OrchestrationMode.HYBRID


class ToolChainOrchestrator:
    """
    Execute multi-tool workflows with safety limits.

    Manages:
    - Tool call sequencing
    - Early abort conditions
    - Timeout protection
    - Result aggregation
    """

    MAX_CHAIN_LENGTH = 4  # Maximum tools per query
    MAX_EXECUTION_TIME = 10.0  # Seconds
    CONFIDENCE_THRESHOLD = 0.7  # Minimum to proceed

    def __init__(self, registry, bridge) -> None:  # type: ignore
        """
        Args:
            registry: ToolRegistry with available tools
            bridge: ExecutionBridge for market data access
        """
        self.registry = registry
        self.bridge = bridge
        self.execution_log: list[ToolCallResult] = []

    def execute_chain(
        self, query: str, symbol: str, user_params: dict[str, Any]
    ) -> ChainExecutionResult:
        """
        Execute autonomous tool chain for strategic queries.

        Standard flow:
        1. technical_overview(prices) → validate confidence
        2. IF confidence < 0.7 → ABORT
        3. get_symbol_info(symbol) → check spread
        4. IF spread > max → ABORT
        5. risk_fixed_fractional(...) → calculate position
        6. generate_order(...) → propose trade

        Args:
            query: User query (for context)
            symbol: Symbol to analyze
            user_params: User preferences (risk_pct, max_spread, etc.)

        Returns:
            Chain execution result with recommendation
        """
        start_time = time.time()
        self.execution_log = []

        try:
            # Step 1: Technical Analysis (MANDATORY)
            tech_result = self._execute_technical_overview(symbol)

            if not tech_result.success:
                return self._error_response(
                    "technical_analysis_failed", tech_result.error, start_time
                )

            # Early abort check
            if tech_result.confidence < self.CONFIDENCE_THRESHOLD:
                return self._abort_response(
                    reason="low_technical_confidence",
                    message=f"Technical confidence {tech_result.confidence:.2f} is below {self.CONFIDENCE_THRESHOLD} threshold. Recommend waiting for clearer signal.",
                    start_time=start_time,
                )

            # Step 2: Market Conditions Check
            if time.time() - start_time > self.MAX_EXECUTION_TIME:
                return self._timeout_response(start_time)

            spread_result = self._check_spread(symbol, user_params)
            if not spread_result.success:
                return self._abort_response(
                    reason="spread_too_wide",
                    message=spread_result.error or "Spread check failed",
                    start_time=start_time,
                )

            # Step 3: Risk Calculation
            if time.time() - start_time > self.MAX_EXECUTION_TIME:
                return self._timeout_response(start_time)

            risk_result = self._calculate_risk(symbol, user_params, tech_result)

            if not risk_result.success:
                return self._error_response(
                    "risk_calculation_failed", risk_result.error, start_time
                )

            # Step 4: Order Generation
            if time.time() - start_time > self.MAX_EXECUTION_TIME:
                return self._timeout_response(start_time)

            order_result = self._generate_order(symbol, user_params, tech_result, risk_result)

            if not order_result.success:
                return self._error_response(
                    "order_generation_failed", order_result.error, start_time
                )

            # Success: Return comprehensive analysis
            return ChainExecutionResult(
                success=True,
                mode=OrchestrationMode.ACTIVE,
                chain_length=len(self.execution_log),
                execution_time=time.time() - start_time,
                results=self.execution_log,
                final_recommendation=self._format_recommendation(
                    tech_result, risk_result, order_result
                ),
                final_confidence=min(
                    tech_result.confidence, risk_result.confidence, order_result.confidence
                ),
            )

        except Exception as e:
            return self._error_response("chain_execution_error", str(e), start_time)

    # ============= Internal Chain Steps =============

    def _execute_technical_overview(self, symbol: str) -> ToolCallResult:
        """Execute technical analysis"""
        t0 = time.time()

        try:
            # Get price history
            prices = self.bridge.adapter.get_price_history(symbol, "H1", 200)

            # Call technical_overview tool
            tech_tool = self.registry.get("technical_overview")
            result = tech_tool.execute(prices=prices, symbol=symbol, adapter=self.bridge.adapter)

            tool_result = ToolCallResult(
                tool_name="technical_overview",
                success=True,
                value=result["value"],
                confidence=result["confidence"],
                latency_ms=(time.time() - t0) * 1000,
                meta=result.get("meta"),
            )

            self.execution_log.append(tool_result)
            return tool_result

        except Exception as e:
            return ToolCallResult(
                tool_name="technical_overview",
                success=False,
                value=None,
                confidence=0.0,
                latency_ms=(time.time() - t0) * 1000,
                error=str(e),
            )

    def _check_spread(self, symbol: str, user_params: dict) -> ToolCallResult:
        """Check if spread is acceptable"""
        t0 = time.time()

        try:
            symbol_info = self.bridge.adapter.get_symbol_info(symbol)
            current_spread = symbol_info["spread"]
            max_spread = user_params.get("max_spread", 30)

            success = current_spread <= max_spread
            error = (
                None
                if success
                else f"Spread {current_spread} pips exceeds maximum {max_spread} pips"
            )

            tool_result = ToolCallResult(
                tool_name="check_spread",
                success=success,
                value={"current": current_spread, "max": max_spread},
                confidence=1.0 if success else 0.0,
                latency_ms=(time.time() - t0) * 1000,
                error=error,
            )

            self.execution_log.append(tool_result)
            return tool_result

        except Exception as e:
            return ToolCallResult(
                tool_name="check_spread",
                success=False,
                value=None,
                confidence=0.0,
                latency_ms=(time.time() - t0) * 1000,
                error=str(e),
            )

    def _calculate_risk(
        self, symbol: str, user_params: dict, tech_result: ToolCallResult
    ) -> ToolCallResult:
        """Calculate position size"""
        t0 = time.time()

        try:
            account = self.bridge.adapter.get_account_info()
            risk_tool = self.registry.get("risk_fixed_fractional")

            # Derive SL from technical analysis or use user default
            sl_pips = user_params.get("sl_pips", 20)

            result = risk_tool.execute(
                balance=account["balance"],
                risk_pct=user_params.get("risk_pct", 0.01),
                sl_pips=sl_pips,
                symbol=symbol,
            )

            tool_result = ToolCallResult(
                tool_name="risk_fixed_fractional",
                success=True,
                value=result["value"],
                confidence=result["confidence"],
                latency_ms=(time.time() - t0) * 1000,
                meta=result.get("meta"),
            )

            self.execution_log.append(tool_result)
            return tool_result

        except Exception as e:
            return ToolCallResult(
                tool_name="risk_fixed_fractional",
                success=False,
                value=None,
                confidence=0.0,
                latency_ms=(time.time() - t0) * 1000,
                error=str(e),
            )

    def _generate_order(
        self,
        symbol: str,
        user_params: dict,
        tech_result: ToolCallResult,
        risk_result: ToolCallResult,
    ) -> ToolCallResult:
        """Generate order proposal"""
        t0 = time.time()

        try:
            order_tool = self.registry.get("generate_order")

            # Derive direction from technical analysis
            direction = self._derive_direction(tech_result.value)

            result = order_tool.execute(
                symbol=symbol,
                direction=direction,
                risk_pct=user_params.get("risk_pct", 0.01),
                sl_pips=user_params.get("sl_pips", 20),
                tp_pips=user_params.get("tp_pips", 40),
                max_spread=user_params.get("max_spread", 30),
            )

            tool_result = ToolCallResult(
                tool_name="generate_order",
                success=True,
                value=result["value"],
                confidence=result["confidence"],
                latency_ms=(time.time() - t0) * 1000,
                meta=result.get("meta"),
            )

            self.execution_log.append(tool_result)
            return tool_result

        except Exception as e:
            return ToolCallResult(
                tool_name="generate_order",
                success=False,
                value=None,
                confidence=0.0,
                latency_ms=(time.time() - t0) * 1000,
                error=str(e),
            )

    # ============= Helper Methods =============

    @staticmethod
    def _derive_direction(tech_value: dict) -> str:
        """Infer trade direction from technical analysis"""
        interp = tech_value.get("interpretation", {})
        macd_signal = interp.get("macd_signal", "neutral")
        rsi_signal = interp.get("rsi_signal", "neutral")

        if macd_signal == "bullish" and rsi_signal != "overbought":
            return "long"
        elif macd_signal == "bearish" and rsi_signal != "oversold":
            return "short"
        else:
            return "hold"

    @staticmethod
    def _format_recommendation(
        tech_result: ToolCallResult, risk_result: ToolCallResult, order_result: ToolCallResult
    ) -> str:
        """Format final recommendation message"""
        direction = order_result.value.get("order", {}).get("direction", "unknown")
        position = risk_result.value
        confidence = tech_result.confidence

        return f"""Technical setup favorable for {direction.upper()} (confidence: {confidence:.2f}).

Position: {position} lots
Technical: RSI {tech_result.value.get("rsi", "N/A")}, MACD {tech_result.value.get("macd_signal", "N/A")}

Recommendation: Review order details and confirm to execute."""

    def _abort_response(self, reason: str, message: str, start_time: float) -> ChainExecutionResult:
        """Create abort response"""
        return ChainExecutionResult(
            success=False,
            mode=OrchestrationMode.ACTIVE,
            chain_length=len(self.execution_log),
            execution_time=time.time() - start_time,
            results=self.execution_log,
            final_recommendation=message,
            final_confidence=0.0,
            abort_reason=reason,
        )

    def _error_response(
        self, reason: str, error: str | None, start_time: float
    ) -> ChainExecutionResult:
        """Create error response"""
        return ChainExecutionResult(
            success=False,
            mode=OrchestrationMode.ACTIVE,
            chain_length=len(self.execution_log),
            execution_time=time.time() - start_time,
            results=self.execution_log,
            final_recommendation=f"Execution failed: {error or 'Unknown error'}",
            final_confidence=0.0,
            abort_reason=reason,
        )

    def _timeout_response(self, start_time: float) -> ChainExecutionResult:
        """Create timeout response"""
        return ChainExecutionResult(
            success=False,
            mode=OrchestrationMode.ACTIVE,
            chain_length=len(self.execution_log),
            execution_time=time.time() - start_time,
            results=self.execution_log,
            final_recommendation=f"Chain execution exceeded {self.MAX_EXECUTION_TIME}s timeout. Retry with simpler query or check system performance.",
            final_confidence=0.0,
            abort_reason="execution_timeout",
        )
