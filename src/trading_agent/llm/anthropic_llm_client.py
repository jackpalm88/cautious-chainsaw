"""
Real Anthropic LLM Client for Trading Agent v1.4
Replaces MockLLMClient with actual Claude API integration
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

from anthropic import Anthropic

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LLMResponse:
    """Standardized LLM response format"""
    content: str
    raw_response: dict[str, Any]
    latency_ms: float
    tokens_used: int
    model_used: str
    confidence: float = 0.0  # Will be calculated based on response quality

@dataclass
class ToolCall:
    """Represents a tool call from LLM"""
    tool_name: str
    parameters: dict[str, Any]
    id: str

class AnthropicLLMClient:
    """Production LLM client using Anthropic's Claude API"""

    def __init__(self,
                 api_key: str | None = None,
                 model: str = "claude-sonnet-4-20250514",
                 max_tokens: int = 4000,
                 temperature: float = 0.0):

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable required")

        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        logger.info(f"Initialized AnthropicLLMClient with model: {model}")

    def complete(self,
                 prompt: str,
                 tools: list[dict[str, Any]] | None = None,
                 system_prompt: str | None = None) -> LLMResponse:
        """
        Send completion request to Claude API

        Args:
            prompt: User message content
            tools: List of available tools (Claude function calling format)
            system_prompt: System instructions

        Returns:
            LLMResponse with parsed content and metadata
        """
        start_time = time.time()

        try:
            # Prepare messages
            messages = [{"role": "user", "content": prompt}]

            # Prepare request parameters
            request_params = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": messages
            }

            # Add system prompt if provided
            if system_prompt:
                request_params["system"] = system_prompt

            # Add tools if provided
            if tools:
                request_params["tools"] = tools
                logger.info(f"Using {len(tools)} tools in request")

            # Make API call
            logger.info(f"Sending request to Claude API (model: {self.model})")
            response = self.client.messages.create(**request_params)

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Extract content
            content = ""
            tool_calls = []

            for content_block in response.content:
                if content_block.type == "text":
                    content += content_block.text
                elif content_block.type == "tool_use":
                    tool_calls.append(ToolCall(
                        tool_name=content_block.name,
                        parameters=content_block.input,
                        id=content_block.id
                    ))

            # Calculate confidence based on response characteristics
            confidence = self._calculate_confidence(response, content, tool_calls)

            logger.info(f"Claude API response received in {latency_ms:.1f}ms")
            logger.info(f"Content length: {len(content)} chars, Tool calls: {len(tool_calls)}")

            return LLMResponse(
                content=content,
                raw_response=response.model_dump(),
                latency_ms=latency_ms,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                model_used=response.model,
                confidence=confidence
            )

        except Exception as e:
            logger.error(f"Claude API error: {str(e)}")
            raise RuntimeError(f"LLM completion failed: {str(e)}") from e

    def reason_with_tools(self,
                         context: dict[str, Any],
                         available_tools: list[dict[str, Any]],
                         decision_type: str = "trading") -> dict[str, Any]:
        """
        Enhanced reasoning with INoT multi-agent approach
        Matches the existing MockLLMClient interface

        Args:
            context: Trading context (prices, indicators, etc.)
            available_tools: List of tool definitions
            decision_type: Type of decision to make

        Returns:
            Structured decision with confidence and reasoning
        """

        # Build system prompt for trading decisions
        system_prompt = self._build_trading_system_prompt()

        # Build user prompt with context
        user_prompt = self._build_context_prompt(context, available_tools, decision_type)

        # Get LLM response
        response = self.complete(
            prompt=user_prompt,
            tools=available_tools,
            system_prompt=system_prompt
        )

        # Parse structured response
        try:
            # Try to extract JSON from response
            decision = self._parse_decision_response(response.content)

            # Add metadata
            decision["llm_metadata"] = {
                "model": response.model_used,
                "latency_ms": response.latency_ms,
                "tokens_used": response.tokens_used,
                "llm_confidence": response.confidence
            }

            return decision

        except Exception as e:
            logger.error(f"Failed to parse LLM decision: {str(e)}")

            # Fallback decision
            return {
                "action": "HOLD",
                "confidence": 0.1,
                "reasoning": f"Failed to parse LLM response: {str(e)}",
                "lots": 0.0,
                "stop_loss": None,
                "take_profit": None,
                "llm_metadata": {
                    "model": response.model_used,
                    "error": str(e),
                    "raw_content": response.content[:200] + "..." if len(response.content) > 200 else response.content
                }
            }

    def _build_trading_system_prompt(self) -> str:
        """Build system prompt for trading decisions"""
        return """You are a professional trading agent analyzing market data to make trading decisions.

Your task is to analyze the provided market context and return a structured JSON decision.

Key principles:
1. Risk management is paramount - never risk more than the account can afford
2. Only trade when you have high confidence (>0.7)
3. Always set appropriate stop losses and take profits
4. Consider market volatility and spread costs
5. Use available tools to gather additional information if needed

Response format (JSON only):
{
    "action": "BUY" | "SELL" | "HOLD",
    "confidence": 0.0-1.0,
    "reasoning": "Detailed explanation of decision",
    "lots": 0.0,
    "stop_loss": number | null,
    "take_profit": number | null,
    "risk_assessment": {
        "risk_level": "LOW" | "MEDIUM" | "HIGH",
        "max_loss_pct": number,
        "reward_risk_ratio": number
    }
}

Always respond with valid JSON only. No additional text outside the JSON structure."""

    def _build_context_prompt(self,
                             context: dict[str, Any],
                             tools: list[dict[str, Any]],
                             decision_type: str) -> str:
        """Build user prompt with trading context"""

        # Extract key context elements
        symbol = context.get("symbol", "Unknown")
        prices = context.get("prices", [])
        indicators = context.get("indicators", {})
        account_info = context.get("account_info", {})

        prompt = f"""Analyze this trading scenario and make a decision:

SYMBOL: {symbol}

MARKET DATA:
- Current Price: {prices[-1] if prices else 'N/A'}
- Recent Prices (last 10): {prices[-10:] if len(prices) >= 10 else prices}
- Price Trend: {'Rising' if len(prices) >= 2 and prices[-1] > prices[-2] else 'Falling' if len(prices) >= 2 else 'Unknown'}

TECHNICAL INDICATORS:
"""

        for indicator, value in indicators.items():
            prompt += f"- {indicator}: {value}\n"

        prompt += f"""
ACCOUNT INFO:
- Balance: {account_info.get('balance', 'N/A')}
- Equity: {account_info.get('equity', 'N/A')}
- Free Margin: {account_info.get('free_margin', 'N/A')}

AVAILABLE TOOLS:
"""

        for tool in tools:
            prompt += f"- {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}\n"

        prompt += f"""
DECISION TYPE: {decision_type}

Based on this information, analyze the market situation and provide your trading decision in the specified JSON format.

Consider:
1. Technical analysis from the indicators
2. Risk management (max 2% risk per trade)
3. Market conditions and volatility
4. Account size and available margin

Respond with JSON only."""

        return prompt

    def _parse_decision_response(self, content: str) -> dict[str, Any]:
        """Parse LLM response into structured decision"""

        # Clean content - remove any markdown formatting
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            decision = json.loads(content)

            # Validate required fields
            required_fields = ["action", "confidence", "reasoning", "lots"]
            for field in required_fields:
                if field not in decision:
                    raise ValueError(f"Missing required field: {field}")

            # Validate action
            valid_actions = ["BUY", "SELL", "HOLD"]
            if decision["action"] not in valid_actions:
                raise ValueError(f"Invalid action: {decision['action']}")

            # Validate confidence
            if not 0.0 <= decision["confidence"] <= 1.0:
                raise ValueError(f"Invalid confidence: {decision['confidence']}")

            return decision

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {str(e)}") from e

    def _calculate_confidence(self,
                             response: Any,
                             content: str,
                             tool_calls: list[ToolCall]) -> float:
        """Calculate confidence based on response characteristics"""

        confidence = 0.5  # Base confidence

        # Boost confidence for longer, more detailed responses
        if len(content) > 200:
            confidence += 0.1

        # Boost confidence if tool calls were made (more thorough analysis)
        if tool_calls:
            confidence += 0.1

        # Boost confidence for reasonable token usage (not too short or too long)
        total_tokens = response.usage.input_tokens + response.usage.output_tokens
        if 100 <= total_tokens <= 2000:
            confidence += 0.1

        # Check for structured response indicators
        if "confidence" in content.lower() and "reasoning" in content.lower():
            confidence += 0.1

        # Check for JSON structure
        try:
            json.loads(content.strip().replace("```json", "").replace("```", ""))
            confidence += 0.1
        except Exception:
            confidence -= 0.2  # Penalty for non-JSON responses

        return min(1.0, max(0.0, confidence))

# Configuration class for easy setup
@dataclass
class LLMConfig:
    """Configuration for LLM client"""
    api_key: str | None = None
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4000
    temperature: float = 0.0
    timeout_seconds: int = 30

def create_llm_client(config: LLMConfig | None = None) -> AnthropicLLMClient:
    """Factory function to create LLM client"""

    if config is None:
        config = LLMConfig()

    return AnthropicLLMClient(
        api_key=config.api_key,
        model=config.model,
        max_tokens=config.max_tokens,
        temperature=config.temperature
    )

# Example usage
if __name__ == "__main__":
    # Test the client
    import os

    # Set up API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Please set ANTHROPIC_API_KEY environment variable")
        exit(1)

    # Create client
    client = create_llm_client()

    # Test basic completion
    response = client.complete("Hello Claude, can you help with trading analysis?")
    print(f"Response: {response.content}")
    print(f"Latency: {response.latency_ms:.1f}ms")
    print(f"Tokens: {response.tokens_used}")

    # Test trading decision
    context = {
        "symbol": "EURUSD",
        "prices": [1.0950, 1.0955, 1.0960, 1.0965, 1.0970],
        "indicators": {
            "RSI": 65.5,
            "MACD": 0.0012,
            "signal": "BULLISH"
        },
        "account_info": {
            "balance": 10000.0,
            "equity": 10000.0,
            "free_margin": 9000.0
        }
    }

    tools = [
        {
            "name": "calc_rsi",
            "description": "Calculate RSI indicator",
            "parameters": {
                "type": "object",
                "properties": {
                    "prices": {"type": "array", "items": {"type": "number"}},
                    "period": {"type": "integer", "default": 14}
                }
            }
        }
    ]

    decision = client.reason_with_tools(context, tools, "trading")
    print(f"Decision: {json.dumps(decision, indent=2)}")
