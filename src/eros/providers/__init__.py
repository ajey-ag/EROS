"""Provider layer: swappable LLM/agent backends behind one interface."""

from __future__ import annotations

from pathlib import Path

from ..config import provider_config
from .base import Provider


def get_provider(root: Path, name: str | None = None, model: str | None = None) -> Provider:
    chosen, cfg = provider_config(root, name)
    if model:
        cfg = {**cfg, "model": model}
    if chosen == "claude_code":
        from .claude_code import ClaudeCodeProvider
        return ClaudeCodeProvider(cfg)
    if chosen == "anthropic":
        from .anthropic_api import AnthropicProvider
        return AnthropicProvider(cfg)
    if chosen == "ollama":
        from .ollama import OllamaProvider
        return OllamaProvider(cfg)
    from .openai_compat import OpenAICompatProvider
    return OpenAICompatProvider(cfg)
