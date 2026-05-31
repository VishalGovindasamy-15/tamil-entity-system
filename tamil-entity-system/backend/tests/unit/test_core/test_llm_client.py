"""Tests for core.llm_client — LLMClient with mocked providers."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.llm_client import LLMClient


class MockConfig:
    """Minimal mock that supports Settings.get() dot-notation."""

    def __init__(self, data=None):
        self._data = data or {}

    def get(self, key, default=None):
        parts = key.split(".")
        node = self._data
        for part in parts:
            if isinstance(node, dict):
                node = node.get(part)
            else:
                return default
            if node is None:
                return default
        return node


@pytest.fixture
def no_providers_config():
    return MockConfig({
        "llm": {
            "primary": "gemini",
            "fallback": "ollama",
            "providers": {
                "gemini": {"enabled": False},
                "openai": {"enabled": False},
                "claude": {"enabled": False},
                "ollama": {"enabled": False},
            },
        }
    })


@pytest.fixture
def ollama_only_config():
    return MockConfig({
        "llm": {
            "primary": "ollama",
            "fallback": "ollama",
            "providers": {
                "gemini": {"enabled": False},
                "openai": {"enabled": False},
                "claude": {"enabled": False},
                "ollama": {
                    "enabled": True,
                    "base_url": "http://localhost:11434",
                    "model": "llama3",
                },
            },
        }
    })


def test_no_providers_enabled(no_providers_config):
    client = LLMClient(no_providers_config)
    assert len(client.providers) == 0


def test_ollama_provider_init(ollama_only_config):
    client = LLMClient(ollama_only_config)
    assert "ollama" in client.providers
    assert client.providers["ollama"]["model"] == "llama3"


@pytest.mark.asyncio
async def test_generate_raises_when_no_providers(no_providers_config):
    client = LLMClient(no_providers_config)
    with pytest.raises(RuntimeError, match="No LLM providers"):
        await client.generate("hello")


@pytest.mark.asyncio
async def test_generate_ollama_calls_httpx(ollama_only_config):
    client = LLMClient(ollama_only_config)

    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "test output"}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await client.generate("test prompt", temperature=0.3)

    assert result == "test output"
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "llama3" in str(call_args)


@pytest.mark.asyncio
async def test_fallback_on_primary_failure():
    """When primary fails, fallback should be used."""
    config = MockConfig({
        "llm": {
            "primary": "gemini",
            "fallback": "ollama",
            "providers": {
                "gemini": {"enabled": True, "api_key_env": "GEMINI_API_KEY", "model": "gemini-2.0-flash"},
                "openai": {"enabled": False},
                "claude": {"enabled": False},
                "ollama": {"enabled": True, "base_url": "http://localhost:11434", "model": "llama3"},
            },
        }
    })

    with patch("core.llm_client.LLMClient._create_provider") as mock_create:
        # Gemini provider that will fail, ollama that will work
        mock_create.side_effect = lambda name: (
            MagicMock() if name == "gemini" else {"base_url": "http://localhost:11434", "model": "llama3"}
        )
        client = LLMClient(config)

    # Make primary (gemini) call fail
    async def fail_gemini(name, prompt, temp, max_t):
        if name == "gemini":
            raise Exception("Gemini API error")
        # Ollama success
        return "fallback result"

    client._call_provider = fail_gemini
    result = await client.generate("test")
    assert result == "fallback result"


@pytest.mark.asyncio
async def test_unknown_provider_raises():
    """_call_provider should raise for unknown provider names."""
    config = MockConfig({"llm": {"primary": "ollama", "fallback": "ollama",
                                 "providers": {"gemini": {"enabled": False}, "openai": {"enabled": False},
                                               "claude": {"enabled": False}, "ollama": {"enabled": False}}}})
    client = LLMClient(config)

    with pytest.raises(ValueError, match="not initialised"):
        await client._call_provider("unknown", "prompt", 0.5, 100)
