"""Load Observability system prompt `.md` files."""

from __future__ import annotations

from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

PROMPT_OBSERVABILITY_DIAGNOSER_SYSTEM = "prompt_observability_diagnoser_system.md"
PROMPT_OBSERVABILITY_RESPONDER_SYSTEM = "prompt_observability_responder_system.md"
PROMPT_OBSERVABILITY_OPS_JUDGE_SYSTEM = "prompt_observability_ops_judge_system.md"


def _load_prompt_file(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8")


def load_observability_diagnoser_system_prompt() -> str:
    return _load_prompt_file(PROMPT_OBSERVABILITY_DIAGNOSER_SYSTEM)


def load_observability_responder_system_prompt() -> str:
    return _load_prompt_file(PROMPT_OBSERVABILITY_RESPONDER_SYSTEM)


def load_observability_ops_judge_system_prompt() -> str:
    return _load_prompt_file(PROMPT_OBSERVABILITY_OPS_JUDGE_SYSTEM)
