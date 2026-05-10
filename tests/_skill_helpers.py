"""Shared skill/eval token-counting harness.

Phase 10 ships this; Phase 11 SUBA-06 imports for the < 1000-token subagent
summary assertion; Phase 12 EVAL-04 imports for eval-harness budget checks.

Per Phase 10 RESEARCH §(i) + LOCKED DECISION D-02: tiktoken cl100k_base for
CI-friendly, deterministic, network-free token counting. Anthropic does not
publish their tokenizer; multiple sources (propelcode.ai, gopenai.com) report
cl100k undercounts the actual Anthropic tokenizer by ~10-15% for English
prose with markdown. We document a 10% safety margin so callers know to
enforce thresholds proportionally lower than Anthropic-spec recommendations
(e.g., enforce ≤ 4500 cl100k for a nominal 5000 Anthropic budget; ≤ 900
cl100k for a nominal 1000 Anthropic budget).
"""

from __future__ import annotations

import tiktoken

_ENCODER = tiktoken.get_encoding("cl100k_base")
"""Module-level encoder — cheap to construct, but cached so repeat callers
in the same pytest session don't re-resolve the BPE tables."""


def count_tokens(text: str) -> int:
    """Return the cl100k_base token count for *text*.

    cl100k is OpenAI's BPE tokenizer (gpt-3.5/4 era). It is an APPROXIMATION
    of Anthropic's tokenizer — see module docstring for the ~10-15% margin
    rationale. Callers MUST apply a safety margin when enforcing token
    budgets against Anthropic-spec thresholds.
    """
    return len(_ENCODER.encode(text))


def assert_under_budget(text: str, hard_budget: int, *, safety_margin_pct: int = 10) -> None:
    """Assert ``count_tokens(text) <= hard_budget * (1 - safety_margin_pct/100)``.

    Raises AssertionError with a message including the measured count and
    the effective cap. Callers should pass the Anthropic-spec budget as
    *hard_budget* (e.g., 5000 for SKILL.md SKLL-01).
    """
    effective = int(hard_budget * (100 - safety_margin_pct) / 100)
    n = count_tokens(text)
    assert n <= effective, (
        f"token budget exceeded: {n} cl100k tokens > {effective} "
        f"(hard cap {hard_budget} Anthropic; {safety_margin_pct}% safety "
        f"margin per RESEARCH §i + D-02)"
    )
