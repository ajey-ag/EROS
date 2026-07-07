"""Anthropic API provider — direct Messages API via an API key.

Uses httpx directly so no extra dependency is required; the key is read from
the env var named in config (default ANTHROPIC_API_KEY).
"""

from __future__ import annotations

import os

import httpx

from .base import Provider


class AnthropicProvider(Provider):
    name = "anthropic"

    def generate(self, prompt: str, system: str | None = None) -> str:
        key_env = self.cfg.get("api_key_env", "ANTHROPIC_API_KEY")
        api_key = os.environ.get(key_env)
        if not api_key:
            raise ValueError(
                f"anthropic provider: env var {key_env} is not set. "
                "Export your API key or switch providers with `eros config`."
            )
        base = self.cfg.get("base_url", "https://api.anthropic.com").rstrip("/")
        body: dict = {
            "model": self.model or "claude-sonnet-5",
            "max_tokens": self.cfg.get("max_tokens", 8192),
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system
        resp = httpx.post(
            f"{base}/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=body,
            timeout=self.cfg.get("timeout_s", 600),
        )
        resp.raise_for_status()
        return "".join(
            block["text"] for block in resp.json()["content"] if block["type"] == "text"
        )
