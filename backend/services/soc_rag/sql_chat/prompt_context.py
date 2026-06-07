"""Build LLM prompts with conversation context (no keyword routing)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def format_conversation_for_sql(
    messages: Optional[List[Dict[str, Any]]],
    question: str,
    *,
    max_turns: int = 8,
) -> str:
    """
    User prompt for classify / SQL generation / answer synthesis.

    Includes recent turns so follow-ups (e.g. "which of them is high?") resolve
    against prior assistant lists, not only the last user line.
    """
    q = (question or "").strip()
    parts: List[str] = []
    if messages and len(messages) > 1:
        recent = messages[-max_turns:]
        parts.append(
            "Conversation (use for follow-ups — pronouns like them/those refer to prior turns):\n"
            + json.dumps(recent, ensure_ascii=False)
        )
    parts.append("Latest user question:\n" + (q or "(empty)"))
    return "\n\n".join(parts)
