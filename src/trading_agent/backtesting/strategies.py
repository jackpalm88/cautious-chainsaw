"""Example strategy implementations for the backtesting engine."""

from typing import Any

from .backtest_engine import BacktestBar, BacktestEngine


def rsi_strategy(engine: BacktestEngine, bar: BacktestBar) -> dict[str, Any]:
    """
    Simple RSI overbought/oversold strategy.

    Rules:
    - BUY when RSI < 30 (oversold)
    - SELL when RSI > 70 (overbought)
    - Use fixed 50-pip SL, 100-pip TP

    Args:
        engine: Backtest engine (provides tool access)
        bar: Current bar

    Returns:
        Trading signal dict or None
    """
    # Get historical prices (last 100 bars)
    idx = engine.current_bar_idx
    if idx < 100:
        return {}  # Not enough data

    prices = [b.close for b in engine.data[max(0, idx-100):idx+1]]

    # Calculate RSI
    rsi_result = engine.call_tool("calc_rsi", prices=prices, period=14)

    if rsi_result.get("error") or rsi_result.get("value") is None:
        return {}

    rsi = rsi_result["value"]
    confidence = rsi_result["confidence"]

    # Check if we already have an open position
    if engine.positions:
        return {}  # One position at a time

    # Trading logic
    signal = {}

    if rsi < 30 and confidence > 0.7:
        # Oversold - BUY signal
        signal = {
            "action": "buy",
            "size": 0.01,  # 0.01 lots
            "stop_loss": bar.close - 0.0050,  # 50 pips below
            "take_profit": bar.close + 0.0100,  # 100 pips above
            "reason": f"RSI oversold: {rsi:.1f}"
        }

    elif rsi > 70 and confidence > 0.7:
        # Overbought - SELL signal
        signal = {
            "action": "sell",
            "size": 0.01,
            "stop_loss": bar.close + 0.0050,  # 50 pips above
            "take_profit": bar.close - 0.0100,  # 100 pips below
            "reason": f"RSI overbought: {rsi:.1f}"
        }

    return signal


def macd_strategy(engine: BacktestEngine, bar: BacktestBar) -> dict[str, Any]:
    """
    MACD crossover strategy.

    Rules:
    - BUY when MACD crosses above signal line
    - SELL when MACD crosses below signal line
    - Dynamic SL based on recent ATR

    Args:
        engine: Backtest engine
        bar: Current bar

    Returns:
        Trading signal dict or None
    """
    idx = engine.current_bar_idx
    if idx < 50:
        return {}

    # Get prices
    prices = [b.close for b in engine.data[max(0, idx-50):idx+1]]

    # Calculate MACD (mock - in production use actual tool)
    # macd_result = engine.call_tool("calc_macd", prices=prices)

    # Simplified MACD logic for demo
    if len(prices) < 26:
        return {}

    # Mock MACD calculation
    ema12 = sum(prices[-12:]) / 12
    ema26 = sum(prices[-26:]) / 26
    macd = ema12 - ema26
    signal_line = sum([ema12 - ema26 for _ in range(9)]) / 9  # Simplified

    # Previous MACD for crossover detection
    if idx < 27:
        return {}

    prev_prices = [b.close for b in engine.data[max(0, idx-51):idx]]
    prev_ema12 = sum(prev_prices[-12:]) / 12
    prev_ema26 = sum(prev_prices[-26:]) / 26
    prev_macd = prev_ema12 - prev_ema26

    # Check for crossover
    if engine.positions:
        return {}

    signal = {}

    # Bullish crossover
    if prev_macd < signal_line and macd > signal_line:
        signal = {
            "action": "buy",
            "size": 0.01,
            "stop_loss": bar.close - 0.0030,  # 30 pips
            "take_profit": bar.close + 0.0060,  # 60 pips
            "reason": "MACD bullish crossover"
        }

    # Bearish crossover
    elif prev_macd > signal_line and macd < signal_line:
        signal = {
            "action": "sell",
            "size": 0.01,
            "stop_loss": bar.close + 0.0030,
            "take_profit": bar.close - 0.0060,
            "reason": "MACD bearish crossover"
        }

    return signal


def combined_rsi_macd_strategy(engine: BacktestEngine, bar: BacktestBar) -> dict[str, Any]:
    """
    Combined RSI + MACD confirmation strategy.

    Rules:
    - BUY when RSI < 40 AND MACD bullish crossover
    - SELL when RSI > 60 AND MACD bearish crossover
    - Higher confidence = larger position size

    Args:
        engine: Backtest engine
        bar: Current bar

    Returns:
        Trading signal dict or None
    """
    idx = engine.current_bar_idx
    if idx < 100:
        return {}

    if engine.positions:
        return {}

    # Get RSI
    prices = [b.close for b in engine.data[max(0, idx-100):idx+1]]
    rsi_result = engine.call_tool("calc_rsi", prices=prices, period=14)

    if rsi_result.get("error"):
        return {}

    rsi = rsi_result.get("value")
    rsi_confidence = rsi_result.get("confidence", 0)

    # Get MACD (simplified)
    if len(prices) < 26:
        return {}

    ema12 = sum(prices[-12:]) / 12
    ema26 = sum(prices[-26:]) / 26
    macd = ema12 - ema26

    # Previous MACD
    if idx < 27:
        return {}
    prev_prices = [b.close for b in engine.data[max(0, idx-101):idx]]
    prev_ema12 = sum(prev_prices[-12:]) / 12
    prev_ema26 = sum(prev_prices[-26:]) / 26
    prev_macd = prev_ema12 - prev_ema26

    signal_line = 0  # Simplified

    # Combined logic
    signal = {}

    # Bullish confirmation
    if rsi < 40 and prev_macd < signal_line and macd > signal_line:
        confidence = (rsi_confidence + 0.8) / 2  # Combined confidence
        size = 0.01 * confidence  # Scale position by confidence

        signal = {
            "action": "buy",
            "size": size,
            "stop_loss": bar.close - 0.0040,
            "take_profit": bar.close + 0.0080,
            "reason": f"RSI {rsi:.1f} + MACD bullish"
        }

    # Bearish confirmation
    elif rsi > 60 and prev_macd > signal_line and macd < signal_line:
        confidence = (rsi_confidence + 0.8) / 2
        size = 0.01 * confidence

        signal = {
            "action": "sell",
            "size": size,
            "stop_loss": bar.close + 0.0040,
            "take_profit": bar.close - 0.0080,
            "reason": f"RSI {rsi:.1f} + MACD bearish"
        }

    return signal


def adaptive_risk_strategy(engine: BacktestEngine, bar: BacktestBar) -> dict[str, Any]:
    """
    Adaptive risk sizing based on account equity and volatility.

    Features:
    - Position size scales with confidence
    - Risk per trade = 1-2% of capital (based on volatility)
    - Wider stops in volatile markets

    Args:
        engine: Backtest engine
        bar: Current bar

    Returns:
        Trading signal dict or None
    """
    idx = engine.current_bar_idx
    if idx < 100:
        return {}

    if engine.positions:
        return {}

    # Calculate recent volatility (ATR proxy)
    recent_bars = engine.data[max(0, idx-20):idx+1]
    ranges = [b.high - b.low for b in recent_bars]
    avg_range = sum(ranges) / len(ranges) if ranges else 0.0001

    # Normalize volatility (0-1 scale)
    volatility = avg_range / bar.close

    # Get RSI signal
    prices = [b.close for b in engine.data[max(0, idx-100):idx+1]]
    rsi_result = engine.call_tool("calc_rsi", prices=prices, period=14)

    if rsi_result.get("error"):
        return {}

    rsi = rsi_result.get("value")
    confidence = rsi_result.get("confidence", 0)

    # Adaptive risk sizing
    base_risk_pct = 0.01  # 1% base risk

    if volatility > 0.005:  # High volatility
        risk_pct = base_risk_pct * 0.5  # Reduce risk
        stop_multiplier = 2.0  # Wider stops
    elif volatility < 0.002:  # Low volatility
        risk_pct = base_risk_pct * 1.5  # Increase risk
        stop_multiplier = 1.0  # Tighter stops
    else:
        risk_pct = base_risk_pct
        stop_multiplier = 1.5

    # Calculate position size
    risk_amount = engine.capital * risk_pct
    stop_distance = avg_range * stop_multiplier
    position_size = risk_amount / (stop_distance * 100000)  # Assuming standard lot
    position_size = max(0.01, min(position_size, 0.1))  # Clamp to reasonable range

    # Generate signal
    signal = {}

    if rsi < 30 and confidence > 0.7:
        signal = {
            "action": "buy",
            "size": position_size,
            "stop_loss": bar.close - stop_distance,
            "take_profit": bar.close + (stop_distance * 2),  # 2:1 RR
            "reason": f"Adaptive RSI {rsi:.1f}, Vol: {volatility:.4f}"
        }

    elif rsi > 70 and confidence > 0.7:
        signal = {
            "action": "sell",
            "size": position_size,
            "stop_loss": bar.close + stop_distance,
            "take_profit": bar.close - (stop_distance * 2),
            "reason": f"Adaptive RSI {rsi:.1f}, Vol: {volatility:.4f}"
        }

    return signal


# Strategy registry for easy selection
STRATEGIES = {
    "rsi": rsi_strategy,
    "macd": macd_strategy,
    "combined": combined_rsi_macd_strategy,
    "adaptive": adaptive_risk_strategy
}


def get_strategy(name: str):
    """Get strategy function by name."""
    if name not in STRATEGIES:
        available = ", ".join(STRATEGIES.keys())
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}")
    return STRATEGIES[name]
