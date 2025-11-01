"""
StrategyCompiler - Compiles DSL definitions into executable strategies
"""

import json
import operator
from pathlib import Path
from typing import TYPE_CHECKING

import jsonschema
import yaml

if TYPE_CHECKING:
    from ..decision.engine import FusedContext

from .base_strategy import BaseStrategy, StrategySignal


class StrategyCompiler:
    """
    Compiles strategy DSL (YAML/JSON) into executable Python strategy objects.

    Uses JSON Schema validation and dynamic class generation.
    """

    # Operator mapping
    OPERATORS = {
        "<": operator.lt,
        "<=": operator.le,
        ">": operator.gt,
        ">=": operator.ge,
        "==": operator.eq,
        "!=": operator.ne,
    }

    def __init__(self, schema_path: str | None = None):
        """
        Initialize compiler.

        Args:
            schema_path: Path to JSON Schema file (optional)
        """
        if schema_path is None:
            # Use default schema
            schema_path = Path(__file__).parent / "dsl" / "schema.json"

        with open(schema_path) as f:
            self.schema = json.load(f)

    def compile_from_file(self, filepath: str) -> BaseStrategy:
        """
        Compile strategy from YAML or JSON file.

        Args:
            filepath: Path to strategy file (.yaml, .yml, or .json)

        Returns:
            Compiled BaseStrategy instance

        Raises:
            ValueError: If file format is invalid
            jsonschema.ValidationError: If DSL doesn't match schema
        """
        path = Path(filepath)

        # Load file
        with open(path) as f:
            if path.suffix in [".yaml", ".yml"]:
                dsl = yaml.safe_load(f)
            elif path.suffix == ".json":
                dsl = json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")

        return self.compile(dsl)

    def compile(self, dsl: dict) -> BaseStrategy:
        """
        Compile strategy from DSL dictionary.

        Args:
            dsl: Strategy definition dictionary

        Returns:
            Compiled BaseStrategy instance

        Raises:
            jsonschema.ValidationError: If DSL doesn't match schema
        """
        # Validate against schema
        jsonschema.validate(instance=dsl, schema=self.schema)

        # Create dynamic strategy class
        class CompiledStrategy(BaseStrategy):
            """Dynamically compiled strategy from DSL"""

            def evaluate(self, context: "FusedContext") -> bool:
                """Check if all conditions are met"""
                # Check if strategy is active in current regime
                if not self.is_active(context):
                    return False

                # Evaluate all conditions (AND logic)
                for condition in self.conditions:
                    if not self._evaluate_condition(condition, context):
                        return False

                return True

            def generate_signal(self, context: "FusedContext") -> StrategySignal:
                """Generate trading signal"""
                # Calculate stop loss and take profit
                stop_loss = None
                take_profit = None

                if self.action == "BUY":
                    stop_loss = context.price * (1 - self.risk["stop_loss_percent"] / 100)
                    if "take_profit_percent" in self.risk:
                        take_profit = context.price * (1 + self.risk["take_profit_percent"] / 100)

                elif self.action == "SELL":
                    stop_loss = context.price * (1 + self.risk["stop_loss_percent"] / 100)
                    if "take_profit_percent" in self.risk:
                        take_profit = context.price * (1 - self.risk["take_profit_percent"] / 100)

                # Generate reasoning
                reasoning = self._generate_reasoning(context)

                # Calculate confidence (based on how many conditions are met)
                confidence = self._calculate_confidence(context)

                return StrategySignal(
                    action=self.action,
                    confidence=confidence,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    reasoning=reasoning,
                    metadata={
                        "strategy_name": self.name,
                        "strategy_version": self.metadata["version"],
                        "priority": self.metadata.get("priority", 5),
                    }
                )

            def _evaluate_condition(self, condition: dict, context: "FusedContext") -> bool:
                """Evaluate a single condition"""
                field = condition["field"]
                op = condition["operator"]
                value = condition["value"]

                # Get field value from context
                context_value = getattr(context, field, None)

                if context_value is None:
                    return False

                # Apply operator
                op_func = StrategyCompiler.OPERATORS[op]
                return op_func(context_value, value)

            def _calculate_confidence(self, context: "FusedContext") -> float:
                """Calculate strategy confidence"""
                # Base confidence from priority
                base_confidence = self.metadata.get("priority", 5) / 10

                # Bonus if technical_confidence is high
                if context.technical_confidence is not None:
                    base_confidence = (base_confidence + context.technical_confidence) / 2

                # Bonus if regime matches
                if self.is_active(context):
                    base_confidence *= 1.1

                return min(base_confidence, 0.95)

            def _generate_reasoning(self, context: "FusedContext") -> str:
                """Generate human-readable reasoning"""
                reasons = []

                for condition in self.conditions:
                    field = condition["field"]
                    op = condition["operator"]
                    value = condition["value"]
                    context_value = getattr(context, field, None)

                    reasons.append(f"{field} {op} {value} (actual: {context_value})")

                return f"{self.description}. Conditions: {', '.join(reasons)}"

        return CompiledStrategy(dsl)

    def validate(self, dsl: dict) -> tuple[bool, str]:
        """
        Validate DSL against schema without compiling.

        Args:
            dsl: Strategy definition dictionary

        Returns:
            (is_valid, error_message)
        """
        try:
            jsonschema.validate(instance=dsl, schema=self.schema)
            return True, ""
        except jsonschema.ValidationError as e:
            return False, str(e)
