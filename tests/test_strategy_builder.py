"""
Tests for Strategy Builder (DSL + Compiler)
"""

from datetime import datetime
from pathlib import Path

from src.trading_agent.decision.engine import FusedContext
from src.trading_agent.strategies.compiler import StrategyCompiler


class TestStrategyCompiler:
    """Test suite for StrategyCompiler"""

    def test_compile_from_yaml(self):
        """Test compiling strategy from YAML file"""
        compiler = StrategyCompiler()
        strategy_path = Path("data/strategies/rsi_oversold.yaml")

        strategy = compiler.compile_from_file(str(strategy_path))

        assert strategy.name == "rsi_oversold_mean_reversion"
        assert strategy.action == "BUY"
        assert strategy.metadata["version"] == "1.0.0"
        assert strategy.metadata["priority"] == 7

    def test_evaluate_conditions_met(self):
        """Test strategy evaluation when conditions are met"""
        compiler = StrategyCompiler()
        strategy_path = Path("data/strategies/rsi_oversold.yaml")
        strategy = compiler.compile_from_file(str(strategy_path))

        # Create context with conditions met
        context = FusedContext(
            symbol="EURUSD",
            price=1.0800,
            timestamp=datetime.now(),
            rsi=25.0,  # < 30 ✓
            macd_histogram=0.5,  # > 0 ✓
            regime="ranging",  # == "ranging" ✓
        )

        assert strategy.evaluate(context) is True

    def test_evaluate_conditions_not_met(self):
        """Test strategy evaluation when conditions are not met"""
        compiler = StrategyCompiler()
        strategy_path = Path("data/strategies/rsi_oversold.yaml")
        strategy = compiler.compile_from_file(str(strategy_path))

        # Create context with conditions NOT met
        context = FusedContext(
            symbol="EURUSD",
            price=1.0800,
            timestamp=datetime.now(),
            rsi=75.0,  # > 30 ✗
            macd_histogram=0.5,
            regime="ranging",
        )

        assert strategy.evaluate(context) is False

    def test_generate_signal(self):
        """Test signal generation"""
        compiler = StrategyCompiler()
        strategy_path = Path("data/strategies/rsi_oversold.yaml")
        strategy = compiler.compile_from_file(str(strategy_path))

        context = FusedContext(
            symbol="EURUSD",
            price=1.0800,
            timestamp=datetime.now(),
            rsi=25.0,
            macd_histogram=0.5,
            regime="ranging",
        )

        signal = strategy.generate_signal(context)

        assert signal.action == "BUY"
        assert signal.confidence > 0.0
        assert signal.stop_loss is not None
        assert signal.take_profit is not None
        assert signal.reasoning != ""

    def test_stop_loss_calculation(self):
        """Test stop loss calculation for BUY"""
        compiler = StrategyCompiler()
        strategy_path = Path("data/strategies/rsi_oversold.yaml")
        strategy = compiler.compile_from_file(str(strategy_path))

        context = FusedContext(
            symbol="EURUSD",
            price=1.0000,
            timestamp=datetime.now(),
            rsi=25.0,
            macd_histogram=0.5,
            regime="ranging",
        )

        signal = strategy.generate_signal(context)

        # SL should be 1.5% below entry for BUY
        expected_sl = 1.0000 * (1 - 1.5 / 100)
        assert abs(signal.stop_loss - expected_sl) < 0.0001

    def test_take_profit_calculation(self):
        """Test take profit calculation for BUY"""
        compiler = StrategyCompiler()
        strategy_path = Path("data/strategies/rsi_oversold.yaml")
        strategy = compiler.compile_from_file(str(strategy_path))

        context = FusedContext(
            symbol="EURUSD",
            price=1.0000,
            timestamp=datetime.now(),
            rsi=25.0,
            macd_histogram=0.5,
            regime="ranging",
        )

        signal = strategy.generate_signal(context)

        # TP should be 3.0% above entry for BUY
        expected_tp = 1.0000 * (1 + 3.0 / 100)
        assert abs(signal.take_profit - expected_tp) < 0.0001

    def test_regime_filtering(self):
        """Test that strategy is inactive in wrong regime"""
        compiler = StrategyCompiler()
        strategy_path = Path("data/strategies/rsi_oversold.yaml")
        strategy = compiler.compile_from_file(str(strategy_path))

        # Context with wrong regime
        context = FusedContext(
            symbol="EURUSD",
            price=1.0800,
            timestamp=datetime.now(),
            rsi=25.0,
            macd_histogram=0.5,
            regime="trending",  # Strategy wants "ranging"
        )

        assert strategy.evaluate(context) is False

    def test_validate_valid_dsl(self):
        """Test DSL validation with valid input"""
        compiler = StrategyCompiler()

        dsl = {
            "name": "test_strategy",
            "description": "Test strategy",
            "metadata": {
                "author": "Test",
                "version": "1.0.0"
            },
            "conditions": [
                {"field": "rsi", "operator": "<", "value": 30}
            ],
            "action": "BUY",
            "risk": {
                "stop_loss_percent": 1.0,
                "max_risk_per_trade_percent": 1.0
            }
        }

        is_valid, error = compiler.validate(dsl)
        assert is_valid is True
        assert error == ""

    def test_validate_invalid_dsl(self):
        """Test DSL validation with invalid input"""
        compiler = StrategyCompiler()

        dsl = {
            "name": "test_strategy",
            # Missing required fields
        }

        is_valid, error = compiler.validate(dsl)
        assert is_valid is False
        assert error != ""

    def test_metadata_in_signal(self):
        """Test that signal includes strategy metadata"""
        compiler = StrategyCompiler()
        strategy_path = Path("data/strategies/rsi_oversold.yaml")
        strategy = compiler.compile_from_file(str(strategy_path))

        context = FusedContext(
            symbol="EURUSD",
            price=1.0800,
            timestamp=datetime.now(),
            rsi=25.0,
            macd_histogram=0.5,
            regime="ranging",
        )

        signal = strategy.generate_signal(context)

        assert signal.metadata["strategy_name"] == "rsi_oversold_mean_reversion"
        assert signal.metadata["strategy_version"] == "1.0.0"
        assert signal.metadata["priority"] == 7
