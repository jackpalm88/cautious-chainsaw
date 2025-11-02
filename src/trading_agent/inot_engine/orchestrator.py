"""
INoT Orchestrator with Hard Veto Enforcement

Production-ready INoT reasoning engine with:
- Risk hard veto (overrides all agents)
- Confidence calibration tracking
- Deterministic execution (temperature=0)
- Token budget enforcement
- Golden test compatibility
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .validator import INoTValidator, create_remediation_prompt

if TYPE_CHECKING:
    from ..decision.engine import FusedContext, MemorySnapshot


@dataclass
class Decision:
    """Final trading decision"""

    action: str  # BUY, SELL, HOLD, CLOSE
    lots: float
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    confidence: float = 0.0
    reasoning: str = ""

    # Metadata
    timestamp: datetime = None
    agent_outputs: list[dict] = None
    vetoed: bool = False
    veto_reason: str | None = None


class INoTOrchestrator:
    """
    INoT Multi-Agent Trading Decision Engine

    Key features:
    - Single-completion multi-agent reasoning
    - Risk hard veto enforcement (safety first)
    - Strict JSON validation with auto-remediation
    - Deterministic execution for backtesting
    """

    def __init__(
        self,
        llm_client,  # LLM API client (e.g., Anthropic, OpenAI)
        config: dict,
        validator: INoTValidator,
    ):
        self.llm = llm_client
        self.config = config
        self.validator = validator

        # Fixed parameters for determinism
        self.model_version = config.get("model_version", "claude-sonnet-4-20250514")
        self.temperature = config.get("temperature", 0.0)  # Deterministic
        self.max_tokens = config.get("max_tokens", 4000)

        # Calibration tracking
        self.calibration_data = []

        # Cost tracking
        self.daily_cost = 0.0
        self.daily_decisions = 0

    def reason(self, context: 'FusedContext', memory: 'MemorySnapshot') -> Decision:
        """
        Execute INoT multi-agent reasoning.

        Flow:
        1. Build prompt with context + memory
        2. LLM single-completion (all 4 agents)
        3. Validate & auto-remediate if needed
        4. Enforce Risk hard veto
        5. Return decision

        Args:
            context: Current market data (FusedContext)
            memory: Read-only memory snapshot

        Returns:
            Decision object (may be HOLD if vetoed)
        """
        # Step 1: Build INoT prompt
        prompt = self._build_inot_prompt(context, memory)

        # Step 2: LLM completion
        try:
            llm_output = self._call_llm(prompt)
        except Exception as e:
            # LLM failure → failsafe HOLD
            return Decision(
                action="HOLD",
                lots=0.0,
                confidence=0.0,
                reasoning=f"LLM call failed: {e}",
                timestamp=datetime.now(),
            )

        # Step 3: Validate with auto-remediation
        validation_result = self.validator.validate(llm_output)

        if not validation_result.valid:
            # Remediation failed → try one LLM self-correction
            correction_prompt = create_remediation_prompt(validation_result.errors, llm_output)

            try:
                corrected_output = self._call_llm(correction_prompt)
                validation_result = self.validator.validate(corrected_output)
            except Exception:
                pass  # Give up, return failsafe

            if not validation_result.valid:
                return Decision(
                    action="HOLD",
                    lots=0.0,
                    confidence=0.0,
                    reasoning=f"Validation failed: {validation_result.errors}",
                    timestamp=datetime.now(),
                )

        agents = validation_result.agents

        # Step 4: Extract agents
        agents[0]
        risk_agent = agents[1]
        agents[2]
        synthesis_agent = agents[3]

        # Step 5: RISK HARD VETO ENFORCEMENT
        if not risk_agent.get("approved", True):
            veto_reason = risk_agent.get("veto_reason", "Risk veto (no reason given)")

            return Decision(
                action="HOLD",
                lots=0.0,
                confidence=risk_agent.get("confidence", 1.0),
                reasoning=f"RISK VETO: {veto_reason}",
                timestamp=datetime.now(),
                agent_outputs=agents,
                vetoed=True,
                veto_reason=veto_reason,
            )

        # Step 6: Extract final decision from Synthesis
        final = synthesis_agent.get("final_decision", {})

        decision = Decision(
            action=final.get("action", "HOLD"),
            lots=final.get("lots", 0.0),
            entry_price=final.get("entry_price"),
            stop_loss=final.get("stop_loss"),
            take_profit=final.get("take_profit"),
            confidence=final.get("confidence", 0.0),
            reasoning=synthesis_agent.get("reasoning_synthesis", ""),
            timestamp=datetime.now(),
            agent_outputs=agents,
            vetoed=False,
        )

        # Step 7: Business rule: If Risk requires SL, enforce it
        if risk_agent.get("stop_loss_required", False):
            if not decision.stop_loss:
                # Override to HOLD if SL missing
                decision.action = "HOLD"
                decision.lots = 0.0
                decision.reasoning = "SYSTEM VETO: Risk requires stop-loss but none provided"
                decision.vetoed = True

        # Step 8: Track for calibration
        self._track_decision(decision)

        return decision

    def _build_inot_prompt(self, context: 'FusedContext', memory: 'MemorySnapshot') -> str:
        """
        Build complete INoT multi-agent prompt.

        Token budget enforcement:
        - Context: ~500-800 tokens
        - Memory summary: ≤1000 tokens
        - Agent instructions: ~1500 tokens
        - Total: ~3000-3500 tokens input
        """
        # Memory summary with reduced token budget (optimization)
        memory_summary = memory.to_summary(max_tokens=600)

        # Build prompt (full template from INoT Deep Dive)
        prompt = f"""
# Multi-Agent Trading Decision Framework

You will analyze the market context from 4 specialized perspectives, then synthesize a final decision.

## Current Market Context
**Symbol:** {context.symbol}
**Price:** {context.price}
**Timestamp:** {context.timestamp}

**Technical Indicators:**
- RSI(14): {context.rsi:.1f}
- MACD: {context.macd:.4f} (Signal: {context.macd_signal:.4f})
- ATR: {context.atr:.5f}
- Volume: {context.volume}

**News & Sentiment:**
- Latest news: "{context.latest_news[:120]}..."
- Sentiment: {context.sentiment:+.1f}

**Position Status:**
- Current position: {context.current_position or 'FLAT'}
- Unrealized P&L: {context.unrealized_pnl:+.2f} pips
- Account equity: ${context.account_equity:.2f}
- Free margin: ${context.free_margin:.2f}

## Memory (Past Decisions & Performance)
{memory_summary}

---

## 🎯 Agent Analysis Phase

Execute the following agent reasoning IN ORDER. Output ONLY valid JSON array with 4 objects.

### Agent_Signal (Technical Analyst)
Analyze technical indicators and identify trading signal.

Output:
{{
  "agent": "Signal",
  "action": "BUY" | "SELL" | "HOLD",
  "confidence": 0.0-1.0,
  "reasoning": "Why this signal (40-500 chars)",
  "key_factors": ["factor1", "factor2", ...],  // 1-5 items
  "memory_reference": "Similar to past setup X" // optional
}}

### Agent_Risk (Risk Manager)
Validate signal against risk parameters. Can VETO if risk exceeds limits.

Output:
{{
  "agent": "Risk",
  "approved": true | false,
  "confidence": 0.0-1.0,
  "position_size_adjustment": 0.0-2.0,  // 0=no trade, 0.5=half, 1.0=full
  "stop_loss_required": true | false,
  "reasoning": "Risk assessment (40-500 chars)",
  "veto_reason": null | "Why blocked (if approved=false)",
  "memory_reference": "Similar risk scenario" // optional
}}

### Agent_Context (Macro Analyst)
Evaluate market regime and news impact.

Output:
{{
  "agent": "Context",
  "regime": "trending_bullish" | "trending_bearish" | "ranging" | "volatile_uncertain",
  "regime_confidence": 0.0-1.0,
  "signal_regime_fit": 0.0-1.0,  // How well signal fits regime
  "news_alignment": "supporting" | "neutral" | "conflicting",
  "weight_adjustment": 0.5-1.5,  // Multiplier for Signal weight
  "reasoning": "Context analysis (40-500 chars)",
  "memory_reference": "Regime performance history" // optional
}}

### Agent_Synthesis (Decision Integrator)
Combine all perspectives into final executable decision.

Output:
{{
  "agent": "Synthesis",
  "final_decision": {{
    "action": "BUY" | "SELL" | "HOLD" | "CLOSE",
    "lots": 0.0-10.0,
    "entry_price": null | float,
    "stop_loss": null | float,  // REQUIRED if Risk.stop_loss_required=true
    "take_profit": null | float,
    "confidence": 0.0-1.0
  }},
  "reasoning_synthesis": "Integrated explanation (100-800 chars)",
  "agent_weights_applied": {{"Signal": 0.0-2.0, "Risk": 0.0-2.0, "Context": 0.0-2.0}},
  "conflict_resolution": null | "How conflicts resolved",
  "memory_update_intent": "What to remember from this decision"
}}

---

## CRITICAL INSTRUCTIONS
1. Output ONLY a JSON array with 4 objects (no markdown, no explanation)
2. Agent order: Signal, Risk, Context, Synthesis
3. If Risk.approved=false, MUST provide veto_reason
4. If Risk.stop_loss_required=true, Synthesis MUST provide stop_loss
5. All confidence values 0.0-1.0
6. Reasoning fields: 40-500 chars (Signal/Risk/Context), 100-800 chars (Synthesis)

Return JSON array now:
"""

        return prompt

    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM with deterministic settings.

        Fixed parameters:
        - temperature=0.0 (determinism)
        - model version locked
        - max_tokens budget
        """
        response = self.llm.complete(
            prompt=prompt,
            model=self.model_version,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        # Track cost
        self.daily_cost += self._estimate_cost(response)
        self.daily_decisions += 1

        return response.content

    def _estimate_cost(self, response) -> float:
        """Estimate API cost for tracking"""
        # Claude Sonnet 4 pricing (approximate)
        input_tokens = response.usage.get("input_tokens", 3000)
        output_tokens = response.usage.get("output_tokens", 1000)

        # $3 per 1M input, $15 per 1M output (example rates)
        cost = (input_tokens / 1_000_000 * 3.0) + (output_tokens / 1_000_000 * 15.0)

        return cost

    def _track_decision(self, decision: Decision):
        """Track decision for calibration analysis"""
        self.calibration_data.append(
            {
                "timestamp": decision.timestamp,
                "confidence": decision.confidence,
                "action": decision.action,
                # Outcome filled in later when position closes
                "outcome": None,
                "pnl": None,
            }
        )

    def update_outcome(self, decision_id: str, outcome: str, pnl: float):
        """Update decision outcome for calibration"""
        # Find decision in calibration data and update
        # This enables confidence calibration analysis
        pass  # Implementation depends on storage backend


# Example usage
if __name__ == "__main__":
    from validator import INoTValidator

    # Mock LLM client for testing
    class MockLLM:
        def complete(self, prompt, **kwargs):
            # Return mock agent outputs
            class MockResponse:
                content = """[
                  {"agent": "Signal", "action": "BUY", "confidence": 0.7, "reasoning": "RSI oversold", "key_factors": ["RSI"]},
                  {"agent": "Risk", "approved": true, "confidence": 0.8, "position_size_adjustment": 1.0, "stop_loss_required": true, "reasoning": "Risk acceptable"},
                  {"agent": "Context", "regime": "ranging", "regime_confidence": 0.75, "signal_regime_fit": 0.8, "news_alignment": "neutral", "weight_adjustment": 1.0, "reasoning": "Ranging market"},
                  {"agent": "Synthesis", "final_decision": {"action": "BUY", "lots": 0.1, "stop_loss": 1.08, "confidence": 0.72}, "reasoning_synthesis": "Consensus buy", "agent_weights_applied": {"Signal": 0.7, "Risk": 0.8, "Context": 1.0}, "memory_update_intent": "RSI oversold in range"}
                ]"""
                usage = {"input_tokens": 3000, "output_tokens": 800}

            return MockResponse()

    # Setup
    validator = INoTValidator(Path("schemas/inot_agents.schema.json"))
    orchestrator = INoTOrchestrator(
        llm_client=MockLLM(), config={"temperature": 0.0}, validator=validator
    )

    # Mock context
    class MockContext:
        symbol = "EURUSD"
        price = 1.0850
        timestamp = datetime.now()
        rsi = 28
        macd = -0.002
        macd_signal = -0.001
        atr = 0.0015
        volume = 1000
        latest_news = "ECB maintains rates"
        sentiment = -0.2
        current_position = None
        unrealized_pnl = 0.0
        account_equity = 10000
        free_margin = 9000

    class MockMemory:
        def to_summary(self, max_tokens):
            return "Recent: 3 wins, 1 loss. Win rate 75%."

    # Execute
    decision = orchestrator.reason(MockContext(), MockMemory())

    print(f"Decision: {decision.action} {decision.lots} lots")
    print(f"Confidence: {decision.confidence:.2f}")
    print(f"Vetoed: {decision.vetoed}")
