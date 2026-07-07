"""Ollama provider — local open-source models (qwen2.5-coder, llama3.1, ...).

Text generation only; agent dispatch falls back to degraded patch mode
(inherited from Provider.agent_run).
"""

from __future__ import annotations

import httpx

from .base import Provider


class OllamaProvider(Provider):
    name = "ollama"

    def generate(self, prompt: str, system: str | None = None) -> str:
        base = self.cfg.get("base_url", "http://localhost:11434").rstrip("/")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = httpx.post(
            f"{base}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False},
            timeout=self.cfg.get("timeout_s", 600),
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]
