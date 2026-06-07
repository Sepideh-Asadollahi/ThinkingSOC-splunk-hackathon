"""User-message builders for each LLM stage (canonical + prior JSON)."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from models.mcp import McpHunterEvidence, McpJudgeEvidence


def system_context_user_block(canonical_prefix: str) -> str:
    return (
        "Refer to the **System Context** as the ground truth.\n\n"
        "## System Context\n"
        + canonical_prefix
    )


def defender_user_message(canonical_prefix: str) -> str:
    return (
        "Apply the Defender persona and rules from your system instructions. "
        "Return only the JSON object.\n\n"
        + system_context_user_block(canonical_prefix)
    )


def hunter_user_message(
    canonical_prefix: str,
    defender_output: Dict[str, Any],
    *,
    hunter_mcp: Optional[McpHunterEvidence] = None,
) -> str:
    from splunk.mcp.hunter_judge_context import format_hunter_mcp_for_prompt

    prior = json.dumps(defender_output, sort_keys=True, ensure_ascii=False, default=str)
    return (
        "Apply the Hunter persona. You receive the canonical alert context plus the Defender JSON. "
        "Return only one JSON object (keys: narrative, splunk_search_suggestions). "
        "Do not return raw SPL lines outside JSON.\n\n"
        + system_context_user_block(canonical_prefix)
        + "\n\n## Prior analyst output (Defender)\n"
        + prior
        + format_hunter_mcp_for_prompt(hunter_mcp)
    )


def judge_user_message(
    canonical_prefix: str,
    defender_output: Dict[str, Any],
    hunter_output: Dict[str, Any],
    *,
    hunter_mcp: Optional[McpHunterEvidence] = None,
    judge_mcp: Optional[McpJudgeEvidence] = None,
) -> str:
    from splunk.mcp.hunter_judge_context import format_hunter_mcp_for_prompt, format_judge_mcp_for_prompt

    d = json.dumps(defender_output, sort_keys=True, ensure_ascii=False, default=str)
    h = json.dumps(hunter_output, sort_keys=True, ensure_ascii=False, default=str)
    return (
        "Apply the Judge persona. Reconcile Defender and Hunter; use identity and risk from System Context. "
        "Return only the JSON object.\n\n"
        + system_context_user_block(canonical_prefix)
        + "\n\n## Defender output\n"
        + d
        + "\n\n## Hunter output\n"
        + h
        + format_hunter_mcp_for_prompt(hunter_mcp, stage="judge")
        + format_judge_mcp_for_prompt(judge_mcp)
    )


def investigation_questions_user_message(
    canonical_prefix: str,
    defender_output: Dict[str, Any],
    hunter_output: Dict[str, Any],
    judge_output: Dict[str, Any],
    *,
    max_questions: int = 3,
    alert_fields_block: str = "",
) -> str:
    d = json.dumps(defender_output, sort_keys=True, ensure_ascii=False, default=str)
    h = json.dumps(hunter_output, sort_keys=True, ensure_ascii=False, default=str)
    j = json.dumps(judge_output, sort_keys=True, ensure_ascii=False, default=str)
    fields_section = (
        "\n\n## Alert search fields (anchor every question)\n"
        "Use these values in each question as field=value. "
        "Each question: one short sentence, one Splunk-retrievable fact only. "
        "Derive from **these fields** + Hunter/Judge — no generic checklist. "
        "Every question must pass your worth-it test: it either proves one attack step "
        "or moves one step toward the primary attack narrative; otherwise omit it. "
        "Each question must target a **different** attack pivot (process, file, network, identity). "
        "No curiosity questions. No Splunk-unanswerable policy/org questions. "
        "No time range. No compound multi-part questions.\n"
        + (alert_fields_block or "(see System Context)")
    )
    return (
        "Generate investigation questions only. Return only the JSON object.\n"
        "Hard limit: at most {0} questions (fewer is OK if not attack-worth). "
        "Self-filter: before including a question, confirm the follow-up SPL would return "
        "one attack-relevant field and materially narrow the main attack story.\n\n".format(
            max(1, int(max_questions))
        )
        + system_context_user_block(canonical_prefix)
        + fields_section
        + "\n\n## Defender output\n"
        + d
        + "\n\n## Hunter output\n"
        + h
        + "\n\n## Judge output\n"
        + j
    )


def framework_mapping_user_message(
    canonical_prefix: str,
    defender_output: Dict[str, Any],
    hunter_output: Dict[str, Any],
    judge_output: Dict[str, Any],
) -> str:
    d = json.dumps(defender_output, sort_keys=True, ensure_ascii=False, default=str)
    h = json.dumps(hunter_output, sort_keys=True, ensure_ascii=False, default=str)
    j = json.dumps(judge_output, sort_keys=True, ensure_ascii=False, default=str)
    return (
        "Generate framework mapping only. Return only the JSON object.\n\n"
        + system_context_user_block(canonical_prefix)
        + "\n\n## Defender output\n"
        + d
        + "\n\n## Hunter output\n"
        + h
        + "\n\n## Judge output\n"
        + j
    )
