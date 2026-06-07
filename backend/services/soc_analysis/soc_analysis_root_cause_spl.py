"""
Root-Cause SPL generator — final stage of the SOC analysis LangGraph.

Generates a single SPL string that a SOC analyst can run to drive an alert toward root cause.
The backend **does not execute** this SPL; it only validates syntax via Splunk parser when configured.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from config import Settings
from models.analysis import RootCauseSpl, RootCauseSplValidation
from splunk.client import SplunkRestClient

logger = logging.getLogger(__name__)


_FORBIDDEN_SPL_COMMANDS = (
    "delete",
    "outputlookup",
    "outputcsv",
    "outputtelemetry",
    "sendalert",
    "sendemail",
    "script",
    "external",
    "run",
    "summaryindex",
    "collect",
    "mcollect",
    "meta",
)

_COMPLEX_SPL_COMMANDS = (
    "join",
    "append",
    "appendcols",
    "transaction",
    "map",
    "multisearch",
    "union",
    "selfjoin",
    "subsearch",
)
_NON_RAW_OUTPUT_COMMANDS = (
    "stats",
    "table",
    "chart",
    "timechart",
    "top",
    "rare",
)


def investigation_question_spl_user_message(
    *,
    question: str,
    normalized: Dict[str, Any],
    search_name: str = "",
    alert_max_chars: int = 32768,
) -> str:
    """Slim per-question SPL prompt — one question, alert fields only."""
    alert_blob = json.dumps(normalized, ensure_ascii=False, default=str)[:alert_max_chars]
    from services.investigation.investigation_question_context import (
        format_alert_fields_block,
        merge_alert_field_sample,
        primary_alert_fields,
    )

    norm = normalized or {}
    sample = merge_alert_field_sample(norm)
    fields = primary_alert_fields(sample, search_name=search_name)
    fields_block = format_alert_fields_block(fields, search_name=search_name)
    return (
        "Produce **simple** SPL for **one** investigation question using **`search`** "
        "(and simple pipes like `stats`, `table`, `where`). "
        "Final output must be **statistical** (`stats`/`chart`/`timechart`/`top`) or a `table` view; do not return raw events. "
        "Do **not** use `tstats`, `datamodel`, or CIM acceleration. "
        "Do **not** include `earliest=` or `latest=` in the SPL (time is applied at execution). "
        "Filter using alert search field values below — do not invent hosts/users. "
        "Avoid complex pipes: join, append, transaction, map, multisearch, union. "
        "Return only the JSON object (single item in investigation_questions array).\n\n"
        "## Investigation question\n"
        + (question or "").strip()
        + "\n\n## Alert search fields\n"
        + fields_block
        + "\n\n## Alert (full JSON)\n"
        + ("search_name: {0}\n".format(search_name) if search_name else "")
        + alert_blob
    )


def root_cause_spl_user_message(
    canonical_prefix: str,
    defender_output: Dict[str, Any],
    hunter_output: Dict[str, Any],
    judge_output: Dict[str, Any],
    investigation_questions: Optional[List[str]] = None,
) -> str:
    """Build the user message for the per-question SPL LLM node."""
    d = json.dumps(defender_output, sort_keys=True, ensure_ascii=False, default=str)
    h = json.dumps(hunter_output, sort_keys=True, ensure_ascii=False, default=str)
    j = json.dumps(judge_output, sort_keys=True, ensure_ascii=False, default=str)
    qs = json.dumps(investigation_questions or [], ensure_ascii=False)
    return (
        "For each investigation question below, produce one tailored SPL using **`search`** only "
        "(no tstats, no datamodel). Return only the JSON object.\n\n"
        "Refer to the **System Context** as the ground truth.\n\n"
        "## System Context\n"
        + canonical_prefix
        + "\n\n## Defender output\n"
        + d
        + "\n\n## Hunter output\n"
        + h
        + "\n\n## Judge output\n"
        + j
        + "\n\n## Investigation questions (answer each with its own SPL, same order)\n"
        + qs
    )


def _spl_pipe_commands(spl: str) -> List[str]:
    return [m.lower() for m in re.findall(r"\|\s*([A-Za-z_][A-Za-z0-9_]*)", spl or "")]


def _has_forbidden_command(spl: str) -> Optional[str]:
    for tok in _spl_pipe_commands(spl):
        if tok in _FORBIDDEN_SPL_COMMANDS:
            return tok
    return None


def _has_complex_command(spl: str) -> Optional[str]:
    for tok in _spl_pipe_commands(spl):
        if tok in _COMPLEX_SPL_COMMANDS:
            return tok
    return None


def _reject_tstats_datamodel(spl: str) -> Optional[str]:
    lower = (spl or "").lower()
    if "tstats" in lower or "datamodel" in lower:
        return "tstats/datamodel not allowed — use search only"
    return None


def _has_non_raw_output(spl: str) -> bool:
    toks = set(_spl_pipe_commands(spl or ""))
    return any(cmd in toks for cmd in _NON_RAW_OUTPUT_COMMANDS)


def _enforce_non_raw_output(spl: str) -> tuple[str, bool]:
    """Ensure SPL output is aggregate/table (not raw events)."""
    if _has_non_raw_output(spl):
        return spl, False
    return (
        spl
        + " | table _time host source sourcetype EventCode Image ParentImage CommandLine ParentCommandLine User user",
        True,
    )


def sanitize_root_cause_spl_output(raw: Any) -> Optional[RootCauseSpl]:
    if not isinstance(raw, dict):
        return None

    spl = str(raw.get("spl") or "").strip()
    if not spl:
        return None

    from services.investigation.spl_tstats_sanitize import sanitize_spl_draft

    spl = sanitize_spl_draft(spl)

    if forbidden := _has_forbidden_command(spl):
        return RootCauseSpl(
            spl="",
            explanation="LLM emitted a forbidden command ({0}); SPL discarded.".format(forbidden),
            notes=["forbidden_command:{0}".format(forbidden)],
            validation=RootCauseSplValidation(
                method="skipped", valid=False, message="forbidden command not allowed in demo"
            ),
        )

    if bad := _reject_tstats_datamodel(spl):
        return RootCauseSpl(
            spl="",
            explanation=bad,
            notes=["search_only_policy"],
            validation=RootCauseSplValidation(method="skipped", valid=False, message=bad),
        )

    spl, non_raw_fixed = _enforce_non_raw_output(spl)

    pivots_raw = raw.get("pivots") or []
    notes_raw = raw.get("notes") or []
    pivots: List[str] = [str(x).strip() for x in pivots_raw if str(x).strip()] if isinstance(pivots_raw, list) else []
    notes: List[str] = [str(x).strip() for x in notes_raw if str(x).strip()] if isinstance(notes_raw, list) else []
    if non_raw_fixed and "auto_table_projection_for_non_raw_output" not in notes:
        notes.append("auto_table_projection_for_non_raw_output")
    if complex := _has_complex_command(spl):
        notes.append("complex_command_warning:{0}".format(complex))

    from services.investigation.spl_predict_pipeline import normalize_execution_time_window

    return RootCauseSpl(
        spl=spl,
        explanation=str(raw.get("explanation") or "").strip(),
        time_window=normalize_execution_time_window(raw.get("time_window")),
        pivots=pivots,
        notes=notes,
        validation=None,
    )


def _esc_spl_lit(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def _search_filters_from_normalized(normalized: Dict[str, Any]) -> List[str]:
    clauses: List[str] = []
    index = str(normalized.get("index") or "").strip()
    if index:
        clauses.append("index={0}".format(index))
    for key in ("host", "Computer", "user", "User", "src", "dest", "source", "sourcetype"):
        val = str(normalized.get(key) or "").strip()
        if not val:
            continue
        if " " in val or "*" in val or ":" in val:
            clauses.append('{0}={1}'.format(key, val))
        else:
            clauses.append('{0}="{1}"'.format(key, _esc_spl_lit(val)))
    return clauses


def build_zero_row_fallback_spl(
    question: str,
    normalized: Dict[str, Any],
    *,
    prior_spl: str = "",
) -> Optional[RootCauseSpl]:
    """
    Automatic ``search`` SPL when execute returned 0 rows and LLM refine failed or used tstats.

    Picks Sysmon-friendly patterns from the investigation question + alert fields.
    """
    from services.investigation.investigation_question_context import merge_alert_field_sample

    q_lower = (question or "").lower()
    sample = merge_alert_field_sample(normalized)
    index = str(sample.get("index") or "").strip() or "botsv1"
    host = str(sample.get("host") or sample.get("dest") or sample.get("Computer") or "").strip()
    source = str(sample.get("source") or "").strip()
    sourcetype = str(
        sample.get("sourcetype") or "XmlWinEventLog:Microsoft-Windows-Sysmon/Operational"
    ).strip()
    image = str(
        sample.get("Image")
        or sample.get("ProcessName")
        or sample.get("process")
        or sample.get("process_name")
        or ""
    ).strip()
    file_hint = ""
    if image:
        file_hint = image.replace("\\", "/").rsplit("/", 1)[-1]
    for token in ("invoke.ps1", "certutil.exe", "regsvr32.exe", "osk.exe", "lsass.exe"):
        if token.replace(".exe", "") in q_lower or token in q_lower:
            file_hint = file_hint or token

    parts = ["search index={0}".format(index)]
    if source:
        parts.append('source="{0}"'.format(_esc_spl_lit(source)))
    elif sourcetype:
        parts.append('sourcetype="{0}"'.format(_esc_spl_lit(sourcetype)))
    if host:
        parts.append(
            "host={0}".format(host) if ("*" in host or " " in host) else 'host="{0}"'.format(_esc_spl_lit(host))
        )
    base = " ".join(parts)

    spl: Optional[str] = None
    explanation = ""

    if any(x in q_lower for x in ("hash", "hashes", "sha256", "md5", "file hash")):
        needle = (file_hint or "invoke.ps1").replace("*", "")
        spl = (
            '{0} EventCode=11 (TargetFilename="*{1}*" OR Image="*{1}*") '
            "| stats dc(Hashes) as unique_hashes count as file_create_events "
            "| head 20 | table unique_hashes file_create_events"
        ).format(base, _esc_spl_lit(needle))
        explanation = "File-create events (EventCode=11) for hash lookup."
    elif any(x in q_lower for x in ("commandline", "command line", "cmdline")):
        needle = (file_hint or image or "*").replace("*", "")
        spl = (
            '{0} EventCode=1 Image="*{1}*" '
            "| stats dc(CommandLine) as unique_commandlines count as process_events "
            "| head 20 | table unique_commandlines process_events"
        ).format(base, _esc_spl_lit(needle))
        explanation = "Process creation (EventCode=1) for CommandLine."
    elif any(x in q_lower for x in ("parent", "parentimage", "parent process")):
        needle = (file_hint or image or "*").replace("*", "")
        spl = (
            '{0} EventCode=1 Image="*{1}*" '
            "| stats dc(ParentImage) as unique_parent_images count as process_events "
            "| head 20 | table unique_parent_images process_events"
        ).format(base, _esc_spl_lit(needle))
        explanation = "Process creation (EventCode=1) for ParentImage."
    elif any(
        x in q_lower
        for x in ("destinationip", "destination port", "network", "connection", "egress")
    ):
        needle = (file_hint or image or "osk.exe").replace("*", "")
        spl = (
            '{0} EventCode=3 Image="*{1}*" '
            "| stats count as connection_events dc(DestinationIp) as unique_dest_ips "
            "dc(DestinationPort) as unique_dest_ports by Image "
            "| sort - connection_events | head 20 "
            "| table Image connection_events unique_dest_ips unique_dest_ports"
        ).format(base, _esc_spl_lit(needle))
        explanation = "Network connections (EventCode=3) for egress analysis."

    if not spl and prior_spl and _reject_tstats_datamodel(prior_spl):
        return None
    if not spl:
        return None

    return RootCauseSpl(
        spl=spl,
        explanation=explanation,
        time_window="earliest=1 latest=now",
        pivots=["host", "Image", "Hashes", "CommandLine", "ParentImage"],
        notes=["auto_fallback_after_zero_rows"],
        validation=None,
    )


def build_rule_based_root_cause_spl(normalized: Dict[str, Any]) -> RootCauseSpl:
    """Deterministic ``search`` SPL when LLM is disabled or upstream fails."""
    orig = str(normalized.get("orig_search") or "").strip()
    if orig:
        if orig.lower().startswith("search") or orig.startswith("|"):
            spl = orig
        else:
            spl = "search " + orig
    else:
        clauses = _search_filters_from_normalized(normalized)
        spl = "search " + " ".join(clauses) if clauses else "search index=* | head 20"

    if _reject_tstats_datamodel(spl):
        clauses = _search_filters_from_normalized(normalized)
        spl = "search " + " ".join(clauses) if clauses else "search index=* | head 20"

    return RootCauseSpl(
        spl=spl,
        explanation="Rule-based search SPL from alert fields.",
        time_window="earliest=1 latest=now",
        pivots=[k for k in ("host", "user", "src", "dest") if normalized.get(k)],
        notes=["rule_based_search"],
        validation=None,
    )


async def validate_root_cause_spl(
    settings: Settings,
    rc: RootCauseSpl,
    *,
    app: Optional[str] = None,
    normalize_tstats: bool = True,
) -> RootCauseSplValidation:
    """Validate ``rc.spl`` via Splunk parser (parse_only). ``normalize_tstats`` is ignored (search-only policy)."""
    spl = (rc.spl or "").strip()
    if not spl:
        return RootCauseSplValidation(method="skipped", valid=False, message="empty SPL")

    if bad := _reject_tstats_datamodel(spl):
        return RootCauseSplValidation(method="skipped", valid=False, message=bad)

    if forbidden := _has_forbidden_command(spl):
        return RootCauseSplValidation(
            method="skipped", valid=False, message="forbidden command: {0}".format(forbidden)
        )

    if not settings.splunk_username or not settings.splunk_password:
        return RootCauseSplValidation(method="skipped", valid=True, message="Splunk credentials not configured")

    parse_app = app or settings.tsoc_spl_parser_app or settings.tsoc_splunk_app or "search"
    client = SplunkRestClient(settings)
    try:
        session_key = await client.login()
        await client.parse_spl(session_key, spl, app=parse_app)
        return RootCauseSplValidation(method="splunk_parser", valid=True, message="OK")
    except ValueError as e:
        return RootCauseSplValidation(method="splunk_parser", valid=False, message=str(e))
    except Exception as e:
        logger.warning("spl parser validation skipped: %s", e)
        return RootCauseSplValidation(method="skipped", valid=True, message=str(e))
