"""
LLM provider abstraction. Selected via LLM_PROVIDER in config
("ollama" | "anthropic" | "mock").

NOT exercised end-to-end in the build sandbox: no Ollama server is running
there, and no live api.anthropic.com calls were made. The "mock" provider IS
exercised by tests so the streaming/citation-checking logic downstream in
rag_pipeline.py and routes.py is verified against the real interface shape.
See HANDOFF.md step 2/3.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator


class LLMClient(ABC):
    @abstractmethod
    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """Yield response text incrementally (token/chunk by chunk)."""
        ...


class OllamaLLMClient(LLMClient):
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        import httpx
        import json

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": True},
            ) as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
                    if data.get("done"):
                        break


class AnthropicLLMClient(LLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        async with client.messages.stream(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text


class MockLLMClient(LLMClient):
    """Deterministic canned-response client for tests / offline dev. Echoes
    back a templated answer that includes a fabricated citation marker so
    the citation-faithfulness checker in rag_pipeline.py has something
    concrete to validate against retrieved chunks in tests."""

    def __init__(self, canned_response: str | None = None) -> None:
        self.canned_response = canned_response or (
            "Based on the provided literature, the requested information is "
            "summarized here [doc_id:0]."
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        for word in self.canned_response.split(" "):
            yield word + " "


def build_llm_client(
    provider: str,
    ollama_base_url: str = "",
    ollama_model: str = "",
    anthropic_api_key: str = "",
    anthropic_model: str = "",
) -> LLMClient:
    if provider == "ollama":
        return OllamaLLMClient(base_url=ollama_base_url, model=ollama_model)
    if provider == "anthropic":
        return AnthropicLLMClient(api_key=anthropic_api_key, model=anthropic_model)
    if provider == "mock":
        return MockLLMClient()
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
