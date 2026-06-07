"""Find similar past alerts for SOC analysis context."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from config import Settings
from services.splunk_json_store import splunk_store_configured

from .compact_alert import compact_alert_document
from .models import SimilarAlertContext, SimilarAlertItem
from .retrieve import retrieve_rag_documents

logger = logging.getLogger(__name__)


def _truncate_similar_block(items: List[SimilarAlertItem], token_budget: int) -> List[SimilarAlertItem]:
    if token_budget <= 0:
        return items
    out: List[SimilarAlertItem] = []
    used = 0
    for it in items:
        blob = json.dumps(it.model_dump(mode="json"), ensure_ascii=False)
        est = max(1, len(blob) // 4)
        if used + est > token_budget and out:
            break
        out.append(it)
        used += est
    return out


def format_similar_for_canonical(ctx: SimilarAlertContext) -> str:
    if not ctx.similar_alerts:
        return ""
    lines = ["## Similar past alerts (essential fields only; not full Splunk rows)"]
    for i, a in enumerate(ctx.similar_alerts, 1):
        lines.append(
            "{0}. [{1}] {2} score={3} verdict={4} essential={5}".format(
                i,
                a.doc_type,
                a.search_name or a.sid or "?",
                a.similarity_score,
                a.prior_verdict or "-",
                json.dumps(a.essential, ensure_ascii=False),
            )
        )
    return "\n".join(lines)


async def find_similar_alerts(
    settings: Settings,
    *,
    sid: Optional[str],
    search_name: Optional[str],
    normalized: Dict[str, Any],
    splunk_results: Optional[List[Dict[str, Any]]] = None,
    row_index: int = 0,
) -> SimilarAlertContext:
    if not splunk_store_configured(settings):
        return SimilarAlertContext(
            similar_alerts=[],
            retrieval_meta={"enabled": False, "reason": "soc_rag_disabled"},
        )

    query_doc = compact_alert_document(
        sid=sid,
        search_name=search_name,
        normalized=normalized,
        splunk_results=splunk_results,
        row_index=row_index,
    )
    top_k = settings.tsoc_rag_similar_max + 2
    min_score = settings.tsoc_rag_similar_min_score
    lookback = settings.tsoc_rag_similar_lookback_days

    hits, backend = await retrieve_rag_documents(
        settings,
        question=query_doc.chunk_text,
        top_k=top_k,
        exclude_doc_id=query_doc.doc_id,
        exclude_sid=sid,
        exclude_row_index=row_index,
        lookback_days=lookback,
    )

    items: List[SimilarAlertItem] = []
    for doc, score in hits:
        if score < min_score:
            continue
        meta = doc.metadata or {}
        items.append(
            SimilarAlertItem(
                sid=doc.sid,
                search_name=doc.search_name,
                _time=str(doc.essential.get("_time") or ""),
                essential={k: str(v) for k, v in doc.essential.items()},
                prior_verdict=str(meta.get("verdict") or doc.essential.get("verdict") or "") or None,
                similarity_score=round(score, 4),
                doc_type=doc.doc_type,
            )
        )

    items = items[: settings.tsoc_rag_similar_max]
    items = _truncate_similar_block(items, settings.tsoc_rag_similar_token_budget)

    return SimilarAlertContext(
        similar_alerts=items,
        retrieval_meta={
            "enabled": True,
            "count": len(items),
            "backend": backend,
            "truncated": len(items) >= settings.tsoc_rag_similar_max,
        },
    )
