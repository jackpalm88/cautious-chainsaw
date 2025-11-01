"""
Integration Guide: MockLLMClient → AnthropicLLMClient
Trading Agent v1.4 → v1.5 Upgrade
"""

import json
import os
from dataclasses import dataclass
from typing import Any

from anthropic_llm_client import AnthropicLLMClient

# Import your existing classes (update paths as needed)
from trading_agent.decision.engine import TradingDecisionEngine


@dataclass
class LLMIntegrationConfig:
    """Configuration for LLM integration upgrade"""

    # Anthropic API settings
    anthropic_api_key: str
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4000
    temperature: float = 0.0

    # Integration settings
    enable_real_llm: bool = True
    fallback_to_mock: bool = True  # Fallback if API fails

    # Performance settings
    timeout_seconds: int = 30
    max_retries: int = 3

    # Logging
    log_requests: bool = True
    log_responses: bool = True

class LLMIntegrationManager:
    """Manages the transition from Mock to Real LLM"""

    def __init__(self, config: LLMIntegrationConfig):
        self.config = config

        # Initialize real LLM client
        if config.enable_real_llm:
            self.real_client = AnthropicLLMClient(
                api_key=config.anthropic_api_key,
                model=config.model,
                max_tokens=config.max_tokens,
                temperature=config.temperature
            )
        else:
            self.real_client = None

        # Keep mock client as fallback
        self.mock_client = None  # Will be initialized from existing code

    def get_llm_client(self):
        """Get the appropriate LLM client (real or mock)"""

        if self.config.enable_real_llm and self.real_client:
            return self.real_client
        elif self.config.fallback_to_mock and self.mock_client:
            return self.mock_client
        else:
            raise RuntimeError("No LLM client available")

    def upgrade_decision_engine(self, decision_engine: TradingDecisionEngine):
        """Upgrade existing decision engine to use real LLM"""

        # Replace the LLM client in the decision engine
        if hasattr(decision_engine, 'inot_orchestrator'):
            # Update INoT orchestrator with real LLM
            real_client = self.get_llm_client()

            # This assumes your INoT orchestrator has a client attribute
            # Adjust based on your actual implementation
            decision_engine.inot_orchestrator.llm_client = real_client

            print("✅ Decision engine upgraded to use real LLM")
        else:
            print("⚠️ Decision engine structure not recognized")

    def test_integration(self) -> dict[str, Any]:
        """Test the LLM integration with a simple request"""

        try:
            client = self.get_llm_client()

            # Test basic completion
            test_prompt = "Analyze EURUSD with RSI=65, MACD=0.0012. Recommend action."

            if isinstance(client, AnthropicLLMClient):
                response = client.complete(test_prompt)

                return {
                    "status": "success",
                    "client_type": "anthropic",
                    "latency_ms": response.latency_ms,
                    "tokens_used": response.tokens_used,
                    "response_length": len(response.content),
                    "confidence": response.confidence
                }
            else:
                # Mock client test
                return {
                    "status": "success",
                    "client_type": "mock",
                    "note": "Using fallback mock client"
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "client_type": "unknown"
            }

# Step-by-step integration instructions
INTEGRATION_STEPS = """
🚀 LLM Integration Steps (v1.4 → v1.5)

1. SETUP ENVIRONMENT
   ```bash
   # Install Anthropic SDK
   pip install anthropic

   # Set API key
   export ANTHROPIC_API_KEY="your_api_key_here"
   ```

2. BACKUP EXISTING CODE
   ```bash
   # Create backup
   cp -r src/trading_agent/inot_engine src/trading_agent/inot_engine.backup
   cp -r src/trading_agent/decision src/trading_agent/decision.backup
   ```

3. REPLACE MOCK CLIENT
   # In your INoT orchestrator or decision engine:

   # OLD (v1.4):
   from trading_agent.llm.mock_client import MockLLMClient
   client = MockLLMClient()

   # NEW (v1.5):
   from anthropic_llm_client import AnthropicLLMClient
   client = AnthropicLLMClient(api_key=os.getenv("ANTHROPIC_API_KEY"))

4. UPDATE DECISION ENGINE
   # Find where MockLLMClient is instantiated and replace:

   # In decision/engine.py or similar:
   class TradingDecisionEngine:
       def __init__(self, config):
           # OLD:
           # self.llm_client = MockLLMClient()

           # NEW:
           from anthropic_llm_client import create_llm_client
           self.llm_client = create_llm_client()

5. UPDATE INOT ORCHESTRATOR
   # In inot_engine/orchestrator.py:
   class INoTOrchestrator:
       def reason(self, context, tools):
           # The method signature should remain the same
           # Just replace the internal LLM calls

           # Use self.llm_client.reason_with_tools() instead of mock

6. TEST INTEGRATION
   ```python
   # Test script:
   config = LLMIntegrationConfig(
       anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
       enable_real_llm=True
   )

   manager = LLMIntegrationManager(config)
   result = manager.test_integration()
   print(f"Integration test: {result}")
   ```

7. GRADUAL ROLLOUT
   # Enable real LLM progressively:

   # Phase 1: Test with mock data
   # Phase 2: Test with live data, no execution
   # Phase 3: Enable live execution with small position sizes
   # Phase 4: Full production
"""

# Configuration templates
CONFIG_TEMPLATES = {
    "development": {
        "anthropic_api_key": "your_dev_key",
        "enable_real_llm": True,
        "fallback_to_mock": True,
        "max_tokens": 2000,
        "temperature": 0.1,
        "log_requests": True
    },

    "production": {
        "anthropic_api_key": "your_prod_key",
        "enable_real_llm": True,
        "fallback_to_mock": False,
        "max_tokens": 4000,
        "temperature": 0.0,
        "log_requests": False
    },

    "testing": {
        "enable_real_llm": False,
        "fallback_to_mock": True,
        "log_requests": True
    }
}

def create_config_file(environment: str = "development"):
    """Create configuration file for the integration"""

    if environment not in CONFIG_TEMPLATES:
        raise ValueError(f"Unknown environment: {environment}")

    config = CONFIG_TEMPLATES[environment].copy()

    # Save to file
    config_path = f"llm_config_{environment}.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"✅ Created {config_path}")
    return config_path

def validate_integration_requirements():
    """Validate that all requirements are met for integration"""

    issues = []

    # Check API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        issues.append("❌ ANTHROPIC_API_KEY environment variable not set")
    else:
        print("✅ API key found")

    # Check Anthropic package
    try:
        import anthropic
        print("✅ Anthropic package installed")
    except ImportError:
        issues.append("❌ Anthropic package not installed (pip install anthropic)")

    # Check network connectivity
    try:
        import requests
        requests.get("https://api.anthropic.com", timeout=5)
        print("✅ Network connectivity to Anthropic API")
    except:
        issues.append("⚠️ Cannot reach Anthropic API (check network)")

    if issues:
        print("\n🚨 Integration Issues:")
        for issue in issues:
            print(f"  {issue}")
        return False
    else:
        print("\n🎯 All requirements met - ready for integration!")
        return True

# Example usage
if __name__ == "__main__":
    print("🚀 LLM Integration Manager")
    print("=" * 50)

    print("\n1. Validating requirements...")
    requirements_ok = validate_integration_requirements()

    if requirements_ok:
        print("\n2. Creating configuration files...")
        create_config_file("development")
        create_config_file("production")

        print("\n3. Testing integration...")
        if os.getenv("ANTHROPIC_API_KEY"):
            config = LLMIntegrationConfig(
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
                enable_real_llm=True
            )

            manager = LLMIntegrationManager(config)
            test_result = manager.test_integration()

            print(f"Test result: {json.dumps(test_result, indent=2)}")
        else:
            print("Skipping test - no API key")

    print("\n" + INTEGRATION_STEPS)

    print("\n🎯 Next Steps:")
    print("1. Set ANTHROPIC_API_KEY environment variable")
    print("2. Copy anthropic_llm_client.py to your src/trading_agent/llm/ directory")
    print("3. Update your decision engine to use AnthropicLLMClient")
    print("4. Test with small position sizes first")
    print("5. Monitor performance and error rates")
