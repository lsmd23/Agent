"""Shared LLM client for real benchmark runners."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

import requests


@dataclass
class LLMClient:
    provider: str
    model: str
    max_tokens: int = 512
    temperature: float = 0.0
    calls: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_env(cls, *, max_tokens: int = 512, temperature: float = 0.0) -> LLMClient:
        provider = os.environ.get("LLM_PROVIDER", "openai")
        model = os.environ.get("LLM_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
        return cls(provider=provider, model=model, max_tokens=max_tokens, temperature=temperature)

    def complete(self, prompt: str, *, module_id: str = "llm") -> tuple[str, dict[str, Any], int]:
        started = time.time()
        text, metadata = model_call(
            self.provider,
            self.model,
            prompt,
            self.max_tokens,
            self.temperature,
        )
        latency_ms = int((time.time() - started) * 1000)
        record = {
            "module_id": module_id,
            "provider": self.provider,
            "model": self.model,
            "prompt": prompt,
            "output": text,
            "latency_ms": latency_ms,
            "usage": metadata,
        }
        self.calls.append(record)
        return text, metadata, latency_ms


def call_openai_compatible(model: str, prompt: str, max_tokens: int, temperature: float) -> tuple[str, dict[str, Any]]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    response = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    text = data["choices"][0]["message"]["content"]
    return text, {"provider_response_id": data.get("id"), "usage": data.get("usage", {})}


def call_ollama(model: str, prompt: str, max_tokens: int, temperature: float) -> tuple[str, dict[str, Any]]:
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    response = requests.post(
        f"{base_url}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        },
        timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("message", {}).get("content", ""), {
        "eval_count": data.get("eval_count"),
        "prompt_eval_count": data.get("prompt_eval_count"),
        "total_duration": data.get("total_duration"),
    }


def model_call(provider: str, model: str, prompt: str, max_tokens: int, temperature: float) -> tuple[str, dict[str, Any]]:
    if provider == "openai":
        return call_openai_compatible(model, prompt, max_tokens, temperature)
    if provider == "ollama":
        return call_ollama(model, prompt, max_tokens, temperature)
    raise ValueError(f"Unsupported provider={provider!r}")
