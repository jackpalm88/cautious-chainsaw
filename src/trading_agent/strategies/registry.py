"""
Strategy Registry - SQLite Database for Strategy Management
Stores strategies, performance metrics, and metadata
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

from .tester import BacktestResult


class StrategyRegistry:
    """SQLite-based strategy registry"""

    def __init__(self, db_path: str | Path = "data/strategies.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Strategies table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    dsl_content TEXT NOT NULL,
                    author TEXT,
                    version TEXT,
                    priority INTEGER DEFAULT 5,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """
            )

            # Backtest results table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS backtest_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    total_profit REAL,
                    total_loss REAL,
                    net_profit REAL,
                    win_rate REAL,
                    profit_factor REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    avg_trade_duration_ms REAL,
                    backtest_duration_ms REAL,
                    tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (strategy_name) REFERENCES strategies(name)
                )
            """
            )

            # Performance index
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_backtest_performance
                ON backtest_results(strategy_name, net_profit DESC, win_rate DESC)
            """
            )

            conn.commit()

    def register_strategy(
        self,
        name: str,
        dsl_content: str | dict,
        description: str = "",
        author: str = "",
        version: str = "1.0.0",
        priority: int = 5,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        Register new strategy

        Args:
            name: Strategy name
            dsl_content: Strategy DSL (YAML string or dict)
            description: Strategy description
            author: Strategy author
            version: Strategy version
            priority: Strategy priority (1-10)
            metadata: Additional metadata

        Returns:
            Strategy ID
        """
        # Convert dict to JSON string if needed
        if isinstance(dsl_content, dict):
            dsl_content = json.dumps(dsl_content, indent=2)

        metadata_json = json.dumps(metadata) if metadata else None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO strategies
                (name, description, dsl_content, author, version, priority, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (name, description, dsl_content, author, version, priority, metadata_json),
            )

            conn.commit()
            return cursor.lastrowid

    def update_strategy(
        self,
        name: str,
        dsl_content: str | dict | None = None,
        description: str | None = None,
        priority: int | None = None,
        active: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Update existing strategy

        Args:
            name: Strategy name
            dsl_content: New DSL content (optional)
            description: New description (optional)
            priority: New priority (optional)
            active: New active status (optional)
            metadata: New metadata (optional)

        Returns:
            True if updated, False if not found
        """
        updates = []
        params = []

        if dsl_content is not None:
            if isinstance(dsl_content, dict):
                dsl_content = json.dumps(dsl_content, indent=2)
            updates.append("dsl_content = ?")
            params.append(dsl_content)

        if description is not None:
            updates.append("description = ?")
            params.append(description)

        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)

        if active is not None:
            updates.append("active = ?")
            params.append(1 if active else 0)

        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(name)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                f"""
                UPDATE strategies
                SET {', '.join(updates)}
                WHERE name = ?
            """,
                params,
            )

            conn.commit()
            return cursor.rowcount > 0

    def get_strategy(self, name: str) -> dict[str, Any] | None:
        """Get strategy by name"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM strategies WHERE name = ?
            """,
                (name,),
            )

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def list_strategies(
        self, active_only: bool = False, min_priority: int = 0
    ) -> list[dict[str, Any]]:
        """
        List all strategies

        Args:
            active_only: Only return active strategies
            min_priority: Minimum priority threshold

        Returns:
            List of strategy dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM strategies WHERE priority >= ?"
            params = [min_priority]

            if active_only:
                query += " AND active = 1"

            query += " ORDER BY priority DESC, created_at DESC"

            cursor.execute(query, params)

            return [dict(row) for row in cursor.fetchall()]

    def delete_strategy(self, name: str) -> bool:
        """Delete strategy and its backtest results"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Delete backtest results first (foreign key)
            cursor.execute(
                """
                DELETE FROM backtest_results WHERE strategy_name = ?
            """,
                (name,),
            )

            # Delete strategy
            cursor.execute(
                """
                DELETE FROM strategies WHERE name = ?
            """,
                (name,),
            )

            conn.commit()
            return cursor.rowcount > 0

    def save_backtest_result(self, result: BacktestResult) -> int:
        """Save backtest result"""
        metadata_json = json.dumps(result.metadata) if result.metadata else None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO backtest_results
                (strategy_name, total_trades, winning_trades, losing_trades,
                 total_profit, total_loss, net_profit, win_rate, profit_factor,
                 sharpe_ratio, max_drawdown, avg_trade_duration_ms,
                 backtest_duration_ms, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    result.strategy_name,
                    result.total_trades,
                    result.winning_trades,
                    result.losing_trades,
                    result.total_profit,
                    result.total_loss,
                    result.net_profit,
                    result.win_rate,
                    result.profit_factor,
                    result.sharpe_ratio,
                    result.max_drawdown,
                    result.avg_trade_duration_ms,
                    result.backtest_duration_ms,
                    metadata_json,
                ),
            )

            conn.commit()
            return cursor.lastrowid

    def get_backtest_results(self, strategy_name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get backtest results for strategy"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM backtest_results
                WHERE strategy_name = ?
                ORDER BY tested_at DESC
                LIMIT ?
            """,
                (strategy_name, limit),
            )

            return [dict(row) for row in cursor.fetchall()]

    def get_best_strategies(
        self, metric: str = "net_profit", limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Get best performing strategies

        Args:
            metric: Metric to rank by (net_profit, win_rate, sharpe_ratio, etc.)
            limit: Number of strategies to return

        Returns:
            List of strategy dictionaries with latest backtest results
        """
        valid_metrics = [
            "net_profit",
            "win_rate",
            "profit_factor",
            "sharpe_ratio",
            "total_trades",
        ]
        if metric not in valid_metrics:
            metric = "net_profit"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get latest backtest result for each strategy
            cursor.execute(
                f"""
                SELECT s.*, b.*
                FROM strategies s
                INNER JOIN (
                    SELECT strategy_name, MAX(tested_at) as latest_test
                    FROM backtest_results
                    GROUP BY strategy_name
                ) latest ON s.name = latest.strategy_name
                INNER JOIN backtest_results b
                    ON b.strategy_name = latest.strategy_name
                    AND b.tested_at = latest.latest_test
                WHERE s.active = 1
                ORDER BY b.{metric} DESC
                LIMIT ?
            """,
                (limit,),
            )

            return [dict(row) for row in cursor.fetchall()]
