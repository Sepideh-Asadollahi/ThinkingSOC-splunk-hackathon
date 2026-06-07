from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Optional

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve `backend/.env` regardless of current working directory (same idea as ThinkingSOC services).
_BACKEND_ROOT = Path(__file__).resolve().parent


def _empty_env_to_none(value: object) -> object:
    """Treat blank .env values as unset (pydantic otherwise fails Optional[float])."""
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


OptionalFloatEnv = Annotated[Optional[float], BeforeValidator(_empty_env_to_none)]


class Settings(BaseSettings):
    """Runtime configuration via environment / `backend/.env` (never commit secrets)."""

    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    splunk_mgmt_url: str = "https://127.0.0.1:8089"
    splunk_username: str = ""
    splunk_password: str = ""
    splunk_verify_ssl: bool = False

    # PostgreSQL storage for TSOC records (analysis, route outputs, ingest summaries, audits).
    tsoc_postgres_dsn: Optional[str] = None
    # Ingest: optional background triage after webhook enrich.
    tsoc_ingest_auto_analyze: bool = True
    tsoc_ingest_auto_analyze_pipeline: Literal["triage", "route", "none"] = "triage"
    tsoc_ingest_auto_analyze_max_rows: int = Field(default=50, ge=1, le=500)
    # Log complete Splunk webhook JSON to console (ingest_webhook_raw_json / _raw_pretty).
    tsoc_ingest_log_raw_webhook_body: bool = True

    # Alert router: LLM-only classification (manual_review fallback when LLM unavailable).
    tsoc_classifier_llm: bool = True

    tsoc_ingest_token: Optional[str] = None
    tsoc_admin_token: Optional[str] = None
    tsoc_alert_log_path: Optional[str] = None
    # Optional: append each SOC analysis JSON line (LLD §4.5)
    tsoc_analysis_log_path: Optional[str] = None

    # LiteLLM — see docs/04-agents-and-pipelines.md
    # Model id as understood by LiteLLM (e.g. gpt-4o-mini, anthropic/claude-3-5-haiku-20241022).
    litellm_model: str = "gpt-4o-mini"
    litellm_api_key: Optional[str] = None
    litellm_api_base: Optional[str] = None
    litellm_timeout_seconds: float = 120.0
    # Upper cap for completion tokens (128k). Individual call sites may request less.
    litellm_max_tokens: int = Field(default=131072, ge=256, le=131072)
    # Effective model context window (tokens) — sizes prompt truncation budgets.
    tsoc_llm_context_tokens: int = Field(default=131072, ge=8192, le=131072)
    litellm_analysis_max_tokens: int = Field(default=8192, ge=256, le=131072)
    # Defender / Hunter / Judge / admin-org gap structured calls
    litellm_analysis_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    # When set, POST /llm/chat uses this if the JSON body omits ``temperature``
    litellm_chat_default_temperature: OptionalFloatEnv = Field(default=None, ge=0.0, le=2.0)

    # Splunk app namespace for REST oneshot (servicesNS).
    # Splunk's built-in Search & Reporting app short name is "search".
    tsoc_splunk_app: str = "search"
    tsoc_splunk_owner: str = "nobody"
    # App namespace for SPL syntax validation (POST search/v2/parser); use ``search``, not CIM app.
    tsoc_spl_parser_app: str = "search"

    # CIM datamodel-aware investigation SPL (datamodelsimple + tstats).
    tsoc_cim_datamodel: str = "Authentication"
    tsoc_cim_spl_app: str = "Splunk_SA_CIM"
    # Inject CIM catalog + field lineage into SAIA/LLM SPL prompts (default off — SAIA infers).
    tsoc_cim_spl_schema_context: bool = False
    # When schema context is on: fetch ``| datamodelsimple type=models`` for datamodel selection.
    tsoc_cim_fetch_all_models: bool = True
    # When schema context is on: LiteLLM picks datamodel per question from the catalog.
    tsoc_cim_llm_select_datamodel: bool = True
    tsoc_execute_investigation_spl: bool = True
    # Default Splunk job time range for investigation search execute.
    tsoc_investigation_spl_time_window: str = "earliest=1 latest=now"
    # Max CIM objects to fetch attributes for via datamodelsimple nodename= (per datamodel).
    tsoc_cim_schema_max_objects: int = Field(default=15, ge=1, le=40)
    # When schema context is on: all objects/field paths for the selected datamodel in prompts.
    tsoc_cim_schema_full_fields: bool = True
    # Max chars of CIM schema text sent to SAIA/LLM per question (capped by 128k budget).
    tsoc_cim_schema_prompt_max_chars: int = Field(default=98304, ge=4096, le=458752)
    # Max chars of alert JSON in per-question SPL prompts.
    tsoc_spl_alert_context_max_chars: int = Field(default=32768, ge=1024, le=131072)
    # Max chars for SAIA ``prompt`` (Splunk MCP 1.1.2 hard limit is 1000).
    tsoc_saia_mcp_prompt_max_chars: int = Field(default=1000, ge=100, le=1000)
    # Before saia_generate_spl: LiteLLM writes the ≤1000-char prompt; then post-SAIA LLM review.
    tsoc_saia_llm_prepare_prompt: bool = True
    # Per-question SPL LLM: slim alert context only (no full Defender/Hunter/Judge JSON).
    tsoc_spl_compact_context: bool = True

    # VirusTotal (API v3) — enrich IOCs (hash/ip/domain/url) into System Context for LLM
    virustotal_api_key: Optional[str] = None
    virustotal_base_url: str = "https://www.virustotal.com/api/v3"
    virustotal_timeout_seconds: float = 15.0
    virustotal_enable: bool = True
    # Cap IOCs queried per analysis to control latency/quota/prompt size.
    virustotal_max_iocs: int = Field(default=8, ge=0, le=50)

    # Splunk MCP Server (Splunkbase app 7931) — see docs/02-integration-boundaries.md
    tsoc_mcp_enabled: bool = True
    splunk_mcp_url: Optional[str] = None
    splunk_mcp_token: Optional[str] = None
    splunk_mcp_verify_ssl: bool = False
    splunk_mcp_timeout_seconds: float = 90.0
    tsoc_mcp_correlation_enabled: bool = False
    # Hunter/Judge LangGraph stages: live MCP hunt queries + SAIA ask before LLM reasoning.
    tsoc_mcp_hunter_judge_enabled: bool = True
    # saia_generate_spl: false = full SAIA reply (reasoning + SPL, closer to Splunk UI write_spl chat).
    tsoc_mcp_saia_spl_only: bool = False
    # After saia_generate_spl: run saia_optimize_spl then saia_explain_spl (Splunk AI Assistant).
    tsoc_mcp_saia_optimize_spl: bool = True
    tsoc_mcp_saia_explain_spl: bool = True
    # After investigation SPL is drafted: run SAIA optimize + explain via MCP (Analysis UI).
    tsoc_analysis_saia_spl_review: bool = True
    # Full MCP JSON-RPC trace (no truncation). Logger: tsoc.trace.mcp
    tsoc_mcp_trace_log: bool = False
    # Full SAIA tool request/response trace (no truncation). Logger: tsoc.trace.saia
    tsoc_saia_trace_log: bool = False
    # Optional path for MCP+SAIA trace lines (same file, both loggers).
    tsoc_trace_log_file: Optional[str] = None
    # Generate SPL via Splunk AI Assistant REST ``/predict`` (UI-like path).
    tsoc_spl_use_rest_predict: bool = True
    # Auto-repair SAIA cloud_connected_configurations when /predict fails or on startup.
    tsoc_saia_auto_repair: bool = True
    # Splunk install path (for ``splunk cmd python3`` token refresh worker).
    splunk_home: str = "/opt/splunk"
    # Poll wait budget for ``/predict`` async response.
    tsoc_spl_predict_timeout_seconds: float = Field(default=90.0, ge=5.0, le=300.0)
    tsoc_spl_predict_poll_interval_seconds: float = Field(default=0.75, ge=0.2, le=5.0)
    # Prefer MCP ``splunk_run_query`` for execution; fallback to REST oneshot on failures.
    tsoc_spl_execute_via_mcp: bool = True
    # After MCP SAIA pipeline, run analysis LLM to fix parser/safety/context issues.
    tsoc_spl_llm_review: bool = True
    # On Splunk parser/execute errors: pass error text to LiteLLM and re-validate/re-execute.
    tsoc_spl_llm_refine_on_error: bool = True
    # After execute: refine SPL on error or 0 rows (LiteLLM + optional MCP optimize), max attempts per question.
    tsoc_spl_execute_refine_max_attempts: int = Field(default=2, ge=0, le=2)
    # Investigation follow-up questions per alert (LLM list + SPL per question).
    tsoc_investigation_questions_max: int = Field(default=3, ge=1, le=12)

    # SOC vector RAG — PostgreSQL + Qdrant (docs/10-soc-vector-rag.md)
    tsoc_rag_similar_max: int = Field(default=3, ge=1, le=5)
    tsoc_rag_similar_min_score: float = Field(default=0.35, ge=0.0, le=1.0)
    tsoc_rag_similar_lookback_days: int = Field(default=30, ge=1, le=365)
    tsoc_rag_similar_token_budget: int = Field(default=1500, ge=200, le=8000)
    tsoc_rag_chat_top_k: int = Field(default=12, ge=1, le=30)
    tsoc_rag_backfill_on_startup: bool = True
    # Long chat sessions: direct history below this count; above uses session RAG
    tsoc_chat_history_direct_max: int = Field(default=12, ge=4, le=100)
    tsoc_chat_history_rag_top_k: int = Field(default=8, ge=2, le=30)
    tsoc_chat_history_recent_tail: int = Field(default=4, ge=2, le=20)

    # SOC chat Text-to-SQL for statistical questions (docs/10-soc-vector-rag.md)
    tsoc_chat_sql_enable: bool = True
    tsoc_chat_sql_max_rows: int = Field(default=500, ge=1, le=5000)
    tsoc_chat_sql_timeout_seconds: float = Field(default=5.0, ge=1.0, le=60.0)
    # Max completion tokens for SQL-generation LLM calls (thinking models need headroom).
    tsoc_chat_sql_max_tokens: int = Field(default=131072, ge=256, le=131072)
    # Classify statistical vs narrative (was 256; 10× for thinking models).
    tsoc_chat_sql_classify_max_tokens: int = Field(default=2560, ge=256, le=131072)
    # Answer LLM only for large result sets; keep modest (huge values slow NIM).
    tsoc_chat_sql_answer_max_tokens: int = Field(default=2048, ge=256, le=131072)
    # Override model used for Text-to-SQL generation. Useful when the main model is a
    # reasoning/thinking variant that exhausts tokens before emitting JSON — point this
    # at a non-thinking instruct model (e.g. nvidia_nim/qwen/qwen3-next-80b-a3b-instruct).
    tsoc_chat_sql_model: Optional[str] = None

    # API rate limiting (simple in-process guard for demo hardening).
    tsoc_rate_limit_enabled: bool = True
    tsoc_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    tsoc_rate_limit_max_requests: int = Field(default=60, ge=1, le=10000)

    # Vector search — Qdrant (https://github.com/qdrant/qdrant) + FastEmbed locally
    tsoc_vector_enable: bool = True
    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_collection: str = "tsoc_soc_rag"
    # FastEmbed model: full id (BAAI/bge-*-en-v1.5) or preset (bge-small | bge-base | medium | bge-large)
    tsoc_embedding_model: str = "BAAI/bge-base-en-v1.5"
    # Informational default; runtime dim is derived from the model (see embeddings.effective_embedding_dim)
    tsoc_embedding_dim: int = Field(default=768, ge=64, le=4096)
    # FastEmbed ONNX cache (absolute path under /opt — not repo, /tmp, or ~/.cache)
    tsoc_fastembed_cache_dir: str = "/opt/.thinking-soc-cache/fastembed"

    # Neo4j graph correlation (Correlation demo — /api/v1/graph)
    neo4j_uri: str = "bolt://127.0.0.1:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "tsoc-tsoc"
    correlation_demo_api_key: str = "dev-key"
    correlation_bearer_token: Optional[str] = None
    tsoc_correlation_enabled: bool = True
    tsoc_correlation_auto_seed: bool = True
    smart_analysis_lookback_days: int = Field(default=7, ge=1, le=90)
    # Attack Discovery: entity co-occurrence window (hours) for clustering + campaign enrichment
    correlation_cluster_window_hours: int = Field(default=168, ge=24, le=720)
    # Optional comma-separated ``type`` prefixes (without colon) for entity taxonomy overrides
    correlation_anchor_entity_prefixes: Optional[str] = None
    correlation_indicator_entity_prefixes: Optional[str] = None


def mcp_configured(settings: Settings) -> bool:
    """True when MCP integration is enabled and minimally configured."""
    if not settings.tsoc_mcp_enabled:
        return False
    token = (settings.splunk_mcp_token or "").strip()
    if not token:
        return False
    return bool(splunk_mcp_url_for(settings))


def splunk_mcp_url_for(settings: Settings) -> str:
    """Resolved MCP endpoint URL."""
    explicit = (settings.splunk_mcp_url or "").strip()
    if explicit:
        return explicit.rstrip("/")
    base = settings.splunk_mgmt_url.rstrip("/")
    return "{0}/services/mcp".format(base)


def clear_settings_cache() -> None:
    get_settings.cache_clear()


@lru_cache
def get_settings() -> Settings:
    base = Settings()
    try:
        from services.platform.integration_settings import load_setting_overrides

        overrides = load_setting_overrides()
    except Exception:
        overrides = {}
    if not overrides:
        return base
    valid = {k: v for k, v in overrides.items() if k in Settings.model_fields}
    if not valid:
        return base
    return base.model_copy(update=valid)


def investigation_questions_max(settings: Settings) -> int:
    """Hard cap for investigation questions (default 3)."""
    return max(1, min(12, int(getattr(settings, "tsoc_investigation_questions_max", 3) or 3)))
