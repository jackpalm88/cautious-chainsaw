"""
Trading Decision Engine with INoT Integration
Combines tool stack with INoT multi-agent reasoning
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..inot_engine.orchestrator import Decision

from ..inot_engine import ConfidenceCalibrator, INoTOrchestrator, INoTValidator
from ..tools import (
    CalcBollingerBands,
    CalcMACD,
    CalcRSI,
    RiskFixedFractional,
    TechnicalOverview,
)


@dataclass
class FusedContext:
    """
    Unified market context for decision-making.
    Combines technical indicators, market data, and risk parameters.
    """
    # Symbol and price
    symbol: str
    price: float
    timestamp: datetime = field(default_factory=datetime.now)

    # Technical indicators (from tools)
    rsi: float | None = None
    rsi_signal: str | None = None

    macd: float | None = None
    macd_signal_line: float | None = None
    macd_histogram: float | None = None
    macd_signal: str | None = None

    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    bb_position: float | None = None
    bb_signal: str | None = None

    # Composite analysis
    technical_signal: str | None = None
    technical_confidence: float | None = None
    agreement_score: float | None = None

    # Market data
    atr: float | None = None
    volume: int | None = None
    spread: float | None = None

    # News and sentiment (future)
    latest_news: str | None = None
    sentiment: float | None = None

    # Account state
    current_position: str | None = None
    unrealized_pnl: float | None = None
    account_equity: float | None = None
    free_margin: float | None = None

    # Risk parameters
    risk_percent: float = 1.0
    stop_loss_pips: float | None = None

    # Market context (from MarketContext tool)
    regime: str | None = None  # trending, ranging, volatile
    volatility: float | None = None  # ATR value
    volatility_normalized: float | None = None
    trend_strength: float | None = None  # 0.0-1.0

    # Complexity indicators
    has_major_news: bool = False
    market_volatility: str | None = None  # Deprecated: use 'regime' instead


@dataclass
class MemorySnapshot:
    """
    Read-only memory snapshot for INoT reasoning.
    Contains recent decisions and performance stats.
    """
    recent_decisions: list[dict] = field(default_factory=list)
    current_regime: str | None = None
    win_rate_30d: float | None = None
    avg_win_pips: float | None = None
    avg_loss_pips: float | None = None
    total_trades_30d: int | None = None

    def to_summary(self, max_tokens: int = 500) -> str:
        """Convert memory to text summary for LLM prompt"""
        lines = ["## Recent Decisions"]

        for decision in self.recent_decisions[:5]:  # Last 5
            timestamp = decision.get('timestamp', 'N/A')
            action = decision.get('action', 'N/A')
            outcome = decision.get('outcome', 'N/A')
            reason = decision.get('reason', 'N/A')
            lines.append(f"- {timestamp}: {action}, outcome: {outcome}, reason: {reason}")

        if not self.recent_decisions:
            lines.append("- No recent decisions")

        lines.append(f"\n## Current Regime: {self.current_regime or 'unknown'}")
        lines.append("\n## 30-Day Stats")
        lines.append(f"- Win rate: {self.win_rate_30d * 100:.1f}%" if self.win_rate_30d else "- Win rate: N/A")
        lines.append(f"- Avg win: {self.avg_win_pips:.1f} pips" if self.avg_win_pips else "- Avg win: N/A")
        lines.append(f"- Avg loss: {self.avg_loss_pips:.1f} pips" if self.avg_loss_pips else "- Avg loss: N/A")
        lines.append(f"- Total trades: {self.total_trades_30d}" if self.total_trades_30d else "- Total trades: N/A")

        return "\n".join(lines)


class TradingDecisionEngine:
    """
    Main trading decision engine with INoT integration.

    Architecture:
    - Tool Stack: Atomic + Composite + Execution tools
    - INoT Layer: Multi-agent reasoning (optional)
    - Calibration: Confidence adjustment

    Flow:
    1. Calculate technical indicators (tools)
    2. Build FusedContext
    3. INoT reasoning (if enabled)
    4. Execute order (if decision made)
    """

    def __init__(self, config: dict):
        """
        Initialize decision engine.

        Args:
            config: Configuration dict with keys:
                - inot: INoT config (optional)
                - tools: Tool config
                - risk: Risk management config
        """
        self.config = config

        # Initialize tool stack
        self._init_tools(config.get("tools", {}))

        # Initialize INoT (optional)
        self.inot = None
        self.calibrator = None
        if config.get("inot", {}).get("enabled", False):
            self._init_inot(config["inot"])

        # Memory (simple in-memory for now)
        self.memory = MemorySnapshot()

    def _init_tools(self, tools_config: dict):
        """Initialize tool stack"""
        # Atomic tools
        self.rsi_tool = CalcRSI(period=tools_config.get("rsi_period", 14))
        self.macd_tool = CalcMACD(
            fast_period=tools_config.get("macd_fast", 12),
            slow_period=tools_config.get("macd_slow", 26),
            signal_period=tools_config.get("macd_signal", 9)
        )
        self.bb_tool = CalcBollingerBands(
            period=tools_config.get("bb_period", 20),
            std_multiplier=tools_config.get("bb_std", 2.0)
        )
        self.risk_tool = RiskFixedFractional()

        # Composite tool
        self.technical_overview = TechnicalOverview()

        # Execution tool (requires bridge)
        self.generate_order = None  # Set externally with bridge

        print("✅ Tool stack initialized")

    def _init_inot(self, inot_config: dict):
        """Initialize INoT components"""
        # Validator
        schema_path = Path(__file__).parent.parent / "inot_engine" / "schemas" / "inot_agents.schema.json"
        validator = INoTValidator(schema_path=schema_path)

        # LLM client (mock for now, replace with real client)
        llm_client = self._create_mock_llm_client()

        # Orchestrator
        self.inot = INoTOrchestrator(
            llm_client=llm_client,
            config=inot_config,
            validator=validator
        )

        # Calibrator
        calibration_path = Path(inot_config.get("calibration_path", "data/inot_calibration.json"))
        calibration_path.parent.mkdir(parents=True, exist_ok=True)
        self.calibrator = ConfidenceCalibrator(storage_path=calibration_path)

        print("✅ INoT Engine initialized")

    def _create_mock_llm_client(self):
        """Create mock LLM client for testing"""
        class MockLLM:
            def complete(self, prompt, **kwargs):
                """Mock LLM completion"""
                class Response:
                    content = """[
  {
    "agent": "Signal",
    "action": "BUY",
    "confidence": 0.75,
    "reasoning": "RSI oversold at 28, MACD bullish crossover forming",
    "key_factors": ["RSI oversold", "MACD bullish crossover"],
    "memory_reference": "Similar to previous successful setup"
  },
  {
    "agent": "Risk",
    "approved": true,
    "confidence": 0.70,
    "position_size_adjustment": 0.5,
    "stop_loss_required": true,
    "reasoning": "Approve with 50% size due to moderate volatility"
  },
  {
    "agent": "Context",
    "regime": "trending",
    "regime_confidence": 0.75,
    "signal_regime_fit": 0.80,
    "news_alignment": "neutral",
    "weight_adjustment": 1.0,
    "reasoning": "Trending market favors momentum strategies"
  },
  {
    "agent": "Synthesis",
    "final_decision": {
      "action": "BUY",
      "lots": 0.05,
      "stop_loss": 1.0835,
      "confidence": 0.68
    },
    "reasoning_synthesis": "Consensus BUY with reduced risk due to volatility",
    "agent_weights_applied": {"Signal": 0.75, "Risk": 0.5, "Context": 1.0},
    "memory_update_intent": "RSI<30 in trending regime"
  }
]"""
                    usage = {"input_tokens": 3000, "output_tokens": 800}

                return Response()

        return MockLLM()

    def analyze_market(self, symbol: str, prices: list[float]) -> FusedContext:
        """
        Analyze market using tool stack.

        Args:
            symbol: Trading symbol
            prices: Historical prices

        Returns:
            FusedContext with technical analysis
        """
        # Calculate technical indicators
        rsi_result = self.rsi_tool.execute(prices=prices)
        macd_result = self.macd_tool.execute(prices=prices)
        bb_result = self.bb_tool.execute(prices=prices)

        # Get composite analysis
        tech_result = self.technical_overview.execute(prices=prices)

        # Build fused context
        context = FusedContext(
            symbol=symbol,
            price=prices[-1],
            timestamp=datetime.now(),

            # RSI
            rsi=rsi_result.value.get('rsi') if rsi_result.value else None,
            rsi_signal=rsi_result.value.get('signal') if rsi_result.value else None,

            # MACD
            macd=macd_result.value.get('macd') if macd_result.value else None,
            macd_signal_line=macd_result.value.get('signal_line') if macd_result.value else None,
            macd_histogram=macd_result.value.get('histogram') if macd_result.value else None,
            macd_signal=macd_result.value.get('signal') if macd_result.value else None,

            # Bollinger Bands
            bb_upper=bb_result.value.get('upper_band') if bb_result.value else None,
            bb_middle=bb_result.value.get('middle_band') if bb_result.value else None,
            bb_lower=bb_result.value.get('lower_band') if bb_result.value else None,
            bb_position=bb_result.value.get('position') if bb_result.value else None,
            bb_signal=bb_result.value.get('signal') if bb_result.value else None,

            # Technical overview
            technical_signal=tech_result.value.get('signal') if tech_result.value else None,
            technical_confidence=tech_result.confidence,
            agreement_score=tech_result.value.get('agreement_score') if tech_result.value else None,

            # Placeholder values (to be filled by real data)
            atr=0.0015,
            volume=1000,
            account_equity=10000.0,
            free_margin=9000.0,
        )

        return context

    def decide(self, context: FusedContext) -> Optional['Decision']:
        """
        Make trading decision.

        Args:
            context: Market context

        Returns:
            Decision object or None if no action
        """
        # Use INoT if enabled
        if self.inot and self._should_use_inot(context):
            try:
                decision = self.inot.reason(context, self.memory)

                # Apply calibration
                if self.calibrator:
                    decision.confidence = self.calibrator.apply_calibration(
                        decision.confidence
                    )

                print(f"🧠 INoT decision: {decision.action} (conf: {decision.confidence:.2f})")
                return decision

            except Exception as e:
                print(f"⚠️  INoT failed: {e}, falling back to rules")

        # Fallback: Simple rule-based decision
        return self._rule_based_decision(context)

    def _should_use_inot(self, context: FusedContext) -> bool:
        """Decide if INoT reasoning is worth the cost"""
        # Always use INoT if enabled (for now)
        return True

    def _rule_based_decision(self, context: FusedContext):
        """Simple rule-based fallback"""
        from ..inot_engine.orchestrator import Decision

        # Simple RSI-based rule
        if context.rsi and context.rsi < 30:
            return Decision(
                action="BUY",
                lots=0.01,
                confidence=0.5,
                reasoning="RSI oversold (fallback rule)"
            )
        elif context.rsi and context.rsi > 70:
            return Decision(
                action="SELL",
                lots=0.01,
                confidence=0.5,
                reasoning="RSI overbought (fallback rule)"
            )
        else:
            return Decision(
                action="HOLD",
                lots=0.0,
                confidence=0.3,
                reasoning="No clear signal (fallback rule)"
            )
