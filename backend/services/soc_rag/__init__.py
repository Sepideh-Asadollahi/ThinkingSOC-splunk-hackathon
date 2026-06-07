"""SOC vector RAG — PostgreSQL + Qdrant knowledge layer."""

from .chat import run_soc_chat
from .index_writer import schedule_alert_index, upsert_alert_document, upsert_analysis_document
from .similar import find_similar_alerts, format_similar_for_canonical

__all__ = [
    "find_similar_alerts",
    "format_similar_for_canonical",
    "run_soc_chat",
    "schedule_alert_index",
    "upsert_alert_document",
    "upsert_analysis_document",
]
