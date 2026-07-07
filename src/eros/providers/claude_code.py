"""Claude Code headless provider — the default agent engine.

Shells out to the `claude` CLI in print mode. Uses the caller's existing
Claude Code login, so no API key or separate billing is needed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .base import AgentResult, Provider


class ClaudeCodeError(RuntimeError):
    pass


class ClaudeCodeProvider(Provider):
    name = "claude_code"

    def _binary(self) -> str:
        binary = self.cfg.get("binary", "claude")
        resolved = shutil.which(binary) or (binary if Path(binary).exists() else None)
        if not resolved:
            raise ClaudeCodeError(
                f"claude binary not found ('{binary}'). Set [provider.claude_code] "
                "binary = '<full path to claude.exe>' in .eros/config.local.toml"
            )
        return resolved

    def _run(self, prompt: str, cwd: Path | None, extra_args: list[str]) -> dict:
        cmd = [self._binary(), "-p", prompt, "--output-format", "json", *extra_args]
        model = self.cfg.get("generate_model") or self.cfg.get("model") or ""
        if model:
            cmd += ["--model", model]
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.cfg.get("timeout_s", 900),
            )
        except subprocess.TimeoutExpired as e:
            raise ClaudeCodeError(f"claude timed out after {e.timeout}s") from e
        if proc.returncode != 0 and not proc.stdout.strip():
            raise ClaudeCodeError(f"claude exited {proc.returncode}: {proc.stderr[:2000]}")
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise ClaudeCodeError(
                f"could not parse claude output as JSON: {proc.stdout[:500]}"
            ) from e

    def generate(self, prompt: str, system: str | None = None) -> str:
        full = f"{system}\n\n{prompt}" if system else prompt
        data = self._run(full, cwd=None, extra_args=["--tools", ""])
        if data.get("is_error"):
            raise ClaudeCodeError(str(data.get("result", "unknown error"))[:2000])
        return data.get("result", "")

    def agent_run(self, spec: str, cwd: Path) -> AgentResult:
        data = self._run(spec, cwd=cwd, extra_args=["--permission-mode", "acceptEdits"])
        return AgentResult(
            success=not data.get("is_error", False),
            output=str(data.get("result", "")),
            agent_mode=True,
            cost_usd=data.get("total_cost_usd"),
            num_turns=data.get("num_turns"),
            raw=data,
        )
