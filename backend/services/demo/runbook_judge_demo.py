"""Idempotent, synthetic judge-tour data for the complete Runbook workflow.

The scenario is deliberately additive: it never truncates tables or replaces any
existing demo record.  Every seeded artifact carries a stable scenario identifier,
which makes repeat runs safe and keeps the install bundle deterministic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable

from config import Settings
from models.analysis import InvestigationQuestionItem
from models.runbook import (
    RunbookApproval,
    RunbookAutopilotEvent,
    RunbookAutopilotSession,
    RunbookRun,
    RunbookShadowRun,
    RunbookStep,
    SafeResponseAction,
    SafeResponseDecision,
    SafeResponsePreview,
    VerifiedRunbookDraft,
)
from services.soc_rag.backfill import backfill_from_storage
from services.soc_rag.chat_store import ensure_chat_schema
from services.splunk_json_store import pg

SCENARIO_ID = "judge-tour-runbook-v1"
SEARCH_NAME = "Judge Demo: Suspicious OAuth Token Replay"
SOURCE_SID = "demo-runbook-source-20260716"
TARGET_SID = "demo-runbook-target-20260716"
RUNBOOK_ID = "demo-rb-oauth-token-replay-v1"
SHADOW_RUN_ID = "demo-shadow-oauth-token-replay-v1"
PREVIEW_ID = "demo-preview-oauth-token-replay-v1"
AUTOPILOT_SESSION_ID = "demo-autopilot-oauth-token-replay-v1"
CHAT_CONVERSATION_ID = "demo-runbook-judge-tour-v1"

_SOURCE_AT = "2026-07-16T08:30:00+00:00"
_TARGET_AT = "2026-07-16T09:15:00+00:00"


def _question(
    *,
    question: str,
    spl: str,
    explanation: str,
    rows: list[Dict[str, Any]],
    transport: str,
) -> InvestigationQuestionItem:
    return InvestigationQuestionItem.model_validate(
        {
            "question": question,
            "spl": spl,
            "cim_datamodel": "Authentication",
            "explanation": explanation,
            "time_window": "earliest=-30m latest=now",
            "pivots": ["user", "src", "dest", "session_id"],
            "notes": [
                "Synthetic demo evidence; safe, read-only SPL.",
                "MCP is preferred and Splunk REST is the tested fallback.",
            ],
            "validation": {
                "method": "splunk_parser",
                "valid": True,
                "message": "SPL accepted by the parser.",
            },
            "spl_results": {
                "row_count": len(rows),
                "rows": rows,
                "truncated": False,
                "error": None,
                "execution_transport": transport,
            },
            "spl_results_analysis": {
                "finding": explanation,
                "confidence": "high",
                "demo_data": True,
            },
            "spl_saia_analysis": {
                "explanation": (
                    "The search command retrieves authentication telemetry and the "
                    "stats command aggregates only the fields needed for review."
                ),
                "optimized": False,
                "steps": ["explain"],
            },
        }
    )


def evidence_results() -> list[InvestigationQuestionItem]:
    """Return parser-valid, evidence-bearing results for every runbook step."""
    return [
        _question(
            question="Did the same identity authenticate from incompatible locations?",
            spl=(
                'search index=identity action=success user="alex.morgan" '
                '| stats earliest(_time) as first_seen latest(_time) as last_seen '
                'values(src) as sources values(country) as countries by user'
            ),
            explanation=(
                "The same identity produced successful sessions from Berlin and a "
                "documentation-range source within seven minutes."
            ),
            transport="mcp",
            rows=[
                {
                    "user": "alex.morgan",
                    "sources": ["192.0.2.44", "198.51.100.27"],
                    "countries": ["DE", "US"],
                    "first_seen": "2026-07-16T08:20:11Z",
                    "last_seen": "2026-07-16T08:27:04Z",
                }
            ],
        ),
        _question(
            question="Was one OAuth session replayed from a new client fingerprint?",
            spl=(
                'search index=identity user="alex.morgan" event_type=oauth_session '
                '| stats dc(client_fingerprint) as fingerprints values(src) as sources '
                'values(app) as apps by session_id user | where fingerprints>1'
            ),
            explanation=(
                "Session demo-session-7 was observed with two client fingerprints and "
                "two sources, which is consistent with replay."
            ),
            transport="rest",
            rows=[
                {
                    "session_id": "demo-session-7",
                    "user": "alex.morgan",
                    "fingerprints": 2,
                    "sources": ["192.0.2.44", "198.51.100.27"],
                    "apps": ["Demo CRM"],
                }
            ],
        ),
        _question(
            question="Did the replayed session access a sensitive application?",
            spl=(
                'search index=identity session_id="demo-session-7" action=success '
                '| stats count values(resource) as resources values(src) as sources '
                'by user app risk_level'
            ),
            explanation=(
                "The replayed session reached a high-risk CRM export resource, so the "
                "case requires containment review."
            ),
            transport="mcp",
            rows=[
                {
                    "user": "alex.morgan",
                    "app": "Demo CRM",
                    "risk_level": "high",
                    "count": 3,
                    "resources": ["customer-export"],
                    "sources": ["198.51.100.27"],
                }
            ],
        ),
    ]


def _analysis_event(*, sid: str, observed_at: str, target: bool) -> Dict[str, Any]:
    source_ip = "203.0.113.84" if target else "198.51.100.27"
    session_id = "demo-session-8" if target else "demo-session-7"
    summary = (
        "A synthetic OAuth session for alex.morgan was reused from a new source and "
        "client fingerprint before accessing the Demo CRM export resource."
    )
    return {
        "tsoc_record_type": "soc_analysis",
        "sid": sid,
        "search_name": SEARCH_NAME,
        "row_index": 0,
        "demo_scenario_id": SCENARIO_ID,
        "stored_at": observed_at,
        "raw_alert": {
            "_time": observed_at,
            "user": "alex.morgan",
            "src": source_ip,
            "app": "Demo CRM",
            "session_id": session_id,
            "severity": "high",
        },
        "analysis_input": {
            "row_index": 0,
            "alert_fields": {
                "_time": observed_at,
                "user": "alex.morgan",
                "src": source_ip,
                "app": "Demo CRM",
                "session_id": session_id,
                "client_fingerprint": "demo-browser-b",
                "severity": "high",
                "signature": "OAuth session replay from a new client fingerprint",
                "search_name": SEARCH_NAME,
                "index": "identity",
                "sourcetype": "demo:oauth:audit",
            },
        },
        "analysis": {
            "summary": summary,
            "defender": (
                "The second source could reflect a corporate proxy, but the fingerprint "
                "change and sensitive export require corroboration before closure."
            ),
            "hunter": {
                "narrative": (
                    "Correlated authentication, session, and resource telemetry supports "
                    "a token-replay hypothesis using synthetic documentation addresses."
                ),
                "splunk_search_suggestions": [q.spl for q in evidence_results()],
            },
            "judge": {
                "verdict": "TRUE_POSITIVE",
                "priority": "high",
                "recommended_next_step": (
                    "Revoke the affected sessions only after analyst approval, preserve "
                    "identity evidence, and review account activity."
                ),
                "rationale": (
                    "Three independent, read-only searches corroborate location, client, "
                    "and sensitive-resource anomalies."
                ),
                "confidence": "high",
            },
            "investigation_questions": [
                q.model_dump(mode="json") for q in evidence_results()
            ],
            "enrichment": {
                "confidence": "medium",
                "resolved_user_id": "alex.morgan",
                "resolved_asset_id": None,
                "matched_relationship_ids": [],
                "notes": "Synthetic identity used only for the judge tour.",
            },
            "risk_context": "Demo CRM is a high-value application; all identities and IPs are synthetic.",
            "framework_mapping": [
                {
                    "framework": "MITRE ATT&CK",
                    "id": "T1528",
                    "name": "Steal Application Access Token",
                    "confidence": "high",
                    "rationale": "Session reuse from a changed fingerprint is consistent with token theft.",
                }
            ],
            "evidence_refs": ["user", "src", "app", "session_id", "client_fingerprint"],
            "evidence_chain": {
                "request": {"sid": sid, "search_name": SEARCH_NAME, "row_index": 0},
                "data_sources": {
                    "splunk_results_row_count": 3,
                    "synthetic_demo": True,
                },
                "reasoning_path": {
                    "analysis_path": "multi_agent",
                    "investigation_questions_count": 3,
                    "investigation_spl_executed_ok_count": 3,
                },
                "decision": {
                    "verdict": "TRUE_POSITIVE",
                    "priority": "high",
                    "needs_human_review": True,
                },
                "trace": {"evidence_refs_count": 5},
            },
        },
        "analysis_output": {"summary": summary, "verdict": "TRUE_POSITIVE"},
        "triage": {
            "review_verdict": "TRUE_POSITIVE",
            "investigation_priority": "critical",
            "triage_score": 92,
            "confidence_score": 0.94,
            "needs_human_review": True,
            "priority_rationale": "High-confidence session replay with sensitive resource access.",
            "source_track": "security",
            "report": {
                "headline": "CRITICAL — TRUE POSITIVE — score 92.",
                "recommended_action": "Acknowledge, review the evidence, then use ThinkingSOC Lite safely.",
                "factors": [],
                "why_verdict": "Three independent evidence pivots corroborate replay.",
                "why_priority": "A high-value application was accessed.",
                "signal_notes": [],
            },
            "signals": [],
            "mapped_from": {"judge.verdict": "TRUE_POSITIVE"},
        },
    }


def build_artifact_events(source_record_id: int, target_record_id: int) -> list[Dict[str, Any]]:
    """Build and validate every linked ThinkingSOC Lite artifact for the judge tour."""
    results = evidence_results()
    steps = [
        RunbookStep(
            step_id="step-1",
            title="Correlate identity locations",
            intent="Compare successful authentication sources for the affected identity.",
            expected_evidence="Distinct sources, countries, and event timestamps.",
            stop_condition="Stop and abstain when authentication telemetry is unavailable.",
        ),
        RunbookStep(
            step_id="step-2",
            title="Validate session fingerprint reuse",
            intent="Determine whether one OAuth session appears under multiple client fingerprints.",
            expected_evidence="A session identifier with more than one fingerprint and source.",
            stop_condition="Stop and abstain when session identifiers cannot be correlated.",
        ),
        RunbookStep(
            step_id="step-3",
            title="Measure sensitive resource access",
            intent="Correlate the suspect session with high-value application resources.",
            expected_evidence="Successful access to a risk-labelled resource.",
            stop_condition="Escalate for human review; never execute containment automatically.",
        ),
    ]
    draft = VerifiedRunbookDraft(
        runbook_id=RUNBOOK_ID,
        source_record_id=source_record_id,
        title="Investigate OAuth Token Replay with Identity Correlation",
        summary=(
            "Evidence-grounded procedure for validating an OAuth session seen from a "
            "new location and client fingerprint."
        ),
        applicable_search_name=SEARCH_NAME,
        source_verdict="TRUE_POSITIVE",
        steps=steps,
        decision_rule=(
            "Escalate when location, fingerprint, and sensitive-resource evidence "
            "corroborate replay; otherwise abstain."
        ),
        limitations=[
            "Exact Alert Name matching is mandatory.",
            "The workflow is read-only and all response actions remain human-gated.",
            "Addresses, identities, and applications in this tour are synthetic.",
        ],
        source_results=results,
        status="SOURCE_VERIFIED",
        configured_model="judge-demo/evidence-grounded",
        model="judge-demo/evidence-grounded",
        prompt_tokens=1840,
        completion_tokens=612,
        generation_duration_ms=4200,
        verification_duration_ms=1850,
        compile_duration_ms=6050,
        parser_valid_step_count=3,
        successful_step_count=3,
        total_evidence_rows=3,
        revision=1,
        origin="compiled",
        revision_note="Curated end-to-end judge tour using synthetic evidence.",
        created_at="2026-07-16T08:36:30+00:00",
    )
    approval = RunbookApproval(
        runbook_id=RUNBOOK_ID,
        source_record_id=source_record_id,
        decision="approve",
        analyst="demo.soc.lead",
        note="Approved after parser validation, source evidence review, and shadow replay.",
        created_at="2026-07-16T08:45:00+00:00",
    )
    shadow = RunbookShadowRun(
        shadow_run_id=SHADOW_RUN_ID,
        runbook_id=RUNBOOK_ID,
        source_record_id=source_record_id,
        target_record_id=target_record_id,
        source_sid=SOURCE_SID,
        target_sid=TARGET_SID,
        search_name=SEARCH_NAME,
        status="EVIDENCE_FOUND",
        results=results,
        duration_ms=2310,
        estimated_manual_minutes=30,
        projected_minutes_saved=24.0,
        projected_labor_savings_usd=26.0,
        parser_valid_step_count=3,
        successful_step_count=3,
        total_evidence_rows=3,
        execution_error_count=0,
        created_at="2026-07-16T08:42:00+00:00",
    )
    run = RunbookRun(
        runbook_id=RUNBOOK_ID,
        source_record_id=source_record_id,
        target_record_id=target_record_id,
        status="REUSED",
        results=results,
        duration_ms=2460,
        estimated_manual_minutes=30,
        estimated_minutes_saved=24.0,
        savings_percent=80.0,
        successful_step_count=3,
        total_evidence_rows=3,
        created_at="2026-07-16T09:20:00+00:00",
    )
    actions = [
        SafeResponseAction(
            action_id="action-1",
            action_type="REVOKE_SESSIONS",
            title="Review session revocation",
            target_type="identity",
            target="alex.morgan",
            risk_level="high",
            rationale="Corroborated replay evidence justifies a human-reviewed containment option.",
            prerequisites=["Confirm identity owner", "Capture session evidence", "Obtain analyst approval"],
            expected_effect="Invalidate active sessions associated with the synthetic identity.",
            rollback_plan="Restore access through the documented identity recovery process.",
            verification_steps=["Confirm sessions are invalid", "Monitor for renewed authentication"],
        ),
        SafeResponseAction(
            action_id="action-2",
            action_type="COLLECT_FORENSICS",
            title="Preserve identity audit evidence",
            target_type="incident",
            target="judge-demo-oauth-replay",
            risk_level="low",
            rationale="Evidence preservation supports review without changing external systems.",
            prerequisites=["Confirm retention policy"],
            expected_effect="Preserve the relevant audit window for investigation.",
            rollback_plan="Remove the temporary hold after case closure according to policy.",
            verification_steps=["Confirm evidence package integrity"],
        ),
    ]
    preview = SafeResponsePreview(
        preview_id=PREVIEW_ID,
        runbook_id=RUNBOOK_ID,
        source_record_id=source_record_id,
        source_verdict="TRUE_POSITIVE",
        evidence_basis="SOURCE_EVIDENCE",
        actions=actions,
        decision_summary=(
            "Present two evidence-backed options to the analyst. No command, API call, "
            "or automatic response is executed."
        ),
        limitations=["Preview only", "Human approval is mandatory"],
        configured_model="judge-demo/policy-guarded",
        model="judge-demo/policy-guarded",
        prompt_tokens=920,
        completion_tokens=384,
        generation_duration_ms=1700,
        execution_supported=False,
        created_at="2026-07-16T08:40:00+00:00",
    )
    decision = SafeResponseDecision(
        preview_id=PREVIEW_ID,
        runbook_id=RUNBOOK_ID,
        source_record_id=source_record_id,
        decision="approve_for_manual_action",
        analyst="demo.soc.lead",
        note="Approved for a separate manual response process; this product performed no execution.",
        automatic_execution_performed=False,
        created_at="2026-07-16T08:47:00+00:00",
    )
    trace_specs = [
        ("SUPERVISOR", "AGENT_STARTED", "RUNNING", "Started the bounded Runbook Autopilot tour.", None, {}),
        ("SUPERVISOR", "HANDOFF", "SUCCEEDED", "Assigned evidence collection to Evidence Scout.", None, {"to": "EVIDENCE_SCOUT"}),
        ("EVIDENCE_SCOUT", "TOOL_CALL", "RUNNING", "Requested read-only identity evidence through Splunk MCP.", "splunk.mcp.search", {"transport": "mcp"}),
        ("EVIDENCE_SCOUT", "TOOL_RESULT", "SUCCEEDED", "MCP and REST-fallback coverage returned parser-valid source evidence.", "splunk.rest.oneshot_fallback", {"mcp_steps": 2, "rest_fallback_steps": 1, "evidence_rows": 3}),
        ("EVIDENCE_SCOUT", "HANDOFF", "SUCCEEDED", "Passed bounded evidence to Runbook Engineer.", None, {"to": "RUNBOOK_ENGINEER"}),
        ("RUNBOOK_ENGINEER", "TOOL_RESULT", "SUCCEEDED", "Compiled three reusable investigation intents.", "runbook.compiler", {"runbook_status": "SOURCE_VERIFIED"}),
        ("RUNBOOK_ENGINEER", "HANDOFF", "SUCCEEDED", "Requested policy and exact-match evaluation.", None, {"to": "POLICY_GUARD"}),
        ("POLICY_GUARD", "POLICY_DECISION", "SUCCEEDED", "Confirmed exact Alert Name, different SID, source evidence, and human gate.", "runbook.policy.evaluate", {"exact_match": True, "different_sid": True, "automatic_execution": False}),
        ("POLICY_GUARD", "HANDOFF", "SUCCEEDED", "Requested a non-executable response preview.", None, {"to": "RESPONSE_ADVISOR"}),
        ("RESPONSE_ADVISOR", "TOOL_RESULT", "SUCCEEDED", "Prepared human-reviewed response options in PREVIEW_ONLY mode.", "runbook.safe_response.preview", {"preview_id": PREVIEW_ID, "execution_supported": False}),
        ("RESPONSE_ADVISOR", "HANDOFF", "SUCCEEDED", "Returned the preview and audit trail to Supervisor.", None, {"to": "SUPERVISOR"}),
        ("SUPERVISOR", "AGENT_COMPLETED", "SUCCEEDED", "Completed the tour after recorded human approval; no response was auto-executed.", None, {"runbook_id": RUNBOOK_ID}),
    ]
    trace = [
        RunbookAutopilotEvent(
            event_id=f"demo-autopilot-event-{index}",
            sequence=index,
            agent=agent,
            kind=kind,
            status=status,
            summary=summary,
            tool_name=tool,
            duration_ms=80 + index * 35,
            metadata=metadata,
            created_at=f"2026-07-16T08:{36 + min(index, 9):02d}:00+00:00",
        )
        for index, (agent, kind, status, summary, tool, metadata) in enumerate(trace_specs, 1)
    ]
    autopilot = RunbookAutopilotSession(
        session_id=AUTOPILOT_SESSION_ID,
        source_record_id=source_record_id,
        objective="Advance a source-verified runbook through policy, shadow evidence, and safe response review.",
        mode="ADVANCE",
        status="COMPLETED",
        agents=["SUPERVISOR", "EVIDENCE_SCOUT", "RUNBOOK_ENGINEER", "POLICY_GUARD", "RESPONSE_ADVISOR"],
        tools_used=[
            "splunk.mcp.search",
            "splunk.rest.oneshot_fallback",
            "runbook.compiler",
            "runbook.policy.evaluate",
            "runbook.safe_response.preview",
        ],
        trace=trace,
        runbook_id=RUNBOOK_ID,
        runbook_status="SOURCE_VERIFIED",
        response_preview_id=PREVIEW_ID,
        next_recommended_action="Review the approved runbook reuse on the second exact-match alert.",
        human_approval_required=True,
        automatic_execution_performed=False,
        started_at="2026-07-16T08:36:00+00:00",
        completed_at="2026-07-16T08:47:30+00:00",
        duration_ms=690000,
    )

    def event(record_type: str, model: Any, *, sid: str = SOURCE_SID) -> Dict[str, Any]:
        return {
            "tsoc_record_type": record_type,
            "sid": sid,
            "search_name": SEARCH_NAME,
            "row_index": 0,
            "demo_scenario_id": SCENARIO_ID,
            **model.model_dump(mode="json"),
        }

    return [
        event("verified_runbook_draft", draft),
        event("verified_runbook_shadow_run", shadow, sid=TARGET_SID),
        event("verified_runbook_response_preview", preview),
        event("verified_runbook_approval", approval),
        event("verified_runbook_response_decision", decision),
        event("verified_runbook_run", run, sid=TARGET_SID),
        event("verified_runbook_autopilot_session", autopilot),
    ]


def _analyst_action(source_record_id: int) -> Dict[str, Any]:
    return {
        "tsoc_record_type": "investigation_analyst_action",
        "sid": SOURCE_SID,
        "search_name": SEARCH_NAME,
        "row_index": 0,
        "demo_scenario_id": SCENARIO_ID,
        "investigation_record_id": source_record_id,
        "action": "acknowledge",
        "note": "Judge tour: acknowledged after reviewing the synthetic evidence chain.",
        "analyst": "demo.soc.lead",
        "recommended_step_at_action": "Open ThinkingSOC Lite and review the Autopilot trace.",
        "recorded_at": "2026-07-16T08:35:00+00:00",
    }


async def _record_id(conn: Any, sid: str) -> int | None:
    value = await conn.fetchval(
        """
        SELECT id FROM tsoc_records
        WHERE tsoc_record_type = 'soc_analysis' AND sid = $1
        ORDER BY id ASC LIMIT 1
        """,
        sid,
    )
    return int(value) if value is not None else None


async def _insert_record(conn: Any, event: Dict[str, Any]) -> int:
    return int(
        await conn.fetchval(
            """
            INSERT INTO tsoc_records
                (tsoc_record_type, sid, search_name, row_index, payload)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            RETURNING id
            """,
            event["tsoc_record_type"],
            event.get("sid"),
            event.get("search_name"),
            event.get("row_index"),
            pg.jsonb_param(event),
        )
    )


async def _insert_artifacts_once(conn: Any, events: Iterable[Dict[str, Any]]) -> int:
    inserted = 0
    for event in events:
        exists = await conn.fetchval(
            """
            SELECT 1 FROM tsoc_records
            WHERE tsoc_record_type = $1
              AND payload->>'demo_scenario_id' = $2
            LIMIT 1
            """,
            event["tsoc_record_type"],
            SCENARIO_ID,
        )
        if exists:
            continue
        await _insert_record(conn, event)
        inserted += 1
    return inserted


async def _seed_chat(settings: Settings) -> int:
    await ensure_chat_schema(settings)
    if pg._PG_POOL is None:
        raise RuntimeError("PostgreSQL store is not initialized")
    async with pg._PG_POOL.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO tsoc_chat_conversations (conversation_id, title, created_at, updated_at)
                VALUES ($1, $2, $3, $3)
                ON CONFLICT (conversation_id) DO NOTHING
                """,
                CHAT_CONVERSATION_ID,
                "Judge tour — Runbook Autopilot",
                datetime(2026, 7, 16, 9, 25, tzinfo=timezone.utc),
            )
            count = int(
                await conn.fetchval(
                    "SELECT COUNT(*) FROM tsoc_chat_messages WHERE conversation_id = $1",
                    CHAT_CONVERSATION_ID,
                )
                or 0
            )
            if count:
                return 0
            messages = [
                (
                    "user",
                    "Show me the complete evidence and agent flow for the OAuth token replay runbook.",
                    1,
                    {"demo_scenario_id": SCENARIO_ID},
                ),
                (
                    "assistant",
                    (
                        "### Judge tour ready\n\n"
                        f"Open **Runbook Library** and select **{SEARCH_NAME}**. The stored scenario shows "
                        "three parser-valid evidence steps, a different-SID shadow replay, human approval, "
                        "safe response preview, and a five-agent Autopilot audit trace.\n\n"
                        "Safety invariant: **human approval is required and automatic execution is false**. "
                        "You can ask follow-up questions in Chat because every ThinkingSOC Lite artifact is indexed in RAG."
                    ),
                    2,
                    {
                        "demo_scenario_id": SCENARIO_ID,
                        "runbook_id": RUNBOOK_ID,
                        "search_name": SEARCH_NAME,
                    },
                ),
            ]
            for role, content, seq, metadata in messages:
                await conn.execute(
                    """
                    INSERT INTO tsoc_chat_messages
                        (conversation_id, role, content, seq, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                    """,
                    CHAT_CONVERSATION_ID,
                    role,
                    content,
                    seq,
                    pg.jsonb_param(metadata),
                    datetime(2026, 7, 16, 9, 25 + seq, tzinfo=timezone.utc),
                )
            return len(messages)


async def seed_runbook_judge_demo(
    settings: Settings,
    *,
    backfill_rag: bool = True,
) -> Dict[str, Any]:
    """Add the complete judge-tour scenario and return a compact verification report."""
    pool = await pg.ensure_pool(settings)
    inserted_records = 0
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(hashtext($1))", SCENARIO_ID)
            source_id = await _record_id(conn, SOURCE_SID)
            if source_id is None:
                source_id = await _insert_record(
                    conn, _analysis_event(sid=SOURCE_SID, observed_at=_SOURCE_AT, target=False)
                )
                inserted_records += 1
            target_id = await _record_id(conn, TARGET_SID)
            if target_id is None:
                target_id = await _insert_record(
                    conn, _analysis_event(sid=TARGET_SID, observed_at=_TARGET_AT, target=True)
                )
                inserted_records += 1
            events = [_analyst_action(source_id), *build_artifact_events(source_id, target_id)]
            inserted_records += await _insert_artifacts_once(conn, events)

    inserted_messages = await _seed_chat(settings)
    rag_counts: Dict[str, int] = {}
    if backfill_rag:
        rag_counts = await backfill_from_storage(
            settings,
            limit_per_type=1000,
            include_inventory=True,
        )

    return {
        "scenario_id": SCENARIO_ID,
        "search_name": SEARCH_NAME,
        "source_record_id": source_id,
        "target_record_id": target_id,
        "source_sid": SOURCE_SID,
        "target_sid": TARGET_SID,
        "runbook_id": RUNBOOK_ID,
        "inserted_records": inserted_records,
        "inserted_chat_messages": inserted_messages,
        "rag_counts": rag_counts,
        "invariants": {
            "same_alert_name": True,
            "different_sid": SOURCE_SID != TARGET_SID,
            "source_verified": True,
            "human_approval_required": True,
            "automatic_execution_performed": False,
        },
    }
