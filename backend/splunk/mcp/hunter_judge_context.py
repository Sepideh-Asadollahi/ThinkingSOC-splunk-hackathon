"""Splunk MCP enrichment for Hunter and Judge LangGraph stages."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from config import Settings, mcp_configured
from models.mcp import McpHunterEvidence, McpJudgeEvidence, McpQueryEvidence, McpSaiaAnswer
from services.llm.litellm_service import LiteLLMNotConfiguredError, litellm_chat_completion
from services.investigation.spl_predict_pipeline import (
    ALL_TIME_EARLIEST,
    ALL_TIME_LATEST,
    parse_mcp_execute_result,
)
from splunk.mcp.client import SplunkMcpClient
from splunk.mcp.context_builder import _extract_string_list
from splunk.mcp.errors import McpConnectionError, McpNotConfiguredError, McpToolError
from splunk.mcp.tool_registry import McpLogicalTool, resolve_tool_name

logger = logging.getLogger(__name__)

_HUNT_QUERY_ROW_LIMIT = 15
_JUDGE_VERIFY_ROW_LIMIT = 10
_SUMMARY_MAX_CHARS = 900
_SAIA_PROMPT_MAX = 1000
_SAIA_CONTEXT_MAX = 2000


def mcp_hunter_judge_enabled(settings: Settings) -> bool:
    return bool(mcp_configured(settings) and getattr(settings, "tsoc_mcp_hunter_judge_enabled", True))


def _escape_spl_value(value: Any) -> str:
    return str(value or "").replace('"', '\\"')


def _build_hunt_queries(normalized: Dict[str, Any]) -> List[str]:
    """Short read-only correlation searches from alert pivots."""
    queries: List[str] = []
    host = normalized.get("host") or normalized.get("dest")
    user = normalized.get("user") or normalized.get("src_user")
    if host:
        h = _escape_spl_value(host)
        queries.append(
            'search index=* host="{0}" | stats count by user, signature, action | head 15'.format(h)
        )
    if user:
        u = _escape_spl_value(user)
        queries.append(
            'search index=* (user="{0}" OR src_user="{0}") | stats count by host, action | head 15'.format(
                u
            )
        )
    if not queries:
        src = normalized.get("src")
        if src:
            s = _escape_spl_value(src)
            queries.append(
                'search index=* src="{0}" | stats count by dest, action | head 15'.format(s)
            )
    return queries[:2]


def _summarize_query_result(raw: Any) -> Tuple[int, str]:
    rows, total_rows, _ = parse_mcp_execute_result(raw)
    count = total_rows if total_rows is not None else len(rows)
    if not rows:
        return count, "(no rows)"
    preview = json.dumps(rows[:5], default=str, ensure_ascii=False)
    if len(preview) > _SUMMARY_MAX_CHARS:
        preview = preview[: _SUMMARY_MAX_CHARS - 3] + "..."
    return count, preview


def _truncate(text: str, max_chars: int) -> str:
    t = (text or "").strip()
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 3] + "..."


def _clean_excerpt(text: str, max_chars: int) -> str:
    """Trim free-text on a word/line boundary so prompts never cut mid-word."""
    t = " ".join((text or "").split())
    if not t:
        return ""
    if len(t) <= max_chars:
        return t
    cut = t[:max_chars]
    sep = max(cut.rfind(". "), cut.rfind("; "), cut.rfind(" "))
    if sep > 0:
        cut = cut[:sep]
    return cut.rstrip(" .;,") + "…"


def _extract_saia_answer(raw: Any) -> str:
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict):
        for key in ("answer", "response", "text", "explanation"):
            val = raw.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        content = raw.get("content")
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text") or ""))
            joined = "\n".join(p for p in parts if p).strip()
            if joined:
                return joined
    return str(raw or "").strip()[:_SUMMARY_MAX_CHARS]


def _judge_saia_questions(
    normalized: Dict[str, Any],
    search_name: Optional[str],
    defender_output: Dict[str, Any],
    hunter_output: Dict[str, Any],
) -> List[str]:
    host = _escape_spl_value(normalized.get("host") or normalized.get("dest") or "unknown")
    user = _escape_spl_value(normalized.get("user") or normalized.get("src_user") or "unknown")
    sn = _escape_spl_value(search_name or "security alert")
    defender = _clean_excerpt(str(defender_output.get("defender") or ""), 200) or "(none)"
    hunter_narr = _clean_excerpt(str(hunter_output.get("narrative") or ""), 200) or "(none)"

    q1 = (
        "For a Splunk SOC alert named '{0}' on host {1} and user {2}, "
        "what follow-up Splunk searches and data sources best confirm true positive "
        "vs benign activity? Be specific to observable fields.".format(sn, host, user)
    )
    q2 = (
        "Defender view: {0} "
        "Hunter view: {1} "
        "What Splunk evidence would most decisively reconcile these perspectives for host {2}?".format(
            defender,
            hunter_narr,
            host,
        )
    )
    return [_truncate(q, _SAIA_PROMPT_MAX) for q in (q1, q2)]


_SAIA_CONTEXT_FIELDS = (
    "host",
    "dest",
    "user",
    "src_user",
    "src",
    "signature",
    "signature_id",
    "index",
    "source",
    "sourcetype",
    "Image",
    "ParentImage",
)


def _build_saia_context(
    search_name: Optional[str],
    normalized: Dict[str, Any],
    defender_output: Dict[str, Any],
    hunter_output: Dict[str, Any],
) -> str:
    """Compact JSON context for SAIA — only key pivots to limit Splunk Cloud RAG load."""
    compact: Dict[str, Any] = {"search_name": search_name}
    for field in _SAIA_CONTEXT_FIELDS:
        val = normalized.get(field)
        if isinstance(val, str) and val.strip():
            compact[field] = val
    defender = _clean_excerpt(str(defender_output.get("defender") or ""), 300)
    hunter_narr = _clean_excerpt(str(hunter_output.get("narrative") or ""), 300)
    if defender:
        compact["defender"] = defender
    if hunter_narr:
        compact["hunter_narrative"] = hunter_narr
    return _truncate(
        json.dumps(compact, default=str, ensure_ascii=False),
        _SAIA_CONTEXT_MAX,
    )


async def _litellm_saia_fallback(
    settings: Settings,
    *,
    question: str,
    context: str,
) -> Optional[str]:
    """Answer a Judge SAIA question via LiteLLM when Splunk AI Assistant is unavailable."""
    if not (settings.litellm_model or "").strip():
        return None
    system = (
        "You are a Splunk SOC analyst assistant. Answer the question concisely with "
        "Splunk-specific, observable-field guidance (data sources, fields, SPL pivots). "
        "Do not invent results; give investigative steps."
    )
    user = "Question:\n{0}\n\nAlert context (JSON):\n{1}".format(question, context)
    try:
        out = await litellm_chat_completion(
            settings,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=settings.litellm_analysis_temperature,
            max_tokens=max(256, settings.litellm_analysis_max_tokens // 4),
        )
    except (LiteLLMNotConfiguredError, ValueError):
        return None
    except Exception as e:  # provider errors must not break the Judge stage
        logger.warning("judge mcp: litellm saia fallback failed: %s", e)
        return None
    for key in ("content", "thinking", "raw_content"):
        piece = str(out.get(key) or "").strip()
        if piece:
            return piece
    return None


def _judge_verification_query(normalized: Dict[str, Any]) -> Optional[str]:
    host = normalized.get("host") or normalized.get("dest")
    if not host:
        return None
    h = _escape_spl_value(host)
    return 'search index=* host="{0}" | stats count by sourcetype, source | head 10'.format(h)


async def _run_hunt_query(
    client: SplunkMcpClient,
    query: str,
    *,
    row_limit: int,
) -> McpQueryEvidence:
    try:
        raw = await client.call_tool(
            McpLogicalTool.SPLUNK_RUN_QUERY,
            {
                "query": query,
                "earliest_time": ALL_TIME_EARLIEST,
                "latest_time": ALL_TIME_LATEST,
                "row_limit": row_limit,
            },
        )
        count, summary = _summarize_query_result(raw)
        return McpQueryEvidence(query=query, row_count=count, summary=summary)
    except McpToolError as e:
        return McpQueryEvidence(query=query, row_count=0, summary="", error=str(e))


async def build_hunter_mcp_context(
    settings: Settings,
    *,
    normalized: Dict[str, Any],
    search_name: Optional[str],
    splunk_results: List[Dict[str, Any]],
    defender_output: Optional[Dict[str, Any]] = None,
    mcp_client: Optional[SplunkMcpClient] = None,
) -> Optional[McpHunterEvidence]:
    """
    Gather live Splunk hunt evidence via MCP before Hunter LLM reasoning.

    Uses ``splunk_get_metadata`` (sourcetypes) and ``splunk_run_query`` correlation searches.
    """
    _ = search_name, splunk_results, defender_output
    if not mcp_hunter_judge_enabled(settings):
        return None

    evidence = McpHunterEvidence()
    client = mcp_client
    if client is None:
        try:
            client = SplunkMcpClient(settings)
            await client.ensure_ready()
        except (McpConnectionError, McpNotConfiguredError, McpToolError) as e:
            logger.warning("hunter mcp: client init failed: %s", e)
            evidence.notes.append("MCP unavailable: {0}".format(e))
            return evidence if evidence.notes else None

    assert client is not None

    index = "*"
    if isinstance(normalized.get("index"), str) and normalized["index"].strip():
        index = normalized["index"].strip()

    if resolve_tool_name(client.tool_names, McpLogicalTool.SPLUNK_GET_METADATA):
        try:
            meta_args: Dict[str, Any] = {
                "index": index,
                "type": "sourcetypes",
                "earliest_time": "0",
                "latest_time": "now",
            }
            meta_st = await client.call_tool(McpLogicalTool.SPLUNK_GET_METADATA, meta_args)
            evidence.metadata_sourcetypes = _extract_string_list(
                meta_st, ("sourcetype", "name", "value")
            )[:20]
            evidence.tools_called.append("splunk_get_metadata:sourcetypes")
        except McpToolError as e:
            evidence.notes.append("get_metadata failed: {0}".format(e))

    if resolve_tool_name(client.tool_names, McpLogicalTool.SPLUNK_RUN_QUERY):
        for query in _build_hunt_queries(normalized):
            result = await _run_hunt_query(client, query, row_limit=_HUNT_QUERY_ROW_LIMIT)
            evidence.hunt_queries.append(result)
            evidence.tools_called.append("splunk_run_query")

    if not evidence.tools_called:
        return None
    return evidence


async def build_judge_mcp_context(
    settings: Settings,
    *,
    normalized: Dict[str, Any],
    search_name: Optional[str],
    defender_output: Dict[str, Any],
    hunter_output: Dict[str, Any],
    hunter_mcp: Optional[McpHunterEvidence] = None,
    mcp_client: Optional[SplunkMcpClient] = None,
) -> Optional[McpJudgeEvidence]:
    """
    Gather Splunk MCP SAIA answers and a verification query before Judge LLM verdict.
    """
    _ = hunter_mcp
    if not mcp_hunter_judge_enabled(settings):
        return None

    evidence = McpJudgeEvidence()
    client = mcp_client
    if client is None:
        try:
            client = SplunkMcpClient(settings)
            await client.ensure_ready()
        except (McpConnectionError, McpNotConfiguredError, McpToolError) as e:
            logger.warning("judge mcp: client init failed: %s", e)
            evidence.notes.append("MCP unavailable: {0}".format(e))
            return evidence if evidence.notes else None

    assert client is not None

    saia_tool = resolve_tool_name(client.tool_names, McpLogicalTool.SAIA_ASK_SPLUNK_QUESTION)
    if saia_tool:
        alert_ctx = _build_saia_context(search_name, normalized, defender_output, hunter_output)
        for question in _judge_saia_questions(
            normalized, search_name, defender_output, hunter_output
        ):
            try:
                raw = await client.call_tool(
                    McpLogicalTool.SAIA_ASK_SPLUNK_QUESTION,
                    {"prompt": question, "additional_context": alert_ctx},
                )
                evidence.saia_answers.append(
                    McpSaiaAnswer(question=question, answer=_extract_saia_answer(raw))
                )
                evidence.tools_called.append("saia_ask_splunk_question")
            except McpToolError as e:
                evidence.notes.append("saia_ask failed: {0}".format(e))
                fallback = await _litellm_saia_fallback(
                    settings, question=question, context=alert_ctx
                )
                if fallback:
                    evidence.saia_answers.append(
                        McpSaiaAnswer(
                            question=question,
                            answer="[LiteLLM fallback — Splunk AI Assistant unavailable]\n" + fallback,
                        )
                    )
                    evidence.tools_called.append("litellm_saia_fallback")

    verify_query = _judge_verification_query(normalized)
    if verify_query and resolve_tool_name(client.tool_names, McpLogicalTool.SPLUNK_RUN_QUERY):
        result = await _run_hunt_query(client, verify_query, row_limit=_JUDGE_VERIFY_ROW_LIMIT)
        evidence.verification_queries.append(result)
        evidence.tools_called.append("splunk_run_query")

    if not evidence.tools_called:
        return None
    return evidence


def format_hunter_mcp_for_prompt(
    evidence: Optional[McpHunterEvidence],
    *,
    stage: str = "hunter",
) -> str:
    if evidence is None or not evidence.tools_called:
        return ""
    if stage == "judge":
        header = (
            "\n\n## Splunk MCP hunt evidence (from Hunter stage)\n"
            "Live correlation queries run before Hunter — use row counts to weigh Hunter hypotheses "
            "against Defender skepticism.\n"
        )
    else:
        header = (
            "\n\n## Splunk MCP hunt evidence (live queries)\n"
            "Ground-truth results after Defender — expand or counter the Defender view. "
            "Cite row counts in narrative and SPL suggestions.\n"
        )
    return header + json.dumps(evidence.model_dump(mode="json"), ensure_ascii=False, default=str)


def format_judge_mcp_for_prompt(evidence: Optional[McpJudgeEvidence]) -> str:
    if evidence is None or not evidence.tools_called:
        return ""
    return (
        "\n\n## Splunk MCP verdict evidence (SAIA + verification)\n"
        "Read after Defender and Hunter outputs above. Weight SAIA guidance and verification "
        "query row counts in verdict, priority, and rationale.\n"
        + json.dumps(evidence.model_dump(mode="json"), ensure_ascii=False, default=str)
    )
