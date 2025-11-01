"""
INoT LLM Adapter - Bridge between INoT and AnthropicLLMClient

This adapter makes AnthropicLLMClient compatible with INoT orchestrator's
expected LLM interface without modifying either component.

Architecture:
    INoT Orchestrator → INoTLLMAdapter → AnthropicLLMClient → Claude API

Key Features:
- Interface compatibility (matches INoT expectations)
- Parameter mapping (INoT params → Claude params)
- Response adaptation (LLMResponse → SimpleResponse)
- Error handling and fallbacks
"""

from dataclasses import dataclass
from typing import Any

from .anthropic_llm_client import AnthropicLLMClient, LLMResponse


@dataclass
class SimpleResponse:
    """
    Simple response object matching INoT's expected interface.
    
    INoT orchestrator expects LLM responses to have:
    - .content attribute (raw text response, typically JSON)
    - .usage attribute (dict with token counts)
    """
    content: str
    
    # Optional metadata (not used by INoT but useful for debugging)
    latency_ms: float = 0.0
    tokens_used: int = 0
    model_used: str = ""
    usage: dict[str, int] | None = None  # For INoT cost tracking


class INoTLLMAdapter:
    """
    Adapter to make AnthropicLLMClient compatible with INoT orchestrator.
    
    This adapter bridges the interface gap between:
    - INoT's expected LLM interface (simple .complete() method)
    - AnthropicLLMClient's interface (rich LLMResponse object)
    
    Usage:
        # Create Claude client
        claude = AnthropicLLMClient(api_key="...")
        
        # Wrap with adapter
        adapter = INoTLLMAdapter(claude)
        
        # Pass to INoT orchestrator
        orchestrator = INoTOrchestrator(
            llm_client=adapter,
            config={...},
            validator=validator
        )
        
        # INoT will call adapter.complete() which internally uses Claude
    """
    
    def __init__(self, anthropic_client: AnthropicLLMClient):
        """
        Initialize adapter with AnthropicLLMClient instance.
        
        Args:
            anthropic_client: Configured AnthropicLLMClient instance
        """
        self.client = anthropic_client
        
        # Store original client settings for restoration
        self._original_model = anthropic_client.model
        self._original_temperature = anthropic_client.temperature
        self._original_max_tokens = anthropic_client.max_tokens
        
    def complete(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None
    ) -> SimpleResponse:
        """
        Execute LLM completion with INoT-compatible interface.
        
        This method matches INoT orchestrator's expectations:
        - Takes prompt and optional parameters
        - Returns object with .content attribute
        - Handles errors gracefully
        
        Args:
            prompt: User prompt (typically INoT multi-agent prompt)
            model: Model version (optional, uses client default if None)
            temperature: Sampling temperature (optional)
            max_tokens: Max tokens to generate (optional)
            
        Returns:
            SimpleResponse with .content containing LLM output
            
        Raises:
            RuntimeError: If LLM call fails (propagated from AnthropicLLMClient)
        """
        # Temporarily override client settings if parameters provided
        if model is not None:
            self.client.model = model
        if temperature is not None:
            self.client.temperature = temperature
        if max_tokens is not None:
            self.client.max_tokens = max_tokens
            
        try:
            # Call AnthropicLLMClient
            response: LLMResponse = self.client.complete(
                prompt=prompt,
                tools=None,  # INoT doesn't use tool calling
                system_prompt=None  # INoT includes system instructions in prompt
            )
            
            # Adapt response to SimpleResponse format
            # Calculate input/output tokens from raw response
            usage_dict = {}
            if hasattr(response, 'raw_response') and response.raw_response:
                raw = response.raw_response
                if 'usage' in raw:
                    usage_dict = {
                        'input_tokens': raw['usage'].get('input_tokens', 0),
                        'output_tokens': raw['usage'].get('output_tokens', 0)
                    }
            
            # Fallback: estimate from total tokens (50/50 split)
            if not usage_dict:
                half_tokens = response.tokens_used // 2
                usage_dict = {
                    'input_tokens': half_tokens,
                    'output_tokens': half_tokens
                }
            
            return SimpleResponse(
                content=response.content,
                latency_ms=response.latency_ms,
                tokens_used=response.tokens_used,
                model_used=response.model_used,
                usage=usage_dict
            )
            
        finally:
            # Restore original client settings
            self.client.model = self._original_model
            self.client.temperature = self._original_temperature
            self.client.max_tokens = self._original_max_tokens
    
    def get_cost_estimate(self, tokens_used: int) -> float:
        """
        Estimate cost for given token usage.
        
        Based on Claude Sonnet 4 pricing:
        - Input: $3 per 1M tokens
        - Output: $15 per 1M tokens
        - Assume 50/50 split for estimation
        
        Args:
            tokens_used: Total tokens (input + output)
            
        Returns:
            Estimated cost in USD
        """
        # Rough estimate: average of input and output pricing
        avg_price_per_1m = (3 + 15) / 2  # $9 per 1M tokens
        return (tokens_used / 1_000_000) * avg_price_per_1m
    
    def reset_to_defaults(self):
        """
        Reset client to original settings.
        
        Useful for cleanup or testing.
        """
        self.client.model = self._original_model
        self.client.temperature = self._original_temperature
        self.client.max_tokens = self._original_max_tokens


# Convenience function for quick setup
def create_inot_adapter(
    api_key: str | None = None,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4000,
    temperature: float = 0.0
) -> INoTLLMAdapter:
    """
    Create INoT adapter with default AnthropicLLMClient configuration.
    
    This is a convenience function for quick setup. For more control,
    create AnthropicLLMClient manually and wrap with INoTLLMAdapter.
    
    Args:
        api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if None)
        model: Claude model version
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0 = deterministic)
        
    Returns:
        Configured INoTLLMAdapter ready to use with INoT orchestrator
        
    Example:
        adapter = create_inot_adapter()
        orchestrator = INoTOrchestrator(
            llm_client=adapter,
            config={...},
            validator=validator
        )
    """
    client = AnthropicLLMClient(
        api_key=api_key,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature
    )
    return INoTLLMAdapter(client)
