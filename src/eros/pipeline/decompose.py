"""decompose: charter.md -> architecture.md via an LLM."""

from __future__ import annotations

from ..providers.base import Provider
from ..store import Store

SYSTEM = """\
You are a pragmatic software architect. You design small, buildable systems for a
single engineer working on one laptop — no Kubernetes, no microservices, no cloud
unless the charter demands it. Favor boring technology and clear module boundaries.
"""

PROMPT = """\
Design the architecture for the following project. Write a complete `architecture.md`
document in markdown with EXACTLY these sections:

# Architecture: <project title>
## Overview            — 2-3 paragraphs: approach and why
## Components          — a numbered list; for each: name, responsibility, key interfaces
## Data model          — core entities and how they are stored
## Technology choices  — language, libraries, storage; one line of justification each
## Build order         — the order components should be built, with rationale
## Risks               — top 3 technical risks and mitigations

Rules:
- Output ONLY the markdown document, no preamble or commentary.
- 4-8 components. Each must be buildable in roughly one focused day or less.
- Design for the constraints stated in the charter.

PROJECT CHARTER:
---
{charter}
---
"""


def decompose(store: Store, slug: str, provider: Provider) -> str:
    charter = (store.project_dir(slug) / "charter.md").read_text(encoding="utf-8")
    doc = provider.generate(PROMPT.format(charter=charter), system=SYSTEM).strip()
    # strip a wrapping code fence if the model added one
    if doc.startswith("```"):
        doc = doc.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    out = store.project_dir(slug) / "architecture.md"
    out.write_text(doc + "\n", encoding="utf-8")
    return str(out)
