"""Configuration: .eros/config.toml (committed) merged with .eros/config.local.toml
(gitignored, machine-specific). API keys are referenced by env-var name only.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "provider": {
        "default": "claude_code",
        "claude_code": {
            "binary": "claude",
            "timeout_s": 900,
            "generate_model": "",  # empty = CLI default
        },
        "anthropic": {
            "model": "claude-sonnet-5",
            "api_key_env": "ANTHROPIC_API_KEY",
            "base_url": "https://api.anthropic.com",
            "max_tokens": 8192,
        },
        "ollama": {
            "base_url": "http://localhost:11434",
            "model": "qwen2.5-coder:7b",
        },
        "openai_compat": {
            "base_url": "http://localhost:1234/v1",
            "model": "",
            "api_key_env": "OPENAI_COMPAT_API_KEY",
            "max_tokens": 8192,
        },
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(root: Path) -> dict:
    cfg = DEFAULTS
    for name in ["config.toml", "config.local.toml"]:
        path = root / ".eros" / name
        if path.exists():
            with path.open("rb") as f:
                cfg = _deep_merge(cfg, tomllib.load(f))
    return cfg


def provider_config(root: Path, name: str | None = None) -> tuple[str, dict]:
    cfg = load_config(root)["provider"]
    chosen = name or cfg["default"]
    if chosen not in ("claude_code", "anthropic", "ollama", "openai_compat"):
        raise ValueError(f"unknown provider '{chosen}'")
    return chosen, cfg.get(chosen, {})
