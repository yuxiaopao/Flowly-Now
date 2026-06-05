"""
Test cases for Ollama Gateway Provider.

Requires local Ollama environment for integration tests.
Run with: python -m pytest tests/test_ollama_gateway.py -v
"""

import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal


class TestOllamaProvider:
    """Test OllamaProvider class structure and methods."""

    def test_ollama_provider_exists(self):
        """OllamaProvider class exists and can be imported."""
        from gateway.providers.ollama_provider import OllamaProvider
        assert OllamaProvider is not None

    def test_ollama_provider_initialization(self):
        """OllamaProvider can be initialized with default/custom settings."""
        from gateway.providers.ollama_provider import OllamaProvider
        provider = OllamaProvider(
            api_key='',
            base_url='http://localhost:11434'
        )
        assert provider._base_url == 'http://localhost:11434'

    def test_ollama_provider_class_attributes(self):
        """OllamaProvider has correct class-level attributes."""
        from gateway.providers.ollama_provider import OllamaProvider
        assert OllamaProvider.provider_name == 'ollama'
        assert OllamaProvider.provider_display_name == 'Ollama (本地)'

    def test_chat_method_signature(self):
        """OllamaProvider.chat() method has correct signature."""
        import inspect
        from gateway.providers.ollama_provider import OllamaProvider
        sig = inspect.signature(OllamaProvider.chat)
        params = list(sig.parameters.keys())
        assert 'messages' in params
        assert 'model' in params
        assert 'temperature' in params
        assert 'max_tokens' in params

    def test_stream_chat_method_exists(self):
        """OllamaProvider.stream_chat() method exists."""
        from gateway.providers.ollama_provider import OllamaProvider
        assert hasattr(OllamaProvider, 'stream_chat')
        assert callable(OllamaProvider.stream_chat)

    def test_health_check_method_exists(self):
        """OllamaProvider.health_check() method exists."""
        from gateway.providers.ollama_provider import OllamaProvider
        assert hasattr(OllamaProvider, 'health_check')
        assert callable(OllamaProvider.health_check)

    def test_calculate_cost_method_exists(self):
        """OllamaProvider.calculate_cost() method exists and returns 0."""
        from gateway.providers.ollama_provider import OllamaProvider
        assert hasattr(OllamaProvider, 'calculate_cost')
        provider = OllamaProvider()
        cost = provider.calculate_cost("llama3", 100, 50)
        assert cost == Decimal("0")

    def test_connect_method_exists(self):
        """OllamaProvider.connect() method exists."""
        from gateway.providers.ollama_provider import OllamaProvider
        assert hasattr(OllamaProvider, 'connect')
        assert callable(OllamaProvider.connect)

    def test_list_models_method_exists(self):
        """OllamaProvider.list_models() method exists."""
        from gateway.providers.ollama_provider import OllamaProvider
        assert hasattr(OllamaProvider, 'list_models')
        assert callable(OllamaProvider.list_models)

    def test_embeddings_method_exists(self):
        """OllamaProvider.embeddings() method exists."""
        from gateway.providers.ollama_provider import OllamaProvider
        assert hasattr(OllamaProvider, 'embeddings')
        assert callable(OllamaProvider.embeddings)

    def test_supports_model_method_exists(self):
        """OllamaProvider.supports_model() method exists."""
        from gateway.providers.ollama_provider import OllamaProvider
        assert hasattr(OllamaProvider, 'supports_model')
        assert callable(OllamaProvider.supports_model)

    def test_invalidate_cache_method_exists(self):
        """OllamaProvider.invalidate_cache() method exists."""
        from gateway.providers.ollama_provider import OllamaProvider
        assert hasattr(OllamaProvider, 'invalidate_cache')
        assert callable(OllamaProvider.invalidate_cache)


class TestOllamaProviderMocked:
    """Test OllamaProvider with mocked HTTP responses."""

    @patch('gateway.providers.ollama_provider.requests.post')
    @patch('gateway.providers.ollama_provider.requests.get')
    def test_chat_returns_provider_response(self, mock_get, mock_post):
        """chat() returns ProviderResponse with correct format."""
        from gateway.providers.ollama_provider import OllamaProvider
        from gateway.providers.base import ProviderResponse

        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            'models': [{'name': 'qwen2.5-coder:7b', 'details': {'parameter_size': '7B'}}]
        }
        mock_get.return_value = mock_get_response

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'model': 'qwen2.5-coder:7b',
            'message': {'content': 'Test response'},
            'done_reason': 'stop',
            'prompt_eval_count': 10,
            'eval_count': 5
        }
        mock_post.return_value = mock_response

        provider = OllamaProvider()
        result = provider.chat(messages=[{'role': 'user', 'content': 'hello'}])

        assert isinstance(result, ProviderResponse)
        assert result.content == 'Test response'
        assert result.model == 'qwen2.5-coder:7b'
        assert result.provider == 'ollama'
        assert result.input_tokens == 10
        assert result.output_tokens == 5
        assert result.cost == Decimal("0")

    @patch('gateway.providers.ollama_provider.requests.post')
    @patch('gateway.providers.ollama_provider.requests.get')
    def test_chat_with_error_response(self, mock_get, mock_post):
        """chat() handles error responses gracefully."""
        from gateway.providers.ollama_provider import OllamaProvider
        from gateway.providers.base import ProviderResponse

        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            'models': [{'name': 'qwen2.5-coder:7b', 'details': {}}]
        }
        mock_get.return_value = mock_get_response

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'error': 'Invalid request'}
        mock_response.raise_for_status.side_effect = Exception('HTTP 400')
        mock_post.return_value = mock_response

        provider = OllamaProvider()
        result = provider.chat(messages=[{'role': 'user', 'content': 'hello'}])

        assert isinstance(result, ProviderResponse)
        assert result.error is not None

    @patch('gateway.providers.ollama_provider.requests.get')
    def test_list_models_returns_model_info_list(self, mock_get):
        """list_models() returns list of ModelInfo objects."""
        from gateway.providers.ollama_provider import OllamaProvider
        from gateway.providers.base import ModelInfo

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {
                    'name': 'qwen2.5-coder:7b',
                    'details': {
                        'parameter_size': '7B',
                        'context_length': 8192,
                        'capabilities': ['tools']
                    }
                },
                {
                    'name': 'smollm2:135m',
                    'details': {
                        'parameter_size': '135M',
                        'context_length': 4096
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        provider = OllamaProvider()
        models = provider.list_models()

        assert isinstance(models, list)
        assert len(models) == 2
        assert all(isinstance(m, ModelInfo) for m in models)
        assert models[0].model_id == 'qwen2.5-coder:7b'
        assert models[0].supports_function_calling is True
        assert models[1].model_id == 'smollm2:135m'

    @patch('gateway.providers.ollama_provider.requests.get')
    def test_health_check_returns_status_dict(self, mock_get):
        """health_check() returns proper status dict."""
        from gateway.providers.ollama_provider import OllamaProvider

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [{'name': 'test'}]
        }
        mock_get.return_value = mock_response

        provider = OllamaProvider()
        health = provider.health_check()

        assert isinstance(health, dict)
        assert 'status' in health
        assert health['status'] == 'ok'
        assert 'latency_ms' in health
        assert 'models_count' in health
        assert health['models_count'] == 1

    @patch('gateway.providers.ollama_provider.requests.get')
    def test_connect_returns_true_on_success(self, mock_get):
        """connect() returns True when Ollama is reachable."""
        from gateway.providers.ollama_provider import OllamaProvider

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        provider = OllamaProvider()
        assert provider.connect() is True

    @patch('gateway.providers.ollama_provider.requests.get')
    def test_connect_returns_false_on_failure(self, mock_get):
        """connect() returns False when Ollama is not reachable."""
        from gateway.providers.ollama_provider import OllamaProvider
        import requests

        mock_get.side_effect = requests.exceptions.ConnectionError()

        provider = OllamaProvider()
        assert provider.connect() is False


class TestProviderRegistry:
    """Test ProviderRegistry with Ollama integration."""

    def test_registry_has_ollama_registered(self):
        """ProviderRegistry shows ollama in list_providers when imported."""
        import requests
        from gateway.providers.registry import register_default_providers

        with patch('django.conf.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            mock_settings.ANTHROPIC_API_KEY = None
            mock_settings.OLLAMA_BASE_URL = 'http://localhost:11434'

            with patch.object(requests, 'get') as mock_get:
                mock_get_response = MagicMock()
                mock_get_response.status_code = 200
                mock_get.return_value = mock_get_response

                register_default_providers()

                from gateway.providers.registry import default_registry
                providers = default_registry.get_all()

                assert 'ollama' in providers

    def test_registry_list_providers_returns_dict(self):
        """list_providers() returns list of provider dicts."""
        from gateway.providers.registry import ProviderRegistry

        registry = ProviderRegistry()
        providers = registry.list_providers()

        assert isinstance(providers, list)

    def test_registry_health_check_returns_dict(self):
        """health_check() returns dict with provider statuses."""
        from gateway.providers.registry import ProviderRegistry

        registry = ProviderRegistry()
        health = registry.health_check()

        assert isinstance(health, dict)


class TestOllamaIntegration:
    """Integration tests requiring local Ollama runtime."""

    @pytest.mark.integration
    def test_ollama_server_is_reachable(self):
        """Test that Ollama server is actually running and responding."""
        import requests
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=5)
            assert resp.status_code == 200
            data = resp.json()
            assert "models" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("Ollama not running")
        except requests.exceptions.TimeoutError:
            pytest.skip("Ollama response timeout")

    @pytest.mark.integration
    def test_ollama_can_chat(self):
        """Test actual chat with Ollama using a simple prompt."""
        from gateway.providers.ollama_provider import OllamaProvider
        from gateway.providers.base import ProviderResponse

        provider = OllamaProvider()
        models = provider.list_models()

        if not models:
            pytest.skip("No Ollama models available")

        model_to_test = models[0].model_id

        result = provider.chat(
            messages=[{'role': 'user', 'content': 'Say "OK" in one word'}],
            model=model_to_test,
            max_tokens=50
        )

        assert isinstance(result, ProviderResponse)
        if result.error:
            if 'memory' in result.error.lower():
                pytest.skip(f"Model {model_to_test} requires too much memory")
            pytest.fail(f"Unexpected error: {result.error}")
        assert result.content.strip().upper() in ['OK', 'OK.']
        assert result.cost == Decimal("0")

    @pytest.mark.integration
    def test_ollama_health_check_real(self):
        """Test health_check with real Ollama connection."""
        from gateway.providers.ollama_provider import OllamaProvider

        provider = OllamaProvider()
        health = provider.health_check()

        assert health['status'] == 'ok'
        assert health['models_count'] >= 1

    @pytest.mark.integration
    def test_ollama_stream_chat_yields_chunks(self):
        """Test stream_chat yields content chunks."""
        from gateway.providers.ollama_provider import OllamaProvider

        provider = OllamaProvider()
        models = provider.list_models()

        if not models:
            pytest.skip("No Ollama models available")

        model_to_test = models[0].model_id

        chunks = []
        errors = []
        for chunk in provider.stream_chat(
            messages=[{'role': 'user', 'content': 'Count from 1 to 3'}],
            model=model_to_test,
            max_tokens=50
        ):
            if chunk.get('type') == 'error':
                errors.append(chunk.get('error', ''))
            chunks.append(chunk)
            if len(chunks) > 20:
                break

        if errors and any('memory' in e.lower() for e in errors):
            pytest.skip(f"Model {model_to_test} requires too much memory")

        assert len(chunks) >= 1
        content_chunks = [c for c in chunks if c.get('type') == 'content']
        assert len(content_chunks) >= 1


class TestModelInfoAlignment:
    """Test ModelInfo format alignment with provider."""

    def test_model_info_has_required_fields(self):
        """ModelInfo dataclass has all required fields."""
        from gateway.providers.base import ModelInfo

        info = ModelInfo(
            model_id='test-model',
            name='Test Model',
            provider='ollama',
            model_type='chat',
            max_tokens=4096,
            supports_streaming=True,
            supports_function_calling=False,
            supports_vision=False,
            input_price=Decimal("0"),
            output_price=Decimal("0"),
            context_window=8192
        )

        assert info.model_id == 'test-model'
        assert info.provider == 'ollama'
        assert info.supports_streaming is True
        assert info.input_price == Decimal("0")
        assert info.output_price == Decimal("0")

    def test_ollama_model_info_format(self):
        """Ollama list_models returns properly formatted ModelInfo."""
        from gateway.providers.ollama_provider import OllamaProvider
        from gateway.providers.base import ModelInfo

        with patch('gateway.providers.ollama_provider.requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                'models': [{
                    'name': 'qwen3:1.7b',
                    'details': {
                        'parameter_size': '1.7B',
                        'context_length': 16384,
                        'capabilities': ['tools']
                    }
                }]
            }

            provider = OllamaProvider()
            models = provider.list_models()

            assert len(models) == 1
            model = models[0]
            assert isinstance(model, ModelInfo)
            assert model.model_id == 'qwen3:1.7b'
            assert '1.7B' in model.name
            assert model.supports_function_calling is True
            assert model.supports_vision is False
            assert model.context_window == 16384

    def test_ollama_vision_model_detection(self):
        """Ollama list_models detects vision capability by name (llava, vision)."""
        from gateway.providers.ollama_provider import OllamaProvider
        from gateway.providers.base import ModelInfo

        with patch('gateway.providers.ollama_provider.requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                'models': [{
                    'name': 'llava:7b',
                    'details': {
                        'parameter_size': '7B',
                        'context_length': 4096,
                        'capabilities': ['vision']
                    }
                }]
            }

            provider = OllamaProvider()
            models = provider.list_models()

            assert len(models) == 1
            model = models[0]
            assert model.model_id == 'llava:7b'
            assert model.supports_vision is True
