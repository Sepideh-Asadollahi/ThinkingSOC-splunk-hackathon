"""SOC Chat Text-to-SQL — validator, intent, and orchestration (mocked LLM/DB)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import Settings
from services.soc_rag.sql_chat import (
    is_statistical_question,
    run_soc_sql_chat,
    validate_readonly_sql,
)
from services.soc_rag.sql_chat.answer import format_answer_from_rows
from services.soc_rag.sql_chat.generate import generate_sql
from services.soc_rag.sql_chat.prompt_context import format_conversation_for_sql
from services.soc_rag.sql_schema import SOC_SQL_SCHEMA_PROMPT, TABLE_SELECTION_GUIDE


class TestValidateReadonlySql:
    def test_accepts_simple_count(self) -> None:
        sql = validate_readonly_sql(
            "SELECT COUNT(*)::int AS cnt FROM tsoc_rag_documents WHERE doc_type = 'splunk_alert'"
        )
        assert "LIMIT" in sql.upper()

    def test_rejects_delete(self) -> None:
        with pytest.raises(ValueError):
            validate_readonly_sql("DELETE FROM tsoc_records")

    def test_rejects_update_keyword(self) -> None:
        with pytest.raises(ValueError, match="forbidden"):
            validate_readonly_sql(
                "SELECT COUNT(*)::int FROM tsoc_records WHERE tsoc_record_type = 'splunk_ingest' "
                "OR UPDATE tsoc_users SET risk_score = 0"
            )

    def test_rejects_multiple_statements(self) -> None:
        with pytest.raises(ValueError, match="multiple"):
            validate_readonly_sql("SELECT 1; SELECT 2")

    def test_rejects_unknown_table(self) -> None:
        with pytest.raises(ValueError, match="not allowed"):
            validate_readonly_sql("SELECT * FROM secret_table")

    def test_accepts_graph_findings(self) -> None:
        sql = validate_readonly_sql(
            "SELECT display_id, title, risk_score FROM graph_findings ORDER BY risk_score DESC LIMIT 5"
        )
        assert "graph_findings" in sql.lower()


@pytest.mark.asyncio
async def test_is_statistical_question_uses_llm(test_settings: Settings) -> None:
    with patch(
        "services.soc_rag.sql_chat.intent.litellm_chat_completion",
        new_callable=AsyncMock,
        return_value={"content": '{"is_statistical": true, "reason": "count"}'},
    ) as mock_llm:
        result = await is_statistical_question(
            test_settings,
            "How many high severity alerts?",
        )
        mock_llm.assert_called_once()
    assert result is True


@pytest.mark.asyncio
async def test_is_statistical_question_llm_says_false(test_settings: Settings) -> None:
    with patch(
        "services.soc_rag.sql_chat.intent.litellm_chat_completion",
        new_callable=AsyncMock,
        return_value={"content": '{"is_statistical": false, "reason": "explain"}'},
    ):
        result = await is_statistical_question(test_settings, "Explain this alert")
    assert result is False


@pytest.mark.asyncio
async def test_run_soc_sql_chat_mocked(test_settings: Settings) -> None:
    settings = test_settings.model_copy(
        update={
            "tsoc_chat_sql_enable": True,
            "tsoc_postgres_dsn": "postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc",
            "litellm_model": "gpt-4o-mini",
            "litellm_api_key": "sk-test",
        }
    )

    class _FakeRow:
        def keys(self) -> list[str]:
            return ["cnt"]

        def __getitem__(self, key: str) -> int:
            return 42

    mock_row = _FakeRow()
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[mock_row])
    mock_conn.execute = AsyncMock()
    mock_acquire = MagicMock()
    mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire.__aexit__ = AsyncMock(return_value=None)
    mock_pool = MagicMock()
    mock_pool.acquire.return_value = mock_acquire

    gen_json = (
        '{"sql": "SELECT COUNT(*)::int AS cnt FROM tsoc_rag_documents '
        'WHERE doc_type = \'splunk_alert\'", "tables_used": ["tsoc_rag_documents"]}'
    )

    with (
        patch(
            "services.soc_rag.sql_chat.generate.litellm_chat_completion",
            new_callable=AsyncMock,
            return_value={"content": gen_json},
        ),
        patch(
            "services.soc_rag.sql_chat.answer.litellm_chat_completion",
            new_callable=AsyncMock,
            return_value={"content": "You have 42 indexed alerts."},
        ),
        patch("services.soc_rag.sql_chat.execute.splunk_store_configured", return_value=True),
        patch("services.soc_rag.sql_chat.execute.pg._PG_POOL", mock_pool),
        patch("services.soc_rag.sql_chat.execute.init_store", new_callable=AsyncMock),
    ):
        resp = await run_soc_sql_chat(settings, "How many alerts are indexed?")

    assert "42" in resp.answer
    assert resp.sql_meta is not None
    assert resp.sql_meta.query_mode == "sql"
    assert "tsoc_rag_documents" in (resp.sql_meta.sql or "")
    assert resp.sql_meta.row_count == 1


class TestSqlSchemaCatalog:
    def test_schema_includes_table_selection_guide(self) -> None:
        assert "tsoc_rag_documents" in SOC_SQL_SCHEMA_PROMPT
        assert "tsoc_records" in SOC_SQL_SCHEMA_PROMPT
        assert "soc_analysis" in SOC_SQL_SCHEMA_PROMPT
        assert "investigation_priority" in SOC_SQL_SCHEMA_PROMPT
        assert TABLE_SELECTION_GUIDE in SOC_SQL_SCHEMA_PROMPT

    def test_schema_documents_priority_not_normalized_severity(self) -> None:
        assert "normalized" in SOC_SQL_SCHEMA_PROMPT
        assert "investigation_priority" in SOC_SQL_SCHEMA_PROMPT

    def test_format_empty_rows_fallback(self) -> None:
        ans = format_answer_from_rows(
            "How many users?",
            [],
            tables_used=["tsoc_users"],
        )
        assert "no rows" in ans.lower()

    def test_format_list_uses_sid_when_no_search_name(self) -> None:
        ans = format_answer_from_rows(
            "How many alerts available in SOC? List them",
            [
                {
                    "total_count": 2,
                    "search_name": "Brute Force",
                    "sid": "sid-a",
                    "tsoc_record_type": "soc_analysis",
                },
                {
                    "total_count": 2,
                    "search_name": None,
                    "sid": "final_verify",
                    "tsoc_record_type": "soc_analysis",
                },
            ],
            tables_used=["tsoc_records"],
        )
        assert "sid=final_verify" in ans
        assert "Brute Force" in ans
        assert "{" not in ans

    def test_format_graph_findings_list(self) -> None:
        ans = format_answer_from_rows(
            "Which correlation findings have the highest risk?",
            [
                {
                    "display_id": "GF-0003",
                    "title": "Operation Shadow Login — Automated Cluster",
                    "risk_score": 78,
                    "finding_type": "smart_attack_discovery",
                    "ticket_status": "open",
                },
            ],
            tables_used=["graph_findings"],
        )
        assert "GF-0003" in ans
        assert "Operation Shadow Login" in ans
        assert "risk=78" in ans
        assert "record" not in ans.lower()


@pytest.mark.asyncio
async def test_generate_sql_calls_llm(test_settings: Settings) -> None:
    settings = test_settings.model_copy(
        update={
            "litellm_model": "gpt-4o-mini",
            "litellm_api_key": "sk-test",
        }
    )
    llm_sql = (
        '{"sql": "SELECT COUNT(*) OVER ()::int AS total_count, display_name '
        'FROM tsoc_users ORDER BY display_name LIMIT 3", '
        '"tables_used": ["tsoc_users"]}'
    )
    with patch(
        "services.soc_rag.sql_chat.generate.litellm_chat_completion",
        new_callable=AsyncMock,
        return_value={"content": llm_sql},
    ) as mock_llm:
        sql, tables = await generate_sql(
            settings,
            "How many users do we have? Give me 3 names.",
            None,
        )
        assert mock_llm.call_count >= 1
    assert "tsoc_users" in sql
    assert "tsoc_users" in tables


@pytest.mark.asyncio
async def test_generate_sql_includes_conversation(test_settings: Settings) -> None:
    settings = test_settings.model_copy(
        update={
            "litellm_model": "gpt-4o-mini",
            "litellm_api_key": "sk-test",
        }
    )
    messages = [
        {"role": "user", "content": "List SOC alerts"},
        {"role": "assistant", "content": "3 items with priority=high"},
        {"role": "user", "content": "Which of them is high?"},
    ]
    llm_sql = (
        '{"sql": "SELECT search_name, sid FROM tsoc_records WHERE '
        'tsoc_record_type IN (\'soc_analysis\', \'observability_analysis\')", '
        '"tables_used": ["tsoc_records"]}'
    )
    with patch(
        "services.soc_rag.sql_chat.generate.litellm_chat_completion",
        new_callable=AsyncMock,
        return_value={"content": llm_sql},
    ) as mock_llm:
        await generate_sql(
            settings,
            "Which of them is high?",
            None,
            messages=messages,
        )
        call_user = mock_llm.call_args[0][1][1]["content"]
    assert "Conversation" in call_user
    assert "Which of them is high?" in call_user


def test_format_conversation_for_sql_latest_question() -> None:
    text = format_conversation_for_sql(
        [{"role": "user", "content": "hi"}],
        "count users",
    )
    assert "Latest user question" in text
    assert "count users" in text
