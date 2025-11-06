"""Utility service that produces deterministic backtest outputs."""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime, timedelta


class BacktestService:
    """Generate synthetic yet consistent backtest reports."""

    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}

    def list_strategies(self) -> list[dict]:
        """Return available strategy templates."""

        return [
            {
                "id": "momentum-pulse-v5",
                "name": "Momentum Pulse v5",
                "description": "Momentum breakout detection with volatility filters.",
                "category": "momentum",
            },
            {
                "id": "carry-radar-v2",
                "name": "Carry Radar v2",
                "description": "Carry yield harvesting with macro risk overlays.",
                "category": "carry",
            },
            {
                "id": "mean-reversion-v3",
                "name": "Mean Reversion v3",
                "description": "Short-term reversion with liquidity-weighted signals.",
                "category": "mean-reversion",
            },
        ]

    def run_backtest(self, *, strategy_id: str, symbol: str, bars: int = 240) -> dict:
        """Return a cached or freshly generated backtest result."""

        cache_key = f"{strategy_id}:{symbol}:{bars}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        rng = random.Random(cache_key)
        base_equity = 100_000.0
        timestamp = datetime.now(UTC)

        equity_curve: list[dict] = []
        drawdown_curve: list[dict] = []
        trades: list[dict] = []
        equity = base_equity
        peak_equity = base_equity

        for _ in range(bars):
            timestamp -= timedelta(minutes=5)
            drift = rng.normalvariate(120.0, 260.0)
            equity = max(base_equity * 0.4, equity + drift)
            peak_equity = max(peak_equity, equity)
            drawdown = (equity - peak_equity) / peak_equity
            equity_curve.append({"timestamp": int(timestamp.timestamp() * 1000), "equity": round(equity, 2)})
            drawdown_curve.append({"timestamp": int(timestamp.timestamp() * 1000), "drawdown": round(drawdown * 100, 2)})

            if rng.random() < 0.2:
                entry_time = timestamp - timedelta(minutes=rng.randint(10, 180))
                exit_time = timestamp
                direction = rng.choice(["LONG", "SHORT"])
                profit = round(rng.normalvariate(180.0, 320.0), 2)
                trades.append(
                    {
                        "id": str(uuid.uuid4()),
                        "entryTime": int(entry_time.timestamp() * 1000),
                        "exitTime": int(exit_time.timestamp() * 1000),
                        "direction": direction,
                        "profit": profit,
                        "symbol": symbol,
                    }
                )

        equity_curve.sort(key=lambda item: item["timestamp"])
        drawdown_curve.sort(key=lambda item: item["timestamp"])

        final_equity = equity_curve[-1]["equity"] if equity_curve else base_equity
        net_profit = final_equity - base_equity
        max_drawdown = min(point["drawdown"] for point in drawdown_curve)
        win_rate = rng.uniform(0.5, 0.7)
        sharpe = rng.uniform(1.4, 2.3)

        result = {
            "id": str(uuid.uuid4()),
            "strategy": strategy_id,
            "symbol": symbol,
            "generatedAt": datetime.now(UTC).isoformat(),
            "metrics": {
                "netProfit": round(net_profit, 2),
                "maxDrawdown": round(max_drawdown, 2),
                "sharpeRatio": round(sharpe, 2),
                "winRate": round(win_rate, 2),
                "trades": len(trades),
            },
            "equityCurve": equity_curve,
            "drawdownCurve": drawdown_curve,
            "trades": trades,
        }

        self._cache[cache_key] = result
        return result


__all__ = ["BacktestService"]
