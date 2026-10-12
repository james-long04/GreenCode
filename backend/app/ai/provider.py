"""Model/provider abstraction.

The proposal lists "weak local model" as a risk and mitigates it with a
provider abstraction so the model is an experimental variable rather than a
hard-coded dependency. ``LLMProvider`` is the only interface the pipeline uses;
``OllamaProvider`` is the production implementation and ``MockProvider`` lets
the whole pipeline (and the test-suite) run without a GPU.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import Settings, get_settings


@dataclass
class GenerationResult:
    text: str
    model: str
    provider: str
    duration_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def generate(self, prompt: str, system: str | None = None) -> GenerationResult: ...

    @abstractmethod
    def model_name(self) -> str: ...

    def health(self) -> dict[str, Any]:
        return {"provider": self.name, "ok": True}


class OllamaProvider(LLMProvider):
    """Talks to a locally running Ollama server via its HTTP API."""

    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: float = 300.0,
                 temperature: float = 0.0, seed: int = 42, num_ctx: int = 8192) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.seed = seed
        self.num_ctx = num_ctx

    def model_name(self) -> str:
        return self.model

    def generate(self, prompt: str, system: str | None = None) -> GenerationResult:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            # Deterministic decoding so repeated experiments are reproducible.
            "options": {"temperature": self.temperature, "seed": self.seed, "num_ctx": self.num_ctx},
        }
        if system:
            payload["system"] = system
        start = time.perf_counter()
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
        duration_ms = (time.perf_counter() - start) * 1000
        return GenerationResult(
            text=data.get("response", ""),
            model=data.get("model", self.model),
            provider=self.name,
            duration_ms=duration_ms,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
            raw={k: v for k, v in data.items() if k != "response"},
        )

    def health(self) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                models = [m.get("name") for m in resp.json().get("models", [])]
            return {"provider": self.name, "ok": True, "model": self.model,
                    "model_available": self.model in models, "models": models}
        except Exception as err:  # noqa: BLE001
            return {"provider": self.name, "ok": False, "model": self.model, "error": str(err)}


class MockProvider(LLMProvider):
    """Deterministic stand-in for tests and offline demos.

    It returns a canned response if one is registered for the prompt (keyed by a
    substring), otherwise it echoes the original code back unchanged inside a
    fenced block — which exercises the "candidate is correct but no faster" path.
    """

    name = "mock"

    def __init__(self, responses: dict[str, str] | None = None, model: str = "mock-model") -> None:
        self.responses = responses or {}
        self.model = model
        self.calls: list[dict[str, Any]] = []

    def model_name(self) -> str:
        return self.model

    def generate(self, prompt: str, system: str | None = None) -> GenerationResult:
        self.calls.append({"prompt": prompt, "system": system})
        text = None
        for key, value in self.responses.items():
            if key in prompt:
                text = value
                break
        if text is None:
            text = _echo_original(prompt)
        return GenerationResult(text=text, model=self.model, provider=self.name, duration_ms=1.0,
                                prompt_tokens=len(prompt.split()), completion_tokens=len(text.split()))


def _echo_original(prompt: str) -> str:
    """Pull the original code block out of a prompt and return it as the 'optimisation'."""
    marker = "```"
    anchor = prompt.find("Original:")
    first = prompt.find(marker, anchor if anchor >= 0 else 0)
    if first == -1:
        return prompt
    second = prompt.find(marker, first + 3)
    if second == -1:
        return prompt[first:]
    return prompt[first : second + 3]


def build_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    if settings.llm_provider == "mock":
        return MockProvider()
    if settings.llm_provider == "ollama":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.ollama_timeout_seconds,
            temperature=settings.llm_temperature,
            seed=settings.llm_seed,
        )
    raise ValueError(f"Unknown LLM provider '{settings.llm_provider}'")


def describe_provider(provider: LLMProvider) -> str:
    return json.dumps({"provider": provider.name, "model": provider.model_name()})
