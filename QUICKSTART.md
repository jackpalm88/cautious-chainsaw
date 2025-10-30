# 🚀 Quick Start - Trading Agent v1.0

**5-minute guide to get started with the Trading Agent**

---

## 📦 Installation

### 1. Clone Repository

```bash
git clone https://github.com/jackpalm88/cautious-chainsaw.git
cd cautious-chainsaw
```

### 2. Install Dependencies

```bash
pip install numpy pytest pytest-cov
```

### 3. Verify Installation

```bash
# Run tests
pytest tests/test_tools.py -v

# Run demo
python examples/demo_tools.py
```

**Expected output:**
```
15 passed in 0.82s
```

---

## 🎯 Basic Usage

### Example 1: Calculate RSI

```python
from src.trading_agent.tools import CalcRSI

# Create RSI tool
rsi = CalcRSI(period=14)

# Your price data
prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
          110, 111, 112, 113, 114, 115, 116, 117, 118, 119]

# Calculate
result = rsi.execute(prices=prices)

# Check result
print(f"RSI: {result.value['rsi']:.2f}")
print(f"Signal: {result.value['signal']}")
print(f"Confidence: {result.confidence:.3f}")

# Decision
if result.is_high_confidence:
    print("✅ High confidence - proceed")
else:
    print("⚠️ Low confidence - abort")
```

**Output:**
```
RSI: 100.00
Signal: bearish
Confidence: 0.907
✅ High confidence - proceed
```

---

### Example 2: Calculate MACD

```python
from src.trading_agent.tools import CalcMACD

# Create MACD tool
macd = CalcMACD()

# Need more data for MACD (minimum 35 prices)
prices = [100 + i * 0.5 for i in range(50)]

# Calculate
result = macd.execute(prices=prices)

print(f"MACD: {result.value['macd']:.5f}")
print(f"Signal: {result.value['signal']:.5f}")
print(f"Histogram: {result.value['histogram']:.5f}")
print(f"Trading Signal: {result.value['trading_signal']}")
```

**Output:**
```
MACD: 2.01411
Signal: 1.98654
Histogram: 0.02757
Trading Signal: bullish
```

---

### Example 3: Tool Registry for LLM

```python
from src.trading_agent.tools import ToolRegistry, CalcRSI, CalcMACD
import json

# Create registry
registry = ToolRegistry()

# Register tools
registry.register(CalcRSI())
registry.register(CalcMACD())

# Export for LLM function calling
functions = registry.get_llm_functions()

print(json.dumps(functions, indent=2))
```

**Output:**
```json
[
  {
    "name": "calc_rsi",
    "description": "Calculate Relative Strength Index (RSI) with confidence scoring",
    "parameters": {
      "type": "object",
      "properties": {
        "prices": {
          "type": "array",
          "items": {"type": "number"},
          "description": "List of closing prices (minimum 15 values)"
        }
      },
      "required": ["prices"]
    }
  },
  ...
]
```

---

## 🧪 Testing with MockAdapter

```python
import asyncio
from src.trading_agent.adapters import MockAdapter, MT5ExecutionBridge
from src.trading_agent.adapters.adapter_base import Signal, OrderDirection

async def test_execution():
    # Create mock adapter (no MT5 required!)
    adapter = MockAdapter(success_rate=0.95, latency_ms=50.0)
    await adapter.connect()
    
    # Create bridge
    bridge = MT5ExecutionBridge(adapter=adapter)
    
    # Create signal
    signal = Signal(
        symbol='EURUSD',
        direction=OrderDirection.LONG,
        size=0.1,
        confidence=0.88
    )
    
    # Execute
    signal_id = bridge.receive_signal(signal)
    result = await bridge.execute_order(signal_id, signal)
    
    print(f"Success: {result.success}")
    print(f"Fill Price: {result.fill_price}")
    
    await adapter.disconnect()

# Run
asyncio.run(test_execution())
```

---

## 📊 Understanding Confidence

The 8-factor confidence model:

```python
confidence = (
    sample_sufficiency^0.25 *      # Do we have enough data?
    volatility_regime^0.15 *       # Is volatility normal?
    indicator_agreement^0.20 *     # Do indicators agree?
    data_quality^0.10 *            # Is data clean?
    liquidity_regime^0.12 *        # (future)
    session_factor^0.08 *          # (future)
    news_proximity^0.07 *          # (future)
    spread_anomaly^0.03            # (future)
)
```

**Thresholds:**
- ≥ 0.7: High confidence → Proceed
- 0.5-0.69: Low confidence → Recommend wait
- < 0.5: Very low → Abort

---

## 🏗️ Project Structure

```
cautious-chainsaw/
├── src/trading_agent/
│   ├── adapters/              # MT5 Bridge (MockAdapter + RealMT5Adapter)
│   ├── tools/                 # Tool Stack
│   │   ├── atomic/            # RSI, MACD
│   │   ├── composite/         # (future)
│   │   └── execution/         # (future)
│   ├── core/                  # Symbol normalization, confidence
│   └── llm/                   # (future)
├── tests/                     # Unit tests
├── examples/                  # Demo scripts
└── README.md
```

---

## 🎓 Next Steps

1. **Read Documentation:**
   - `README.md` - Full architecture overview
   - `IMPLEMENTATION_SUMMARY.md` - Current status
   - `examples/demo_tools.py` - Interactive demo

2. **Explore Tools:**
   - Check `src/trading_agent/tools/atomic/` for tool implementations
   - Review `tests/test_tools.py` for usage examples

3. **Add Your Own Tool:**
   ```python
   from src.trading_agent.tools import BaseTool, ToolResult, ToolTier
   
   class MyTool(BaseTool):
       name = "my_tool"
       version = "1.0.0"
       tier = ToolTier.ATOMIC
       
       def execute(self, **kwargs):
           # Your logic here
           return ToolResult(value=..., confidence=..., latency_ms=...)
       
       def get_schema(self):
           return {...}  # JSON-Schema for LLM
   ```

4. **Integrate with LLM:**
   - Use `registry.get_llm_functions()` for OpenAI function calling
   - See Tool Stack Action Plan for orchestration prompt

---

## ⚡ Performance Targets

| Tool Type | Target Latency (p95) | Actual |
|-----------|---------------------|--------|
| Atomic | <5ms | <1ms ✅ |
| Composite | <50ms | TBD |
| Execution | <500ms | TBD |

---

## 🐛 Troubleshooting

### Import Error: "No module named 'src'"

```bash
# Add to your script:
import sys
import os
sys.path.insert(0, '/path/to/cautious-chainsaw')
```

### Test Failures

```bash
# Reinstall dependencies
pip install --upgrade numpy pytest pytest-cov

# Run with verbose output
pytest tests/test_tools.py -vv
```

### Low Confidence Scores

- Check if you have enough data (RSI needs 15+ prices, MACD needs 35+)
- Verify data quality (no gaps, no flat periods)
- Review confidence components in `result.metadata`

---

## 📞 Support

- **Issues:** https://github.com/jackpalm88/cautious-chainsaw/issues
- **Discussions:** https://github.com/jackpalm88/cautious-chainsaw/discussions
- **Documentation:** See `README.md` and `IMPLEMENTATION_SUMMARY.md`

---

**Ready to trade? Start with the demo:**

```bash
python examples/demo_tools.py
```

**Happy Trading! 🚀**
