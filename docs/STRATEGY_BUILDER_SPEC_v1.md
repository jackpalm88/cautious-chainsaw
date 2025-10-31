# 📜 Strategy Builder Spec v1.0

**Datums:** 2025-10-30  
**Autors:** Manus AI (INoT Framework)

---

## 🎯 Mērķis

Šis dokuments definē tehnisko specifikāciju **Strategy Builder** modulim. Mērķis ir izveidot deklaratīvu, testējamu un paplašināmu sistēmu tirdzniecības stratēģiju veidošanai un pārvaldībai.

---

## 1. Failu Struktūra

```
cautious-chainsaw/
├── src/trading_agent/
│   ├── strategies/                 # Jauns modulis
│   │   ├── __init__.py
│   │   ├── dsl/                    # DSL shēma un validācija
│   │   │   ├── __init__.py
│   │   │   └── schema.json
│   │   ├── compiler.py             # Pārvērš DSL uz Python objektu
│   │   ├── tester.py               # Backtesting ar MockAdapter
│   │   ├── registry.py             # Saglabā stratēģijas un rezultātus
│   │   ├── base_strategy.py        # Bāzes klase visām stratēģijām
│   │   └── selector.py             # Izvēlas labāko stratēģiju
│   ├── decision/
│   │   └── engine.py               # Integrācija ar Strategy Selector
│   └── tools/
│       └── market_context.py       # Jauns tool tirgus režīma noteikšanai
├── data/
│   ├── strategies/                 # Lietotāja definētās stratēģijas
│   │   ├── rsi_oversold.yaml
│   │   └── macd_crossover.yaml
│   └── strategy_registry.db        # SQLite datubāze
└── tests/
    └── test_strategy_builder.py    # Jauni testi
```

---

## 2. Strategy DSL (schema.json)

**Atrašanās vieta:** `src/trading_agent/strategies/dsl/schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Trading Strategy DSL",
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "Unikāls stratēģijas nosaukums"
    },
    "description": {
      "type": "string",
      "description": "Stratēģijas apraksts"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "author": {"type": "string"},
        "version": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "priority": {"type": "integer", "minimum": 1, "maximum": 10},
        "active_regimes": {"type": "array", "items": {"type": "string"}},
        "avoid_news_events": {"type": "array", "items": {"type": "string"}}
      }
    },
    "conditions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "field": {"type": "string", "description": "Lauks no FusedContext (piem., context.rsi)"},
          "operator": {"type": "string", "enum": ["<", "<=", ">", ">=", "==", "!="]},
          "value": {"type": ["number", "string", "boolean"]}
        },
        "required": ["field", "operator", "value"]
      }
    },
    "action": {
      "type": "string",
      "enum": ["BUY", "SELL"]
    },
    "risk": {
      "type": "object",
      "properties": {
        "stop_loss_percent": {"type": "number"},
        "take_profit_percent": {"type": "number"},
        "max_risk_per_trade_percent": {"type": "number"}
      },
      "required": ["stop_loss_percent", "max_risk_per_trade_percent"]
    }
  },
  "required": ["name", "conditions", "action", "risk"]
}
```

**Piemērs (rsi_oversold.yaml):**

```yaml
name: RSI_Oversold_Mean_Reversion
description: Pērk, kad RSI ir pārpārdots un tirgus ir "ranging"
metadata:
  author: Manus AI
  version: 1.0
  tags: ["RSI", "mean-reversion"]
  priority: 7
  active_regimes: ["ranging"]
conditions:
  - field: rsi
    operator: "<"
    value: 30
  - field: macd_histogram
    operator: ">"
    value: 0
  - field: bb_position
    operator: "=="
    value: "LOWER"
action: BUY
risk:
  stop_loss_percent: 1.5
  take_profit_percent: 3.0
  max_risk_per_trade_percent: 1.0
```

---

## 3. Funkciju Prototipi (Python Pseidokods)

### `MarketContext` Tool

```python
# src/trading_agent/tools/market_context.py

class MarketContext(BaseTool):
    def execute(self, prices: list[float]) -> dict:
        # Aprēķina volatilitāti (piem., ATR)
        volatility = self._calculate_volatility(prices)

        # Nosaka tirgus režīmu (trending, ranging, volatile)
        regime = self._detect_regime(prices)

        return {
            "volatility": volatility,
            "regime": regime
        }
```

### `Strategy Compiler`

```python
# src/trading_agent/strategies/compiler.py

from .base_strategy import BaseStrategy

class StrategyCompiler:
    def compile(self, dsl_data: dict) -> BaseStrategy:
        # Validē DSL pret schema.json
        self._validate_dsl(dsl_data)

        # Izveido dinamisku Python klasi
        class CompiledStrategy(BaseStrategy):
            def __init__(self, dsl):
                self.dsl = dsl

            def evaluate(self, context: FusedContext) -> bool:
                # Pārbauda metadata (piem., active_regimes)
                if context.regime not in self.dsl["metadata"]["active_regimes"]:
                    return False

                # Pārbauda nosacījumus
                for cond in self.dsl["conditions"]:
                    field_value = getattr(context, cond["field"])
                    if not self._check_condition(field_value, cond["operator"], cond["value"]):
                        return False
                return True

        return CompiledStrategy(dsl_data)
```

### `Strategy Tester`

```python
# src/trading_agent/strategies/tester.py

class StrategyTester:
    def __init__(self, mock_adapter):
        self.mock_adapter = mock_adapter

    def backtest(self, strategy: BaseStrategy, historical_data: list) -> dict:
        # Iterē caur vēsturiskajiem datiem
        # Katrā solī izsauc strategy.evaluate()
        # Ja evaluate() atgriež True, izpilda orderi caur MockAdapter
        # Aprēķina rezultātus (profit, drawdown, Sharpe ratio)
        pass
```

### `Strategy Registry`

```python
# src/trading_agent/strategies/registry.py

import sqlite3

class StrategyRegistry:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)

    def register_strategy(self, strategy_dsl: dict):
        # Saglabā stratēģijas DSL datubāzē
        pass

    def save_test_results(self, strategy_name: str, results: dict):
        # Saglabā backtest rezultātus
        pass

    def get_best_strategy(self, symbol: str, regime: str) -> BaseStrategy:
        # Atrod labāko stratēģiju pēc Sharpe ratio
        pass
```

### `Strategy Selector`

```python
# src/trading_agent/strategies/selector.py

class StrategySelector:
    def __init__(self, registry: StrategyRegistry):
        self.registry = registry

    def select(self, context: FusedContext) -> BaseStrategy | None:
        # Iegūst labāko stratēģiju no reģistra
        best_strategy = self.registry.get_best_strategy(
            context.symbol,
            context.regime
        )

        # Pārbauda, vai stratēģija ir aktīva
        if best_strategy and best_strategy.evaluate(context):
            return best_strategy
        return None
```

### `TradingDecisionEngine` Integrācija

```python
# src/trading_agent/decision/engine.py

class TradingDecisionEngine:
    def __init__(self, config):
        # ...
        self.strategy_selector = StrategySelector(self.strategy_registry)

    def decide(self, context: FusedContext) -> Decision:
        # 1. Izvēlas labāko stratēģiju
        strategy = self.strategy_selector.select(context)

        if strategy:
            # Izpilda stratēģiju
            risk_params = strategy.dsl["risk"]
            # ... aprēķina pozīcijas lielumu
            return Decision(...)

        # 2. Ja nav stratēģijas, izmanto INoT
        if self.config["inot"]["enabled"]:
            return self.inot_orchestrator.reason(context, self.memory)

        # 3. Fallback uz rules
        return self._fallback_rules(context)
```

---

## 4. Implementācijas Plāns

1. **Fāze 1: `MarketContext` Tool**
   - Izveidot `MarketContext` tool, kas nosaka tirgus režīmu un volatilitāti.

2. **Fāze 2: DSL & Compiler**
   - Izveidot `schema.json`.
   - Izveidot `StrategyCompiler`.

3. **Fāze 3: Tester & Registry**
   - Izveidot `StrategyTester` ar `MockAdapter`.
   - Izveidot `StrategyRegistry` ar SQLite.

4. **Fāze 4: Selector & Integration**
   - Izveidot `StrategySelector`.
   - Integrēt ar `TradingDecisionEngine`.

5. **Fāze 5: LLM Co-Design**
   - Izveidot prompt, kas liek LLM ģenerēt stratēģijas DSL formātā.

---

**Šī specifikācija nodrošina skaidru ceļu uz modulāru, testējamu un AI-vadītu tirdzniecības sistēmu.** 🚀**
