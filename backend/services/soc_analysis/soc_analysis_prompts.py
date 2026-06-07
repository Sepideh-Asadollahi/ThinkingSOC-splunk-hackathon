"""
Load SOC system prompt `.md` files for Defender, Hunter, and Judge.

Heavy alert/inventory data is **not** stored here; runtime code passes it under **## System Context** in the user message.
"""

from __future__ import annotations

from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

PROMPT_DEFENDER_SYSTEM = "prompt_defender_system.md"
PROMPT_HUNTER_SYSTEM = "prompt_hunter_system.md"
PROMPT_JUDGE_SYSTEM = "prompt_judge_system.md"
PROMPT_INVESTIGATION_QUESTIONS_SYSTEM = "prompt_investigation_questions_system.md"
PROMPT_FRAMEWORK_MAPPING_SYSTEM = "prompt_framework_mapping_system.md"
PROMPT_ADMIN_ORG_GAP_SYSTEM = "prompt_admin_org_gap_system.md"
PROMPT_ROOT_CAUSE_SPL_SYSTEM = "prompt_root_cause_spl_system.md"


def load_prompt_file(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8")


def load_defender_system_prompt() -> str:
    return load_prompt_file(PROMPT_DEFENDER_SYSTEM)


def load_hunter_system_prompt() -> str:
    return load_prompt_file(PROMPT_HUNTER_SYSTEM)


def load_judge_system_prompt() -> str:
    return load_prompt_file(PROMPT_JUDGE_SYSTEM)


def load_investigation_questions_system_prompt() -> str:
    return load_prompt_file(PROMPT_INVESTIGATION_QUESTIONS_SYSTEM)

def load_framework_mapping_system_prompt() -> str:
    return load_prompt_file(PROMPT_FRAMEWORK_MAPPING_SYSTEM)


def load_admin_org_gap_system_prompt() -> str:
    return load_prompt_file(PROMPT_ADMIN_ORG_GAP_SYSTEM)


def load_root_cause_spl_system_prompt() -> str:
    return load_prompt_file(PROMPT_ROOT_CAUSE_SPL_SYSTEM)
