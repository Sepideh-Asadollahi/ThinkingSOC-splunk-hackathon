"""SOC Chat SQL prompt context and triage enrichment."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from config import Settings
from services.soc_rag.sql_chat.enrich import enrich_rows_with_triage
from services.soc_rag.sql_chat.prompt_context import format_conversation_for_sql


def test_format_conversation_includes_history() -> None:
    messages = [
        {"role": "user", "content": "List alerts"},
        {"role": "assistant", "content": "3 items"},
        {"role": "user", "content": "Which of them is high?"},
    ]
    text = format_conversation_for_sql(messages, "Which of them is high?")
    assert "Conversation" in text
    assert "Which of them is high?" in text
    assert "List alerts" in text


@pytest.mark.asyncio
async def test_enrich_rows_adds_priority_from_payload(test_settings: Settings) -> None:
    rows = [
        {
            "id": 1,
            "search_name": "Brute Force",
            "tsoc_record_type": "soc_analysis",
            "payload": {
                "tsoc_record_type": "soc_analysis",
                "analysis": {
                    "triage": {
                        "source_track": "security",
                        "triage_score": 68,
                        "confidence_score": 0.8,
                        "priority_rationale": "test",
                        "investigation_priority": "high",
                        "review_verdict": "NEEDS_HUMAN_REVIEW",
                        "needs_human_review": True,
                    }
                },
            },
        },
    ]
    out = await enrich_rows_with_triage(
        test_settings,
        rows,
        tables_used=["tsoc_records"],
    )
    assert out[0]["investigation_priority"] == "high"
    assert out[0]["triage_score"] == 68


@pytest.mark.asyncio
async def test_enrich_fetches_by_id_when_payload_missing(test_settings: Settings) -> None:
    stored = {
        "id": 5,
        "tsoc_record_type": "soc_analysis",
        "search_name": "Brute Force",
        "payload": {
            "tsoc_record_type": "soc_analysis",
            "analysis": {
                "judge": {
                    "verdict": "NEEDS_HUMAN_REVIEW",
                    "priority": "high",
                    "confidence": 0.9,
                    "rationale": "test",
                    "recommended_next_step": "review",
                },
            },
        },
    }
    rows = [{"id": 5, "search_name": "Brute Force", "tsoc_record_type": "soc_analysis"}]

    with patch(
        "services.soc_rag.sql_chat.enrich.get_stored_event_by_id",
        new_callable=AsyncMock,
        return_value=stored,
    ):
        out = await enrich_rows_with_triage(
            test_settings,
            rows,
            tables_used=["tsoc_records"],
        )
    assert out[0].get("investigation_priority") in ("high", "critical")
