"""OpenAI-compatible provider — Groq, Together, LM Studio, vLLM, llama.cpp
server, etc. Anything that speaks /v1/chat/completions.

API key is read from the env var named in config (api_key_env); some local
servers need no key at all.
"""

from __future__ import annotations

import os

import httpx

from .base import Provider


class OpenAICompatProvider(Provider):
    name = "openai_compat"

    def generate(self, prompt: str, system: str | None = None) -> str:
        base = self.cfg.get("base_url", "").rstrip("/")
        if not base:
            raise ValueError("openai_compat: base_url not configured in .eros/config.toml")
        headers = {}
        key_env = self.cfg.get("api_key_env", "")
        if key_env and os.environ.get(key_env):
            headers["Authorization"] = f"Bearer {os.environ[key_env]}"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = httpx.post(
            f"{base}/chat/completions",
            headers=headers,
            json={
                "model": self.model,
                "messages": messages,
                "max_tokens": self.cfg.get("max_tokens", 8192),
            },
            timeout=self.cfg.get("timeout_s", 600),
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
