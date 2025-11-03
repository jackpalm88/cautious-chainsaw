"""
Strategy Selector - Best Strategy Selection
Selects optimal strategy based on performance and context
"""

from typing import Any

from ..decision.engine import FusedContext
from .base_strategy import BaseStrategy
from .registry import StrategyRegistry


class StrategySelector:
    """Selects best strategy for current market context"""

    def __init__(self, registry: StrategyRegistry):
        self.registry = registry

    def select_best(
        self,
        context: FusedContext,
        strategies: list[BaseStrategy],
        metric: str = "net_profit",
        min_trades: int = 10,
    ) -> BaseStrategy | None:
        """
        Select best strategy for current context

        Args:
            context: Current market context
            strategies: List of candidate strategies
            metric: Performance metric to optimize
            min_trades: Minimum trades required for consideration

        Returns:
            Best strategy or None if no suitable strategy found
        """
        # Filter strategies that are active in current regime
        active_strategies = [s for s in strategies if s.is_active(context)]

        if not active_strategies:
            return None

        # Get performance data for active strategies
        strategy_scores: list[tuple[BaseStrategy, float]] = []

        for strategy in active_strategies:
            # Get latest backtest results
            results = self.registry.get_backtest_results(strategy.name, limit=1)

            if not results:
                continue

            result = results[0]

            # Filter by minimum trades
            if result["total_trades"] < min_trades:
                continue

            # Calculate score based on metric
            score = self._calculate_score(result, metric, context)
            strategy_scores.append((strategy, score))

        # Sort by score descending
        strategy_scores.sort(key=lambda x: x[1], reverse=True)

        # Return best strategy
        if strategy_scores:
            return strategy_scores[0][0]

        return None

    def select_ensemble(
        self,
        context: FusedContext,
        strategies: list[BaseStrategy],
        top_n: int = 3,
        metric: str = "sharpe_ratio",
    ) -> list[tuple[BaseStrategy, float]]:
        """
        Select ensemble of top strategies with weights

        Args:
            context: Current market context
            strategies: List of candidate strategies
            top_n: Number of strategies to select
            metric: Performance metric to optimize

        Returns:
            List of (strategy, weight) tuples
        """
        # Filter strategies that are active in current regime
        active_strategies = [s for s in strategies if s.is_active(context)]

        if not active_strategies:
            return []

        # Get performance data
        strategy_scores: list[tuple[BaseStrategy, float]] = []

        for strategy in active_strategies:
            results = self.registry.get_backtest_results(strategy.name, limit=1)

            if not results:
                continue

            result = results[0]
            score = self._calculate_score(result, metric, context)
            strategy_scores.append((strategy, score))

        # Sort by score descending
        strategy_scores.sort(key=lambda x: x[1], reverse=True)

        # Take top N
        top_strategies = strategy_scores[:top_n]

        # Calculate weights (normalized scores)
        total_score = sum(score for _, score in top_strategies)

        if total_score == 0:
            return []

        weighted_strategies = [
            (strategy, score / total_score) for strategy, score in top_strategies
        ]

        return weighted_strategies

    def _calculate_score(self, result: dict[str, Any], metric: str, context: FusedContext) -> float:
        """
        Calculate strategy score

        Args:
            result: Backtest result dictionary
            metric: Primary metric
            context: Current market context

        Returns:
            Composite score
        """
        # Get primary metric value
        primary_score = result.get(metric, 0.0)

        # Apply context-based adjustments
        regime_bonus = 1.0
        if context.regime:
            # Bonus for matching regime
            # (Would need regime-specific performance data for full implementation)
            regime_bonus = 1.1

        # Penalize low sample size
        sample_penalty = min(1.0, result.get("total_trades", 0) / 50.0)

        # Penalize high drawdown
        drawdown_penalty = 1.0 - min(0.5, result.get("max_drawdown", 0.0))

        # Composite score
        score = primary_score * regime_bonus * sample_penalty * drawdown_penalty

        return max(0.0, score)

    def get_strategy_rankings(
        self, strategies: list[BaseStrategy], metric: str = "net_profit"
    ) -> list[dict[str, Any]]:
        """
        Get ranked list of strategies with performance data

        Args:
            strategies: List of strategies to rank
            metric: Metric to rank by

        Returns:
            List of strategy info dictionaries with rankings
        """
        rankings: list[dict[str, Any]] = []

        for strategy in strategies:
            results = self.registry.get_backtest_results(strategy.name, limit=1)

            if not results:
                continue

            result = results[0]

            rankings.append(
                {
                    "strategy_name": strategy.name,
                    "description": strategy.description,
                    "priority": strategy.metadata.get("priority", 5),
                    "total_trades": result["total_trades"],
                    "net_profit": result["net_profit"],
                    "win_rate": result["win_rate"],
                    "profit_factor": result["profit_factor"],
                    "sharpe_ratio": result["sharpe_ratio"],
                    "max_drawdown": result["max_drawdown"],
                    metric: result.get(metric, 0.0),
                }
            )

        # Sort by metric descending
        rankings.sort(key=lambda x: x.get(metric, 0.0), reverse=True)

        # Add rank
        for i, ranking in enumerate(rankings, 1):
            ranking["rank"] = i

        return rankings
