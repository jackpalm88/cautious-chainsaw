# 🤖 Trading Agent v1.0

**INoT-Inspired Multi-Broker Trading Agent with LLM Orchestration**

Advanced algorithmic trading framework featuring:
- ✅ **Multi-Broker Support** (MT5, Binance, IBKR)
- ✅ **Symbol Normalization** (FX, Crypto, CFD, Stocks)
- ✅ **Enhanced Confidence Scoring** (8-factor model)
- ✅ **Hybrid LLM Orchestration** (Passive + Active modes)
- ✅ **Tool Stack Architecture** (Atomic → Composite → Execution)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- MetaTrader 5 (optional - for live trading)
- Binance account (optional - for crypto)

### Installation

```bash
# Clone repository
git clone https://github.com/jackpalm88/Financial-Agent.git
cd Financial-Agent

# Install core package
pip install -e .

# (Optional) Technical analysis extras
pip install -e ".[dev,technical-analysis]"

# Run tests
pytest
```

### Basic Usage

```python
from trading_agent.core.symbol_normalization import UniversalSymbolNormalizer, NormalizerFactory
from trading_agent.adapters.mt5_adapter import MT5Adapter

# Initialize broker adapter
adapter = MT5Adapter()
adapter.connect()

# Create normalizer
normalizer = UniversalSymbolNormalizer(
    NormalizerFactory.create("mt5", adapter)
)

# Calculate risk for 20 pip stop loss
risk_value = normalizer.to_risk_units("EURUSD", 20, "pips")
print(f"20 pips on EURUSD = ${risk_value:.2f} per lot")

# Get normalized symbol info
info = normalizer.get_normalized_info("EURUSD")
print(f"Min lot size: {info.min_size}, Step: {info.size_step}")
```

---

## 📦 Architecture Overview

### Multi-Broker Normalization

```
┌─────────────┐
│ User Input  │
│ "20 pips SL"│
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ Symbol Normalizer│
│  (Broker-Agnostic)│
└──────┬───────────┘
       │
       ├──► MT5: 20 * 0.0001 * 100,000 * tick_value = $200/lot
       ├──► Binance: 20 * tick_size * price * multiplier
       └──► IBKR: 20 * contract_multiplier * tick_value
```

**Key Files:**
- `core/symbol_normalization.py` - Multi-broker symbol normalization
- `adapters/mt5_adapter.py` - MetaTrader 5 implementation
- `adapters/binance_adapter.py` - Binance implementation (stub v1.0)

### Confidence Model (8-Factor)

```python
confidence = (
    # Technical Factors (70%)
    sample_sufficiency^0.25 *
    volatility_regime^0.15 *
    indicator_agreement^0.20 *
    data_quality^0.10 *
    
    # Market Context (30%)
    liquidity_regime^0.12 *
    session_factor^0.08 *
    news_proximity^0.07 *
    spread_anomaly^0.03
)
```

**Confidence Thresholds:**
- ≥ 0.7: Proceed with trade
- 0.5-0.69: Low confidence (recommend wait)
- < 0.5: Abort (unreliable signal)

**Key Files:**
- `core/confidence_model.py` - Enhanced confidence calculator
- `core/market_context.py` - Market regime detection

### LLM Orchestration (Hybrid Mode)

**Passive Mode** (User-Driven)
```
User: "What is RSI for EURUSD?"
→ Single tool call: calc_rsi()
→ Return: "RSI: 65.4"
```

**Active Mode** (Autonomous Chain)
```
User: "Should I buy EURUSD?"
→ Tool chain:
  1. technical_overview() → confidence=0.88 ✓
  2. check_spread() → 18 pips ✓
  3. risk_fixed_fractional() → 0.5 lots
  4. generate_order() → proposal ready
→ Return: Comprehensive analysis + order proposal
```

**Key Files:**
- `core/orchestration.py` - Hybrid orchestration logic
- `llm/prompts.py` - System prompts for LLM
- `llm/orchestrator.py` - LLM integration layer

---

## 🧪 Testing

### Run All Tests
```bash
pytest
```

### Test Coverage
```bash
pytest --cov=src/trading_agent --cov-report=html
open htmlcov/index.html
```

### Test Categories
```bash
# Fast unit tests only
pytest -m unit

# Integration tests (may require broker connections)
pytest -m integration

# Slow tests (>1 second)
pytest -m slow
```

---

## 📚 Documentation

### Key Concepts

**Symbol Normalization**
- Problem: Different brokers use different units (pips vs points vs ticks)
- Solution: Unified `NormalizedSymbolInfo` format
- Implementation: Broker-specific normalizers + factory pattern

**Confidence Scoring**
- Problem: Single-factor confidence (sample size) insufficient
- Solution: 8-factor model (technical + market context)
- Implementation: Weighted geometric mean (robust to outliers)

**LLM Orchestration**
- Problem: LLM needs tool usage guidance
- Solution: Hybrid mode (passive for simple, active for complex)
- Implementation: Query classifier + multi-tool chain executor

### Architecture Documents

Located in `/docs`:
- `tool_stack_architecture_final.md` - Complete architecture spec
- `tool_stack_inot_deep_dive.md` - Multi-agent design analysis
- `architecture_validation_summary.md` - Dual-AI convergence report

---

## 🛠️ Development

### Setup Development Environment

```bash
# Install with dev dependencies
pip install -e ".[dev,llm]"

# Install pre-commit hooks (optional)
pre-commit install

# Run linter
ruff check src/ tests/

# Run type checker
mypy src/
```

### Project Structure

```
trading-agent-v1/
├── src/trading_agent/
│   ├── core/
│   │   ├── symbol_normalization.py   # Multi-broker normalization
│   │   ├── confidence_model.py       # 8-factor confidence
│   │   ├── orchestration.py          # Hybrid LLM orchestration
│   │   └── market_context.py         # Market regime detection
│   ├── adapters/
│   │   ├── mt5_adapter.py            # MetaTrader 5 (complete)
│   │   ├── binance_adapter.py        # Binance (stub v1.0)
│   │   └── ibkr_adapter.py           # IBKR (stub v1.0)
│   ├── tools/
│   │   ├── technical_overview.py     # Composite technical analysis
│   │   ├── risk_calc.py              # Risk management tools
│   │   └── generate_order.py         # Order generation
│   └── llm/
│       ├── prompts.py                # System prompts
│       └── orchestrator.py           # LLM integration
├── tests/
│   ├── test_symbol_normalization.py
│   ├── test_confidence_model.py
│   ├── test_orchestration.py
│   └── test_end_to_end.py
├── data/fixtures/                    # Test data
└── docs/                             # Architecture docs
```

---

## 🚦 Roadmap

### v1.0 (Current) - Week 1 Complete ✅
- [x] Multi-broker symbol normalization (MT5 + stubs)
- [x] Enhanced confidence model (8 factors)
- [x] Hybrid LLM orchestration
- [x] Core tool stack (6+ tools)
- [x] Test coverage >90%

### v1.1 (Next Sprint)
- [ ] Full Binance implementation
- [ ] Economic calendar integration (ForexFactory API)
- [ ] Empirical confidence calibration
- [ ] Advanced orchestration (5+ tool chains)
- [ ] Performance optimization (async tools)

### v1.2 (Future)
- [ ] IBKR adapter complete
- [ ] Alpaca integration
- [ ] Machine learning confidence models
- [ ] Multi-timeframe analysis
- [ ] Portfolio management tools

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

**Architecture inspired by:**
- INoT Framework (Multi-Agent Introspection)
- FinAgent MQL5 Implementation
- CCXT Multi-Exchange Library

**Validation:**
- Dual-AI convergence (INoT + GPT) → 95% alignment
- MT5 Bridge v2.0 pattern validation
- Industry best practices (MetaQuotes, Binance API)

---

## 📞 Support

- **Issues:** https://github.com/jackpalm88/Financial-Agent/issues
- **Documentation:** https://github.com/jackpalm88/Financial-Agent#readme
- **Discussions:** https://github.com/jackpalm88/Financial-Agent/discussions

---

**Built with ❤️ using INoT Multi-Agent Architecture**
