import asyncio
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from Memory import SQLiteMemoryStore, StoredDecision, StorageError
from trading_agent.adapters.adapter_mock import MockAdapter
from trading_agent.adapters.adapter_mt5 import RealMT5Adapter
from trading_agent.adapters.bridge import (
    MT5ExecutionBridge as ExecutionBridge,
    OrderDirection,
    Signal,
)
from trading_agent.decision.engine import FusedContext
from trading_agent.inot_engine.orchestrator import Decision as InotDecision, INoTOrchestrator
from trading_agent.inot_engine.validator import INoTValidator

# Import all completed modules
from trading_agent.input_fusion.engine import InputFusionEngine
from trading_agent.llm.anthropic_llm_client import LLMConfig, create_llm_client
from trading_agent.llm.inot_adapter import INoTLLMAdapter
from trading_agent.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from trading_agent.resilience.health_monitor import HealthMonitor, ServiceHealth, ServiceStatus
from trading_agent.strategies.compiler import StrategyCompiler
from trading_agent.strategies.registry import StrategyRegistry
from trading_agent.strategies.selector import StrategySelector
from trading_agent.tools import (
    CalcBollingerBands,
    CalcMACD,
    CalcRSI,
    MarketContext,
    TechnicalOverview,
)

# Note: Assuming StoredDecision and TradeOutcome are defined in Memory module or accessible

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TradingAgent:
    """Main orchestrator connecting all trading modules."""

    def __init__(self, config_path: str = "config/production.yaml"):
        dotenv_path = Path(".env")
        load_dotenv(dotenv_path=dotenv_path if dotenv_path.exists() else None)
        raw_config = self._load_config(config_path)
        self.config = raw_config
        self.running = False
        self._validate_env_vars()
        self.config = self._resolve_env_placeholders(self.config, source=config_path)
        self._initialize_components()

    def _validate_env_vars(self) -> None:
        """Validate required environment variables are set."""

        required_env_vars = {"ANTHROPIC_API_KEY"}
        broker_config = self.config.get("broker", {})
        if broker_config.get("type", "mt5").lower() == "mt5":
            required_env_vars.update({"MT5_SERVER", "MT5_LOGIN", "MT5_PASSWORD"})

        missing = [var for var in required_env_vars if not os.getenv(var)]
        if missing:
            raise EnvironmentError(
                "Missing required environment variables: "
                + ", ".join(sorted(missing))
            )

    def _load_config(self, path: str) -> dict[str, Any]:
        """Load configuration from file."""

        try:
            with open(path, "r", encoding="utf-8") as handle:
                config = yaml.safe_load(handle) or {}
        except FileNotFoundError as exc:
            logger.error("Configuration file not found at %s", path)
            raise
        except Exception as exc:
            logger.error("Failed to load configuration: %s", exc)
            raise

        return config

    def _resolve_env_placeholders(self, value: Any, *, source: str) -> Any:
        """Recursively resolve ${VAR} placeholders using environment variables."""

        if isinstance(value, dict):
            return {k: self._resolve_env_placeholders(v, source=source) for k, v in value.items()}

        if isinstance(value, list):
            return [self._resolve_env_placeholders(item, source=source) for item in value]

        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            env_value = os.getenv(env_var)
            if env_value is None or env_value.strip() == "":
                raise ValueError(
                    f"Environment variable '{env_var}' referenced in {source} is not set."
                )
            return env_value

        return value

    def _initialize_components(self) -> None:
        """Initialize all trading components."""

        fusion_config = self.config.get("fusion", {})
        self.fusion = InputFusionEngine(
            sync_window_ms=fusion_config.get("window_ms", 100),
            buffer_capacity=fusion_config.get("buffer_size", 1000),
        )

        # Technical tool stack
        tools_config = self.config.get("tools", {})
        self.rsi_tool = CalcRSI(period=tools_config.get("rsi_period", 14))
        self.macd_tool = CalcMACD(
            fast_period=tools_config.get("macd_fast", 12),
            slow_period=tools_config.get("macd_slow", 26),
            signal_period=tools_config.get("macd_signal", 9),
        )
        self.bb_tool = CalcBollingerBands(
            period=tools_config.get("bb_period", 20),
            std_multiplier=tools_config.get("bb_std", 2.0),
        )
        self.technical_overview = TechnicalOverview(
            rsi_period=self.rsi_tool.period,
            macd_fast=self.macd_tool.fast_period,
            macd_slow=self.macd_tool.slow_period,
            macd_signal=self.macd_tool.signal_period,
            bb_period=self.bb_tool.period,
            bb_std=self.bb_tool.std_multiplier,
        )
        self.market_context_tool = MarketContext()

        # INoT Analysis Engine
        try:
            schema_path = (
                Path(__file__).parent / "inot_engine" / "schemas" / "inot_agents.schema.json"
            )
            validator = INoTValidator(schema_path=schema_path)
            llm_client = create_llm_client(
                LLMConfig(api_key=os.getenv("ANTHROPIC_API_KEY"))
            )
            self.inot = INoTOrchestrator(
                llm_client=INoTLLMAdapter(llm_client),
                config=self.config.get("inot", {}),
                validator=validator,
            )
            self.inot_threshold = float(self.config.get("inot", {}).get("threshold", 0.7))
        except Exception as exc:
            logger.exception("Failed to initialize INoT orchestrator: %s", exc)
            raise

        # Strategy Management
        self.strategy_compiler = StrategyCompiler()
        strategies_config = self.config.get("strategies", {})
        registry_path = strategies_config.get("registry_path")
        self.strategy_registry = (
            StrategyRegistry(registry_path) if registry_path else StrategyRegistry()
        )
        self.strategy_selector = StrategySelector(self.strategy_registry)
        self.strategy_library = self._load_strategy_library()

        # Memory System
        memory_config = self.config.get("memory", {})
        self.memory = SQLiteMemoryStore(
            db_path=memory_config.get("db_path", "./data/memory.db")
        )

        # Execution Layer
        adapter_type = self.config.get("broker", {}).get("type", "mt5").lower()
        if adapter_type == "mt5":
            broker_config = self.config.get("broker", {})
            adapter = RealMT5Adapter(
                {
                    "login": int(broker_config["login"]),
                    "password": broker_config["password"],
                    "server": broker_config["server"],
                    "timeout": int(broker_config.get("timeout", 60000)),
                    "path": broker_config.get("path"),
                }
            )
        elif adapter_type == "mock":
            adapter = MockAdapter()
        else:
            raise ValueError(f"Unknown adapter type: {adapter_type}")

        self.execution = ExecutionBridge(adapter)

        # Resilience Layer
        resilience_config = self.config.get("resilience", {})
        breaker_config = CircuitBreakerConfig(
            failure_threshold=resilience_config.get("failure_threshold", 3),
            recovery_timeout=resilience_config.get("recovery_timeout", 20),
            half_open_max_successes=resilience_config.get("half_open_max_successes", 2),
            name="inot-analysis",
        )
        self.circuit_breaker = CircuitBreaker(config=breaker_config)

        self.health_monitor = HealthMonitor()
        self._register_health_checks()

        logger.info("All components initialized successfully")

    def _register_health_checks(self) -> None:
        """Register health monitoring checks."""

        self.health_monitor.register("fusion", self._check_fusion)
        self.health_monitor.register("memory", self._check_memory)
        self.health_monitor.register("execution", self._check_execution)

    def _load_strategy_library(self) -> list[Any]:
        """Load and compile active strategies."""

        strategies: list[Any] = []

        try:
            registry_strategies = self.strategy_registry.list_strategies(active_only=True)
            if registry_strategies:
                for entry in registry_strategies:
                    dsl_content = entry.get("dsl_content")
                    if not dsl_content:
                        continue
                    strategy_def = yaml.safe_load(dsl_content)
                    strategies.append(self.strategy_compiler.compile(strategy_def))
            else:
                strategies_dir = Path(
                    self.config.get("strategies", {}).get("dsl_path", "data/strategies")
                )
                if strategies_dir.exists():
                    for pattern in ("*.yml", "*.yaml", "*.json"):
                        for file_path in sorted(strategies_dir.glob(pattern)):
                            strategies.append(
                                self.strategy_compiler.compile_from_file(str(file_path))
                            )

        except Exception as exc:
            logger.error("Failed to load strategies: %s", exc)
            raise

        if not strategies:
            raise RuntimeError(
                "No trading strategies available. Register strategies in the registry "
                "or provide DSL files under data/strategies/."
            )

        for strategy in strategies:
            if not hasattr(strategy, "evaluate") or not hasattr(strategy, "generate_signal"):
                raise TypeError(
                    f"Strategy {strategy} does not implement the required interface."
                )

        logger.info("Loaded %d strategies", len(strategies))
        return strategies

    def _check_fusion(self) -> ServiceHealth:
        """Health check for the fusion engine."""

        start = time.perf_counter()
        details: dict[str, str] = {}
        status = ServiceStatus.HEALTHY

        try:
            snapshot = self.fusion.get_latest_snapshot()
            if snapshot is None:
                status = ServiceStatus.DEGRADED
                details["message"] = "No fused snapshot available"
        except Exception as exc:
            status = ServiceStatus.UNAVAILABLE
            details["error"] = str(exc)

        latency = (time.perf_counter() - start) * 1000
        return ServiceHealth(
            name="fusion",
            status=status,
            checked_at=time.time(),
            latency_ms=latency,
            details=details,
        )

    def _check_memory(self) -> ServiceHealth:
        """Health check for the memory subsystem."""

        start = time.perf_counter()
        details: dict[str, str] = {}

        try:
            recent = self.memory.load_recent_decisions(limit=1)
            status = ServiceStatus.HEALTHY if recent else ServiceStatus.DEGRADED
            details["recent_decisions"] = str(len(recent))
        except StorageError as exc:
            status = ServiceStatus.UNAVAILABLE
            details["error"] = str(exc)

        latency = (time.perf_counter() - start) * 1000
        return ServiceHealth(
            name="memory",
            status=status,
            checked_at=time.time(),
            latency_ms=latency,
            details=details,
        )

    def _check_execution(self) -> ServiceHealth:
        """Health check for broker connectivity."""

        start = time.perf_counter()
        adapter = self.execution.adapter
        details: dict[str, str] = {"adapter": adapter.get_name()}
        status = ServiceStatus.HEALTHY

        try:
            if not adapter.is_connected():
                status = ServiceStatus.DEGRADED
                details["message"] = "Execution adapter disconnected"
        except Exception as exc:
            status = ServiceStatus.UNAVAILABLE
            details["error"] = str(exc)

        latency = (time.perf_counter() - start) * 1000
        return ServiceHealth(
            name="execution",
            status=status,
            checked_at=time.time(),
            latency_ms=latency,
            details=details,
        )

    async def run(self) -> None:
        """Main trading loop."""

        self.running = True
        logger.info("Starting trading agent...")
        loop_delay = float(self.config.get("trading", {}).get("loop_interval", 60))

        while self.running:
            try:
                market_data = await self._collect_market_data()
                if not market_data:
                    await asyncio.sleep(1)
                    continue

                analysis = await self._analyze_market(market_data)
                strategy = self._select_strategy(analysis)
                decision = self._make_decision(analysis, strategy)
                self._store_decision(decision)

                min_confidence = float(self.config.get("trading", {}).get("min_confidence", 0.7))
                if decision.confidence >= min_confidence and decision.lots > 0:
                    await self._execute_trade(decision, analysis["decision"])

                self._update_metrics()
                await asyncio.sleep(loop_delay)

            except Exception as exc:
                logger.error("Error in trading loop: %s", exc)
                await self._handle_error(exc)

    async def run_single_iteration(self) -> None:
        """Run a single trading iteration (used for testing)."""

        try:
            market_data = await self._collect_market_data()
            if not market_data:
                return

            analysis = await self._analyze_market(market_data)
            strategy = self._select_strategy(analysis)
            decision = self._make_decision(analysis, strategy)
            self._store_decision(decision)

            min_confidence = float(self.config.get("trading", {}).get("min_confidence", 0.7))
            if decision.confidence >= min_confidence and decision.lots > 0:
                await self._execute_trade(decision, analysis["decision"])

            self._update_metrics()
        except Exception as exc:
            logger.error("Error in single iteration: %s", exc)
            await self._handle_error(exc)

    async def _collect_market_data(self) -> dict[str, Any] | None:
        """Collect live market data and compute indicators."""

        try:
            symbol = self.config["trading"]["symbol"]
            timeframe = self.config["trading"].get("timeframe", "H1")

            await self._ensure_broker_connection()

            price_tuple = await self.execution.adapter.current_price(symbol)
            if price_tuple is None:
                raise RuntimeError("Failed to obtain current price from broker")

            bid, ask = price_tuple
            mid_price = (bid + ask) / 2
            spread = ask - bid

            lookback = max(self.bb_tool.period * 3, 200)
            price_history = await self._fetch_price_history(symbol, timeframe, lookback)

            rsi_result = self.rsi_tool.execute(prices=price_history)
            macd_result = self.macd_tool.execute(prices=price_history)
            bb_result = self.bb_tool.execute(prices=price_history)
            technical_overview_result = self.technical_overview.execute(prices=price_history)
            market_context_result = self.market_context_tool.execute(prices=price_history)

            for result in (
                rsi_result,
                macd_result,
                bb_result,
                technical_overview_result,
                market_context_result,
            ):
                if not result.success:
                    raise RuntimeError(result.error or "Indicator execution failed")

            account_info = await self.execution.adapter.account_info()
            positions = await self.execution.adapter.open_positions(symbol=symbol)

            position_state = None
            if positions:
                position = positions[0]
                position_state = {
                    "direction": position.direction,
                    "volume": position.volume,
                    "profit": position.profit,
                }

            account_data = None
            if account_info:
                account_data = {
                    "account_id": account_info.account_id,
                    "balance": account_info.balance,
                    "equity": account_info.equity,
                    "margin": account_info.margin,
                    "free_margin": account_info.free_margin,
                    "margin_level": account_info.margin_level,
                }

            timestamp = datetime.utcnow()

            return {
                "price": {
                    "bid": bid,
                    "ask": ask,
                    "mid": mid_price,
                    "spread": spread,
                },
                "history": price_history,
                "indicators": {
                    "rsi": rsi_result.value,
                    "macd": macd_result.value,
                    "bollinger_bands": bb_result.value,
                },
                "indicator_confidence": {
                    "rsi": rsi_result.confidence,
                    "macd": macd_result.confidence,
                    "bollinger_bands": bb_result.confidence,
                },
                "technical_overview": {
                    "summary": technical_overview_result.value,
                    "confidence": technical_overview_result.confidence,
                },
                "market_context": {
                    **market_context_result.value,
                    "confidence": market_context_result.confidence,
                },
                "account": account_data,
                "position": position_state,
                "timestamp": timestamp,
            }
        except Exception as exc:
            logger.error("Failed to collect market data: %s", exc)
            return None

    async def _analyze_market(self, market_data: dict[str, Any]) -> dict[str, Any]:
        """Analyze market data with the INoT orchestrator."""

        fused_context: FusedContext | None = None
        try:
            fused_context = self._build_fused_context(market_data)
            memory_snapshot = self.memory.load_snapshot(
                symbol=self.config["trading"]["symbol"]
            )
            decision = self.circuit_breaker.call(
                self.inot.reason,
                fused_context,
                memory_snapshot,
            )
            agent_outputs = decision.agent_outputs or []

            return {
                "market_data": market_data,
                "fused_context": fused_context,
                "memory_snapshot": memory_snapshot,
                "decision": decision,
                "agents": agent_outputs,
            }
        except Exception as exc:
            logger.error("INoT analysis failed: %s", exc)
            fallback_decision = InotDecision(
                action="HOLD",
                lots=0.0,
                confidence=0.0,
                reasoning=f"Analysis failed: {exc}",
            )
            return {
                "market_data": market_data,
                "fused_context": fused_context,
                "memory_snapshot": None,
                "decision": fallback_decision,
                "agents": [],
                "failed": True,
            }

    def _select_strategy(self, analysis: dict[str, Any]) -> Any:
        """Select the best strategy for the current context."""

        context = analysis.get("fused_context")
        if context is None:
            # Fallback to first available strategy if context unavailable
            return self.strategy_library[0]

        try:
            strategy = self.strategy_selector.select_best(context, self.strategy_library)
            if strategy:
                return strategy

            evaluated = [s for s in self.strategy_library if s.evaluate(context)]
            if evaluated:
                return evaluated[0]
        except Exception as exc:
            logger.error("Strategy selection failed: %s", exc)

        return self.strategy_library[0]

    def _make_decision(self, analysis: dict[str, Any], strategy: Any) -> StoredDecision:
        """Combine INoT decision with strategy output."""

        inot_decision: InotDecision = analysis["decision"]
        fused_context: FusedContext | None = analysis.get("fused_context")
        market_data = analysis["market_data"]

        if fused_context is None:
            fused_context = self._build_fused_context(market_data)

        strategy_signal = strategy.generate_signal(fused_context)

        lots = self._calculate_position_size(inot_decision, strategy_signal, market_data)
        stop_loss = inot_decision.stop_loss or strategy_signal.stop_loss
        take_profit = inot_decision.take_profit or strategy_signal.take_profit
        action = inot_decision.action or strategy_signal.action
        confidence = max(inot_decision.confidence, strategy_signal.confidence)

        if action not in {"BUY", "SELL"}:
            lots = 0.0
            stop_loss = None
            take_profit = None

        indicator_data = market_data["indicators"]
        market_context = market_data["market_context"]
        agent_outputs = analysis.get("agents", [])

        decision_id = f"{fused_context.symbol}-{datetime.utcnow().isoformat()}"

        return StoredDecision(
            id=decision_id,
            timestamp=datetime.utcnow(),
            symbol=fused_context.symbol,
            action=action,
            confidence=confidence,
            lots=lots,
            stop_loss=stop_loss,
            take_profit=take_profit,
            price=market_data["price"]["mid"],
            rsi=(indicator_data.get("rsi") or {}).get("rsi"),
            macd=(indicator_data.get("macd") or {}).get("macd"),
            bb_position=(indicator_data.get("bollinger_bands") or {}).get("band_position"),
            regime=market_context.get("regime"),
            signal_agent_output=self._find_agent_output(agent_outputs, "Signal"),
            risk_agent_output=self._find_agent_output(agent_outputs, "Risk"),
            context_agent_output=self._find_agent_output(agent_outputs, "Context"),
            synthesis_agent_output=self._find_agent_output(agent_outputs, "Synthesis"),
        )

    def _store_decision(self, decision: StoredDecision) -> None:
        """Persist the decision to the memory store."""

        if decision.lots <= 0:
            logger.info("Skipping persistence for non-actionable decision %s", decision.id)
            return

        try:
            self.memory.save_decision(decision)
            logger.info("Persisted decision %s", decision.id)
        except StorageError as exc:
            logger.error("Failed to store decision %s: %s", decision.id, exc)

    async def _execute_trade(self, decision: StoredDecision, inot_decision: InotDecision) -> None:
        """Execute trade through the execution bridge."""

        if decision.action not in {"BUY", "SELL"}:
            logger.info("Decision %s is %s; skipping execution", decision.id, decision.action)
            return

        await self._ensure_broker_connection()

        direction = OrderDirection.LONG if decision.action == "BUY" else OrderDirection.SHORT
        signal = Signal(
            symbol=decision.symbol,
            direction=direction,
            size=decision.lots,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
            confidence=decision.confidence,
            reasoning=inot_decision.reasoning,
            metadata={"decision_id": decision.id},
        )

        signal_id = self.execution.receive_signal(signal)
        result = await self.execution.execute_order(signal_id, signal)

        if result.success:
            logger.info(
                "Trade executed for %s (order %s)", decision.id, result.order_id
            )
        else:
            logger.error(
                "Trade execution failed for %s: %s", decision.id, result.error_message
            )

    def _update_metrics(self) -> None:
        """Update health and performance metrics."""

        health = self.health_monitor.evaluate_all()
        logger.debug("System health: %s", health)

    async def _handle_error(self, error: Exception) -> None:
        """Handle errors gracefully."""

        logger.error("Handling error: %s", error)
        await asyncio.sleep(1)

    def stop(self) -> None:
        """Stop the trading agent."""

        logger.info("Stopping trading agent...")
        self.running = False

    async def _ensure_broker_connection(self) -> None:
        """Ensure the execution adapter is connected."""

        adapter = self.execution.adapter
        if not adapter.is_connected():
            connected = await adapter.connect()
            if not connected:
                raise RuntimeError("Unable to establish MT5 connection")

    async def _fetch_price_history(
        self, symbol: str, timeframe: str, lookback: int
    ) -> list[float]:
        """Fetch historical prices asynchronously."""

        return await asyncio.to_thread(
            self._fetch_price_history_sync, symbol, timeframe, lookback
        )

    def _fetch_price_history_sync(self, symbol: str, timeframe: str, lookback: int) -> list[float]:
        """Blocking helper to fetch price history from MT5."""

        try:
            import MetaTrader5 as mt5
        except ImportError as exc:
            raise RuntimeError("MetaTrader5 package is required for live data access") from exc

        timeframe_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }

        mt5_timeframe = timeframe_map.get(timeframe.upper(), mt5.TIMEFRAME_H1)
        rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, lookback)
        if rates is None:
            raise RuntimeError(f"Failed to fetch historical rates for {symbol}")

        return [float(rate["close"]) for rate in rates]

    def _build_fused_context(self, market_data: dict[str, Any]) -> FusedContext:
        """Build fused context object from market data."""

        indicators = market_data.get("indicators", {})
        technical_overview = market_data.get("technical_overview", {}).get("summary", {})
        market_context = market_data.get("market_context", {})
        account = market_data.get("account") or {}
        position = market_data.get("position") or {}

        return FusedContext(
            symbol=self.config["trading"]["symbol"],
            price=market_data["price"]["mid"],
            timestamp=market_data["timestamp"],
            rsi=(indicators.get("rsi") or {}).get("rsi"),
            rsi_signal=(indicators.get("rsi") or {}).get("signal"),
            macd=(indicators.get("macd") or {}).get("macd"),
            macd_signal_line=(indicators.get("macd") or {}).get("signal"),
            macd_histogram=(indicators.get("macd") or {}).get("histogram"),
            macd_signal=(indicators.get("macd") or {}).get("trading_signal"),
            bb_upper=(indicators.get("bollinger_bands") or {}).get("upper_band"),
            bb_middle=(indicators.get("bollinger_bands") or {}).get("middle_band"),
            bb_lower=(indicators.get("bollinger_bands") or {}).get("lower_band"),
            bb_position=(indicators.get("bollinger_bands") or {}).get("band_position"),
            technical_signal=technical_overview.get("aggregated_signal"),
            technical_confidence=market_data.get("technical_overview", {}).get("confidence"),
            agreement_score=technical_overview.get("agreement_score"),
            atr=market_context.get("volatility"),
            volume=None,
            spread=market_data["price"].get("spread"),
            latest_news=None,
            sentiment=None,
            current_position=position.get("direction", "FLAT"),
            unrealized_pnl=position.get("profit"),
            account_equity=account.get("equity"),
            free_margin=account.get("free_margin"),
            risk_percent=float(self.config.get("risk", {}).get("max_position_size", 0.02)),
            regime=market_context.get("regime"),
            volatility=market_context.get("volatility"),
            volatility_normalized=market_context.get("volatility_normalized"),
            trend_strength=market_context.get("trend_strength"),
            has_major_news=False,
            market_volatility=market_context.get("regime"),
        )

    def _calculate_position_size(self, inot_decision: InotDecision, strategy_signal: Any, market_data: dict[str, Any]) -> float:
        """Derive a safe position size based on risk settings and signals."""

        risk_config = self.config.get("risk", {})
        max_lots = float(risk_config.get("max_position_size", 0.1))

        suggested_lots = inot_decision.lots
        if not suggested_lots and getattr(strategy_signal, "metadata", None):
            suggested_lots = strategy_signal.metadata.get("position_size")
        if not suggested_lots and hasattr(strategy_signal, "position_size"):
            suggested_lots = getattr(strategy_signal, "position_size")

        if not suggested_lots:
            suggested_lots = max_lots

        lots = min(float(suggested_lots), max_lots)
        return max(round(lots, 2), 0.0)

    @staticmethod
    def _find_agent_output(agents: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
        """Extract agent output by name."""

        for agent in agents:
            if agent.get("agent") == name:
                return agent
        return None


async def main():
    """Entry point."""
    # Create data directory for memory.db
    os.makedirs("data", exist_ok=True)

    try:
        agent = TradingAgent(config_path="config/production.yaml")

        # Run the loop for a few iterations for E2E test
        logger.info("Running agent for 3 iterations (E2E Test)...")
        for _ in range(3):
            await agent.run_single_iteration()
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
    finally:
        # Agent stop is handled by the loop logic in a real scenario,
        # but for this test, we just log the end.
        logger.info("E2E Test finished.")
