"""
Tests for INoT LLM Adapter

Validates that INoTLLMAdapter correctly bridges AnthropicLLMClient
and INoT orchestrator interfaces.
"""

from unittest.mock import Mock, patch

import pytest

from src.trading_agent.llm.anthropic_llm_client import (
    AnthropicLLMClient,
    LLMResponse,
)
from src.trading_agent.llm.inot_adapter import (
    INoTLLMAdapter,
    SimpleResponse,
    create_inot_adapter,
)


class TestSimpleResponse:
    """Test SimpleResponse dataclass"""

    def test_simple_response_creation(self):
        """Test creating SimpleResponse"""
        response = SimpleResponse(
            content='{"test": "data"}',
            latency_ms=100.5,
            tokens_used=150,
            model_used="claude-sonnet-4"
        )

        assert response.content == '{"test": "data"}'
        assert response.latency_ms == 100.5
        assert response.tokens_used == 150
        assert response.model_used == "claude-sonnet-4"

    def test_simple_response_minimal(self):
        """Test SimpleResponse with only required field"""
        response = SimpleResponse(content="test")

        assert response.content == "test"
        assert response.latency_ms == 0.0
        assert response.tokens_used == 0
        assert response.model_used == ""


class TestINoTLLMAdapter:
    """Test INoTLLMAdapter functionality"""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create mock AnthropicLLMClient"""
        client = Mock(spec=AnthropicLLMClient)
        client.model = "claude-sonnet-4-20250514"
        client.temperature = 0.0
        client.max_tokens = 4000
        return client

    @pytest.fixture
    def adapter(self, mock_anthropic_client):
        """Create INoTLLMAdapter with mock client"""
        return INoTLLMAdapter(mock_anthropic_client)

    def test_adapter_initialization(self, mock_anthropic_client):
        """Test adapter initialization"""
        adapter = INoTLLMAdapter(mock_anthropic_client)

        assert adapter.client == mock_anthropic_client
        assert adapter._original_model == "claude-sonnet-4-20250514"
        assert adapter._original_temperature == 0.0
        assert adapter._original_max_tokens == 4000

    def test_complete_basic(self, adapter, mock_anthropic_client):
        """Test basic complete() call"""
        # Mock LLMResponse
        mock_response = LLMResponse(
            content='{"action": "BUY"}',
            raw_response={},
            latency_ms=150.5,
            tokens_used=200,
            model_used="claude-sonnet-4",
            confidence=0.85
        )
        mock_anthropic_client.complete.return_value = mock_response

        # Call adapter
        result = adapter.complete(prompt="Test prompt")

        # Verify
        assert isinstance(result, SimpleResponse)
        assert result.content == '{"action": "BUY"}'
        assert result.latency_ms == 150.5
        assert result.tokens_used == 200
        assert result.model_used == "claude-sonnet-4"

        # Verify client was called correctly
        mock_anthropic_client.complete.assert_called_once_with(
            prompt="Test prompt",
            tools=None,
            system_prompt=None
        )

    def test_complete_with_parameters(self, adapter, mock_anthropic_client):
        """Test complete() with custom parameters"""
        # Track parameters during complete() call
        params_during_call = {}

        def capture_params(*args, **kwargs):
            params_during_call['model'] = mock_anthropic_client.model
            params_during_call['temperature'] = mock_anthropic_client.temperature
            params_during_call['max_tokens'] = mock_anthropic_client.max_tokens
            return LLMResponse(
                content="test",
                raw_response={},
                latency_ms=100.0,
                tokens_used=50,
                model_used="claude-sonnet-4"
            )

        mock_anthropic_client.complete.side_effect = capture_params

        # Call with custom parameters
        result = adapter.complete(
            prompt="Test",
            model="claude-opus-4",
            temperature=0.5,
            max_tokens=2000
        )

        # Verify parameters were set during call
        assert params_during_call['model'] == "claude-opus-4"
        assert params_during_call['temperature'] == 0.5
        assert params_during_call['max_tokens'] == 2000

        # Verify result
        assert result.content == "test"

    def test_complete_restores_settings(self, adapter, mock_anthropic_client):
        """Test that complete() restores original settings"""
        mock_response = LLMResponse(
            content="test",
            raw_response={},
            latency_ms=100.0,
            tokens_used=50,
            model_used="claude-sonnet-4"
        )
        mock_anthropic_client.complete.return_value = mock_response

        # Call with custom parameters
        adapter.complete(
            prompt="Test",
            model="claude-opus-4",
            temperature=0.7,
            max_tokens=1000
        )

        # Verify settings were restored
        assert mock_anthropic_client.model == "claude-sonnet-4-20250514"
        assert mock_anthropic_client.temperature == 0.0
        assert mock_anthropic_client.max_tokens == 4000

    def test_complete_restores_on_error(self, adapter, mock_anthropic_client):
        """Test that settings are restored even on error"""
        # Mock error
        mock_anthropic_client.complete.side_effect = RuntimeError("API error")

        # Call should raise error
        with pytest.raises(RuntimeError, match="API error"):
            adapter.complete(
                prompt="Test",
                model="claude-opus-4",
                temperature=0.5
            )

        # Verify settings were still restored
        assert mock_anthropic_client.model == "claude-sonnet-4-20250514"
        assert mock_anthropic_client.temperature == 0.0

    def test_get_cost_estimate(self, adapter):
        """Test cost estimation"""
        # Test with 1000 tokens
        cost = adapter.get_cost_estimate(1000)
        expected = (1000 / 1_000_000) * 9  # $9 per 1M tokens average
        assert cost == pytest.approx(expected)

        # Test with 100,000 tokens
        cost = adapter.get_cost_estimate(100_000)
        expected = (100_000 / 1_000_000) * 9
        assert cost == pytest.approx(expected)

    def test_reset_to_defaults(self, adapter, mock_anthropic_client):
        """Test resetting to default settings"""
        # Modify settings
        mock_anthropic_client.model = "modified"
        mock_anthropic_client.temperature = 0.9
        mock_anthropic_client.max_tokens = 1000

        # Reset
        adapter.reset_to_defaults()

        # Verify restored
        assert mock_anthropic_client.model == "claude-sonnet-4-20250514"
        assert mock_anthropic_client.temperature == 0.0
        assert mock_anthropic_client.max_tokens == 4000


class TestCreateINoTAdapter:
    """Test convenience function"""

    @patch('src.trading_agent.llm.inot_adapter.AnthropicLLMClient')
    def test_create_inot_adapter_defaults(self, mock_client_class):
        """Test creating adapter with defaults"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Create adapter
        adapter = create_inot_adapter()

        # Verify client was created with defaults
        mock_client_class.assert_called_once_with(
            api_key=None,
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.0
        )

        # Verify adapter wraps client
        assert isinstance(adapter, INoTLLMAdapter)
        assert adapter.client == mock_client

    @patch('src.trading_agent.llm.inot_adapter.AnthropicLLMClient')
    def test_create_inot_adapter_custom(self, mock_client_class):
        """Test creating adapter with custom parameters"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Create with custom params
        adapter = create_inot_adapter(
            api_key="test-key",
            model="claude-opus-4",
            max_tokens=2000,
            temperature=0.5
        )

        # Verify
        mock_client_class.assert_called_once_with(
            api_key="test-key",
            model="claude-opus-4",
            max_tokens=2000,
            temperature=0.5
        )
        assert isinstance(adapter, INoTLLMAdapter)


class TestIntegrationWithRealClient:
    """Integration tests with real AnthropicLLMClient (mocked API)"""

    @pytest.fixture
    def real_client_with_mock_api(self):
        """Create real client with mocked Anthropic API"""
        with patch('src.trading_agent.llm.anthropic_llm_client.Anthropic') as mock_anthropic:
            # Mock API response
            mock_message = Mock()
            mock_message.content = [Mock(type="text", text='{"test": "response"}')]
            mock_message.usage = Mock(input_tokens=100, output_tokens=50)
            mock_message.model = "claude-sonnet-4-20250514"
            mock_message.model_dump.return_value = {}

            mock_anthropic.return_value.messages.create.return_value = mock_message

            # Create real client
            client = AnthropicLLMClient(
                api_key="test-key",
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0.0
            )

            yield client, mock_anthropic

    def test_adapter_with_real_client(self, real_client_with_mock_api):
        """Test adapter with real AnthropicLLMClient"""
        client, mock_anthropic = real_client_with_mock_api

        # Create adapter
        adapter = INoTLLMAdapter(client)

        # Call complete
        result = adapter.complete(prompt="Test prompt")

        # Verify result
        assert isinstance(result, SimpleResponse)
        assert result.content == '{"test": "response"}'
        assert result.tokens_used == 150  # 100 + 50

        # Verify API was called
        mock_anthropic.return_value.messages.create.assert_called_once()

    def test_adapter_parameter_override(self, real_client_with_mock_api):
        """Test parameter override with real client"""
        client, mock_anthropic = real_client_with_mock_api
        adapter = INoTLLMAdapter(client)

        # Call with overrides
        result = adapter.complete(
            prompt="Test",
            model="claude-opus-4",
            temperature=0.7,
            max_tokens=2000
        )

        # Verify API call used overridden parameters
        call_args = mock_anthropic.return_value.messages.create.call_args
        assert call_args.kwargs['model'] == "claude-opus-4"
        assert call_args.kwargs['temperature'] == 0.7
        assert call_args.kwargs['max_tokens'] == 2000

        # Verify settings restored
        assert client.model == "claude-sonnet-4-20250514"
        assert client.temperature == 0.0
        assert client.max_tokens == 4000


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
