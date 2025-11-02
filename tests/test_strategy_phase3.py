"""
Tests for Strategy Builder Phase 3: Tester + Registry + Selector
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.trading_agent.decision.engine import FusedContext
from src.trading_agent.strategies.compiler import StrategyCompiler
from src.trading_agent.strategies.registry import StrategyRegistry
from src.trading_agent.strategies.selector import StrategySelector
from src.trading_agent.strategies.tester import StrategyTester


class TestStrategyTester:
    """Tests for StrategyTester"""

    @pytest.fixture
    def tester(self):
        return StrategyTester(initial_balance=10000.0)

    @pytest.fixture
    def strategy(self):
        compiler = StrategyCompiler()
        dsl = {
            "name": "test_strategy",
            "description": "Test strategy",
            "metadata": {"author": "Test", "version": "1.0.0", "priority": 5},
            "conditions": [{"field": "rsi", "operator": "<", "value": 30}],
            "action": "BUY",
            "risk": {
                "stop_loss_percent": 2.0,
                "take_profit_percent": 4.0,
                "max_risk_per_trade_percent": 1.0,
            },
        }
        return compiler.compile(dsl)

    @pytest.fixture
    def contexts(self):
        """Generate test contexts"""
        base_time = datetime.now()
        contexts = []

        # Oversold condition (RSI < 30)
        for i in range(10):
            contexts.append(
                FusedContext(
                    symbol="EURUSD",
                    price=1.08 + i * 0.001,
                    timestamp=base_time + timedelta(seconds=i),
                    rsi=25.0,  # Oversold
                    regime="ranging",
                )
            )

        # Normal condition (RSI > 30)
        for i in range(10):
            contexts.append(
                FusedContext(
                    symbol="EURUSD",
                    price=1.09 + i * 0.001,
                    timestamp=base_time + timedelta(seconds=10 + i),
                    rsi=50.0,  # Normal
                    regime="ranging",
                )
            )

        return contexts

    def test_backtest_basic(self, tester, strategy, contexts):
        """Test basic backtest"""
        result = tester.backtest(strategy, contexts)

        assert result.strategy_name == "test_strategy"
        assert result.total_trades >= 0
        assert result.backtest_duration_ms > 0

    def test_backtest_with_trades(self, tester, strategy, contexts):
        """Test backtest with trades"""
        result = tester.backtest(strategy, contexts)

        # Should have some trades (RSI < 30 triggers BUY)
        assert result.total_trades > 0
        assert result.winning_trades + result.losing_trades == result.total_trades

    def test_backtest_metrics(self, tester, strategy, contexts):
        """Test backtest metrics calculation"""
        result = tester.backtest(strategy, contexts)

        # Metrics should be calculated
        assert 0.0 <= result.win_rate <= 1.0
        assert result.profit_factor >= 0.0
        assert 0.0 <= result.max_drawdown <= 1.0

    def test_backtest_no_trades(self, tester):
        """Test backtest with no matching conditions"""
        compiler = StrategyCompiler()
        dsl = {
            "name": "impossible_strategy",
            "description": "Never triggers",
            "metadata": {"author": "Test", "version": "1.0.0"},
            "conditions": [{"field": "rsi", "operator": "<", "value": 0}],
            "action": "BUY",
            "risk": {
                "stop_loss_percent": 2.0,
                "max_risk_per_trade_percent": 1.0,
            },
        }
        strategy = compiler.compile(dsl)

        contexts = [
            FusedContext(
                symbol="EURUSD",
                price=1.08,
                timestamp=datetime.now(),
                rsi=50.0,
                regime="ranging",
            )
        ]

        result = tester.backtest(strategy, contexts)

        assert result.total_trades == 0
        assert result.net_profit == 0.0


class TestStrategyRegistry:
    """Tests for StrategyRegistry"""

    @pytest.fixture
    def registry(self):
        # Use temporary database
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            db_path = f.name

        registry = StrategyRegistry(db_path)
        yield registry

        # Cleanup - close all connections first (Windows file locking)
        import gc

        del registry
        gc.collect()  # Force garbage collection to close connections

        # Wait a bit for Windows to release the file
        import time

        time.sleep(0.1)

        Path(db_path).unlink(missing_ok=True)

    def test_register_strategy(self, registry):
        """Test strategy registration"""
        dsl = {
            "name": "test_strategy",
            "description": "Test",
            "conditions": [],
            "action": "BUY",
            "risk": {"stop_loss_percent": 1.0, "max_risk_per_trade_percent": 1.0},
        }

        strategy_id = registry.register_strategy(
            name="test_strategy",
            dsl_content=dsl,
            description="Test strategy",
            author="Test",
            version="1.0.0",
        )

        assert strategy_id > 0

    def test_get_strategy(self, registry):
        """Test get strategy"""
        dsl = {"name": "test", "conditions": [], "action": "BUY", "risk": {}}

        registry.register_strategy(name="test", dsl_content=dsl)

        strategy = registry.get_strategy("test")

        assert strategy is not None
        assert strategy["name"] == "test"

    def test_list_strategies(self, registry):
        """Test list strategies"""
        for i in range(3):
            dsl = {"name": f"test_{i}", "conditions": [], "action": "BUY", "risk": {}}
            registry.register_strategy(name=f"test_{i}", dsl_content=dsl, priority=i)

        strategies = registry.list_strategies()

        assert len(strategies) == 3

    def test_update_strategy(self, registry):
        """Test update strategy"""
        dsl = {"name": "test", "conditions": [], "action": "BUY", "risk": {}}

        registry.register_strategy(name="test", dsl_content=dsl, priority=5)

        updated = registry.update_strategy(name="test", priority=8, active=False)

        assert updated is True

        strategy = registry.get_strategy("test")
        assert strategy["priority"] == 8
        assert strategy["active"] == 0

    def test_delete_strategy(self, registry):
        """Test delete strategy"""
        dsl = {"name": "test", "conditions": [], "action": "BUY", "risk": {}}

        registry.register_strategy(name="test", dsl_content=dsl)

        deleted = registry.delete_strategy("test")

        assert deleted is True

        strategy = registry.get_strategy("test")
        assert strategy is None

    def test_save_backtest_result(self, registry):
        """Test save backtest result"""
        from src.trading_agent.strategies.tester import BacktestResult

        dsl = {"name": "test", "conditions": [], "action": "BUY", "risk": {}}
        registry.register_strategy(name="test", dsl_content=dsl)

        result = BacktestResult(
            strategy_name="test",
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            total_profit=600.0,
            total_loss=300.0,
            net_profit=300.0,
            win_rate=0.6,
            profit_factor=2.0,
            sharpe_ratio=1.5,
            max_drawdown=0.1,
            avg_trade_duration_ms=1000.0,
            backtest_duration_ms=500.0,
            metadata={},
        )

        result_id = registry.save_backtest_result(result)

        assert result_id > 0

    def test_get_backtest_results(self, registry):
        """Test get backtest results"""
        from src.trading_agent.strategies.tester import BacktestResult

        dsl = {"name": "test", "conditions": [], "action": "BUY", "risk": {}}
        registry.register_strategy(name="test", dsl_content=dsl)

        # Save multiple results
        for i in range(3):
            result = BacktestResult(
                strategy_name="test",
                total_trades=10 + i,
                winning_trades=6,
                losing_trades=4,
                total_profit=600.0,
                total_loss=300.0,
                net_profit=300.0 + i * 100,
                win_rate=0.6,
                profit_factor=2.0,
                sharpe_ratio=1.5,
                max_drawdown=0.1,
                avg_trade_duration_ms=1000.0,
                backtest_duration_ms=500.0,
                metadata={},
            )
            registry.save_backtest_result(result)

        results = registry.get_backtest_results("test", limit=2)

        assert len(results) == 2


class TestStrategySelector:
    """Tests for StrategySelector"""

    @pytest.fixture
    def registry(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            db_path = f.name

        registry = StrategyRegistry(db_path)
        yield registry

        # Cleanup - close all connections first (Windows file locking)
        import gc

        del registry
        gc.collect()

        import time

        time.sleep(0.1)

        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def selector(self, registry):
        return StrategySelector(registry)

    @pytest.fixture
    def strategies(self, registry):
        """Create test strategies"""
        from src.trading_agent.strategies.compiler import StrategyCompiler
        from src.trading_agent.strategies.tester import BacktestResult

        compiler = StrategyCompiler()
        strategies = []

        for i in range(3):
            dsl = {
                "name": f"strategy_{i}",
                "description": f"Test strategy {i}",
                "metadata": {
                    "author": "Test",
                    "version": "1.0.0",
                    "priority": 5 + i,
                    "active_regimes": ["ranging"],
                },
                "conditions": [{"field": "rsi", "operator": "<", "value": 30}],
                "action": "BUY",
                "risk": {
                    "stop_loss_percent": 2.0,
                    "max_risk_per_trade_percent": 1.0,
                },
            }

            strategy = compiler.compile(dsl)
            strategies.append(strategy)

            # Register in database
            registry.register_strategy(
                name=f"strategy_{i}",
                dsl_content=dsl,
                priority=5 + i,
            )

            # Save backtest result
            result = BacktestResult(
                strategy_name=f"strategy_{i}",
                total_trades=20 + i * 10,
                winning_trades=12 + i * 5,
                losing_trades=8,
                total_profit=1000.0 + i * 500,
                total_loss=400.0,
                net_profit=600.0 + i * 500,
                win_rate=0.6 + i * 0.1,
                profit_factor=2.0 + i * 0.5,
                sharpe_ratio=1.5 + i * 0.3,
                max_drawdown=0.1,
                avg_trade_duration_ms=1000.0,
                backtest_duration_ms=500.0,
                metadata={},
            )
            registry.save_backtest_result(result)

        return strategies

    def test_select_best(self, selector, strategies):
        """Test select best strategy"""
        context = FusedContext(
            symbol="EURUSD",
            price=1.08,
            timestamp=datetime.now(),
            rsi=25.0,
            regime="ranging",
        )

        best = selector.select_best(context, strategies, metric="net_profit")

        assert best is not None
        assert best.name in ["strategy_0", "strategy_1", "strategy_2"]

    def test_select_ensemble(self, selector, strategies):
        """Test select ensemble"""
        context = FusedContext(
            symbol="EURUSD",
            price=1.08,
            timestamp=datetime.now(),
            rsi=25.0,
            regime="ranging",
        )

        ensemble = selector.select_ensemble(context, strategies, top_n=2, metric="sharpe_ratio")

        assert len(ensemble) <= 2
        if ensemble:
            # Weights should sum to 1.0
            total_weight = sum(weight for _, weight in ensemble)
            assert abs(total_weight - 1.0) < 0.01

    def test_get_strategy_rankings(self, selector, strategies):
        """Test get strategy rankings"""
        rankings = selector.get_strategy_rankings(strategies, metric="net_profit")

        assert len(rankings) == 3
        # Should be sorted by net_profit descending
        for i in range(len(rankings) - 1):
            assert rankings[i]["net_profit"] >= rankings[i + 1]["net_profit"]
