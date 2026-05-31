"""
Unified LLM client supporting Gemini, OpenAI, Claude, and Ollama.
Routes to the configured primary provider with automatic fallback.
"""
import os
from typing import Any, Dict, Optional

from core.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    """Multi-provider LLM wrapper with primary/fallback routing.

    Providers are initialized lazily based on config; unavailable SDKs
    are silently skipped so the system degrades gracefully.
    """

    def __init__(self, config):
        """
        Args:
            config: A :class:`Settings` instance or a plain dict supporting
                    ``.get(key, default)`` dot-notation.
        """
        self._config = config
        self.primary = config.get("llm.primary", "gemini")
        self.fallback = config.get("llm.fallback", "ollama")
        self.providers: Dict[str, Any] = {}
        self.providers_config: Dict[str, Dict] = {}
        self._init_providers()

    # ── Initialisation ──────────────────────────────────────────────

    def _init_providers(self) -> None:
        """Create client objects only for *enabled* providers."""
        for name in ("gemini", "openai", "claude", "ollama"):
            if self._config.get(f"llm.providers.{name}.enabled", False):
                try:
                    provider = self._create_provider(name)
                    if provider is not None:
                        self.providers[name] = provider
                        logger.info("LLM provider '%s' initialised", name)
                except Exception as exc:
                    logger.warning("Failed to init provider '%s': %s", name, exc)

        if not self.providers:
            logger.warning("No LLM providers enabled – LLM features will be unavailable")

    def _create_provider(self, name: str):
        """Factory for provider-specific SDK clients."""
        if name == "gemini":
            try:
                import google.generativeai as genai
            except ImportError:
                logger.warning("google-generativeai not installed; skipping Gemini")
                return None
            api_key_env = self._config.get("llm.providers.gemini.api_key_env", "GEMINI_API_KEY")
            api_key = os.getenv(api_key_env, "")
            if not api_key:
                logger.warning("Env var %s not set; Gemini will fail at call time", api_key_env)
            genai.configure(api_key=api_key)
            model_name = self._config.get("llm.providers.gemini.model", "gemini-2.0-flash")
            self.providers_config["gemini"] = {"model": model_name}
            return genai.GenerativeModel(model_name)

        elif name == "openai":
            try:
                from openai import AsyncOpenAI
            except ImportError:
                logger.warning("openai SDK not installed; skipping OpenAI")
                return None
            api_key_env = self._config.get("llm.providers.openai.api_key_env", "OPENAI_API_KEY")
            model = self._config.get("llm.providers.openai.model", "gpt-4o")
            self.providers_config["openai"] = {"model": model}
            return AsyncOpenAI(api_key=os.getenv(api_key_env, ""))

        elif name == "claude":
            try:
                import anthropic
            except ImportError:
                logger.warning("anthropic SDK not installed; skipping Claude")
                return None
            api_key_env = self._config.get("llm.providers.claude.api_key_env", "ANTHROPIC_API_KEY")
            model = self._config.get("llm.providers.claude.model", "claude-sonnet-4-20250514")
            self.providers_config["claude"] = {"model": model}
            return anthropic.AsyncAnthropic(api_key=os.getenv(api_key_env, ""))

        elif name == "ollama":
            base_url = self._config.get("llm.providers.ollama.base_url", "http://localhost:11434")
            model = self._config.get("llm.providers.ollama.model", "llama3")
            self.providers_config["ollama"] = {"model": model}
            return {"base_url": base_url, "model": model}

        return None

    # ── Public API ──────────────────────────────────────────────────

    async def generate(self, prompt: str, temperature: float = 0.5,
                       max_tokens: int = 1500) -> str:
        """Generate text using primary provider with fallback.

        Raises:
            RuntimeError: When no providers are available.
            Exception: When both primary and fallback fail.
        """
        if not self.providers:
            raise RuntimeError("No LLM providers are available")

        try:
            return await self._call_provider(self.primary, prompt, temperature, max_tokens)
        except Exception as primary_err:
            logger.warning("Primary provider '%s' failed: %s", self.primary, primary_err)
            if self.fallback and self.fallback != self.primary and self.fallback in self.providers:
                logger.info("Falling back to '%s'", self.fallback)
                return await self._call_provider(self.fallback, prompt, temperature, max_tokens)
            raise

    async def _call_provider(self, name: str, prompt: str,
                             temperature: float, max_tokens: int) -> str:
        """Dispatch to the correct provider SDK."""
        provider = self.providers.get(name)
        if not provider:
            raise ValueError(f"LLM provider '{name}' not initialised or not enabled")

        if name == "gemini":
            response = provider.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                },
            )
            return response.text

        elif name == "openai":
            response = await provider.chat.completions.create(
                model=self.providers_config["openai"]["model"],
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content

        elif name == "claude":
            response = await provider.messages.create(
                model=self.providers_config["claude"]["model"],
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.content[0].text

        elif name == "ollama":
            import httpx

            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{provider['base_url']}/api/generate",
                    json={
                        "model": provider["model"],
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        },
                    },
                )
                resp.raise_for_status()
                return resp.json()["response"]

        raise ValueError(f"Unknown provider: {name}")
