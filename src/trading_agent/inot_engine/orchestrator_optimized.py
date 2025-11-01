"""
Optimized INoT Prompt Template

This file contains the optimized multi-agent prompt that will replace
the current verbose prompt in orchestrator.py.

Optimizations applied:
1. Trend-following clarity (from single-agent prompts)
2. Confidence calibration guidelines
3. RSI/MACD interpretation rules
4. Concise instructions (remove redundancy)
5. Reduced token count (~2500 vs ~3500)

Expected improvements:
- Latency: 12s → 7-8s (-30%)
- Consistency: Maintained or improved
- JSON compliance: Maintained (>95%)
"""

def build_optimized_inot_prompt(context, memory_summary: str) -> str:
    """
    Build optimized INoT multi-agent prompt.
    
    Token budget:
    - Context: ~400 tokens (reduced from 800)
    - Memory: ~600 tokens (reduced from 1000)
    - Instructions: ~1200 tokens (reduced from 1500)
    - Total: ~2200 tokens (vs 3500 before)
    """
    
    prompt = f"""# Multi-Agent Trading Decision (INoT Framework)

Analyze market from 4 perspectives, output JSON array with 4 objects.

## Market Context
**{context.symbol}** @ {context.price:.4f} | RSI: {context.rsi:.1f} | MACD: {context.macd:+.4f} | ATR: {context.atr:.5f}
News: {context.latest_news[:150]}... (Sentiment: {context.sentiment:+.1f})
Position: {context.current_position or 'FLAT'} | P&L: {context.unrealized_pnl:+.0f} pips
Equity: ${context.account_equity:.0f} | Free: ${context.free_margin:.0f}

## Memory
{memory_summary}

---

## Agent Instructions

**TRADING RULES (ALL AGENTS):**
- Trend-following ONLY: Uptrend→BUY/HOLD, Downtrend→SELL/HOLD, Sideways→HOLD
- RSI: 70+=overbought (caution), 50-70=bullish, 30-50=bearish, <30=oversold (caution)
- MACD: >signal=bullish, <signal=bearish, near 0=weak
- Confidence: 0.8+=strong trend+multi-confirm, 0.6-0.8=clear trend, 0.4-0.6=weak→HOLD, <0.4=HOLD

### 1. Signal Agent (Technical)
Identify trading signal from technicals.
```json
{{
  "agent": "Signal",
  "action": "BUY|SELL|HOLD",
  "confidence": 0.0-1.0,
  "reasoning": "Why (50-300 chars)",
  "key_factors": ["factor1", "factor2"]
}}
```

### 2. Risk Agent (Risk Manager)
Validate signal, can VETO if risk too high.
```json
{{
  "agent": "Risk",
  "approved": true|false,
  "confidence": 0.0-1.0,
  "position_size_adjustment": 0.0-2.0,
  "stop_loss_required": true|false,
  "reasoning": "Risk assessment (50-300 chars)",
  "veto_reason": null|"Why blocked"
}}
```

### 3. Context Agent (Macro)
Evaluate regime and news fit.
```json
{{
  "agent": "Context",
  "regime": "trending_bullish|trending_bearish|ranging|volatile_uncertain",
  "regime_confidence": 0.0-1.0,
  "signal_regime_fit": 0.0-1.0,
  "news_alignment": "supporting|neutral|conflicting",
  "weight_adjustment": 0.5-1.5,
  "reasoning": "Context analysis (50-300 chars)"
}}
```

### 4. Synthesis Agent (Integrator)
Combine all into final decision.
```json
{{
  "agent": "Synthesis",
  "final_decision": {{
    "action": "BUY|SELL|HOLD|CLOSE",
    "lots": 0.0-10.0,
    "entry_price": float|null,
    "stop_loss": float|null,
    "take_profit": float|null,
    "confidence": 0.0-1.0
  }},
  "reasoning_synthesis": "Integrated explanation (100-500 chars)",
  "agent_weights_applied": {{"Signal": 0.5-2.0, "Risk": 0.5-2.0, "Context": 0.5-2.0}}
}}
```

---

## Output Format
Return ONLY JSON array: [Signal, Risk, Context, Synthesis]
- No markdown, no explanation
- If Risk.approved=false, Synthesis MUST action=HOLD
- If Risk.stop_loss_required=true, Synthesis MUST provide stop_loss

## Example (Bullish Scenario)
```json
[
  {{"agent": "Signal", "action": "BUY", "confidence": 0.75, "reasoning": "Uptrend: price +30 pips, RSI 58 (bullish), MACD crossover", "key_factors": ["uptrend", "rsi_bullish", "macd_positive"]}},
  {{"agent": "Risk", "approved": true, "confidence": 0.80, "position_size_adjustment": 1.0, "stop_loss_required": true, "reasoning": "Risk acceptable: ATR normal, margin sufficient, 2% risk limit OK", "veto_reason": null}},
  {{"agent": "Context", "regime": "trending_bullish", "regime_confidence": 0.85, "signal_regime_fit": 0.90, "news_alignment": "supporting", "weight_adjustment": 1.2, "reasoning": "Strong bullish regime, news supports USD weakness"}},
  {{"agent": "Synthesis", "final_decision": {{"action": "BUY", "lots": 0.10, "entry_price": 1.0950, "stop_loss": 1.0900, "take_profit": 1.1025, "confidence": 0.78}}, "reasoning_synthesis": "All agents align: strong uptrend, risk approved, bullish regime. Entry at 1.0950, SL 50 pips, TP 75 pips (1.5:1 R:R).", "agent_weights_applied": {{"Signal": 1.0, "Risk": 1.0, "Context": 1.2}}}}
]
```

Return JSON array now:
"""
    
    return prompt
