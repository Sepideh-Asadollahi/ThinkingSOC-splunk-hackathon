"""Tests for Qdrant RAG helpers (no running Qdrant required)."""

from config import Settings

from services.soc_rag.qdrant_store import _normalize_qdrant_url, _point_id, qdrant_enabled


def test_qdrant_point_id_stable() -> None:
    a = _point_id("sid-1::splunk_alert::0")
    b = _point_id("sid-1::splunk_alert::0")
    c = _point_id("sid-2::splunk_alert::0")
    assert a == b
    assert a != c


def test_normalize_qdrant_url_adds_http_scheme() -> None:
    assert _normalize_qdrant_url("127.0.0.1:6333") == "http://127.0.0.1:6333"
    assert _normalize_qdrant_url("http://127.0.0.1:6333/") == "http://127.0.0.1:6333"


def test_qdrant_enabled_defaults() -> None:
    s = Settings(tsoc_vector_enable=True, qdrant_url="http://127.0.0.1:6333")
    assert qdrant_enabled(s) is True
    s2 = Settings(tsoc_vector_enable=False)
    assert qdrant_enabled(s2) is False


def test_default_embedding_model_is_base_bge() -> None:
    s = Settings()
    assert s.tsoc_embedding_model == "BAAI/bge-base-en-v1.5"
    assert s.tsoc_embedding_dim == 768


def test_embedding_dim_for_bge_large() -> None:
    from services.soc_rag.embeddings import embedding_dim_for_model

    assert embedding_dim_for_model("BAAI/bge-large-en-v1.5") == 1024


def test_embedding_model_presets() -> None:
    from services.soc_rag.embeddings import (
        EMBEDDING_MODEL_CATALOG,
        effective_embedding_dim,
        list_embedding_model_options,
        resolve_embedding_model,
    )

    assert resolve_embedding_model("bge-small") == "BAAI/bge-small-en-v1.5"
    assert resolve_embedding_model("small") == "BAAI/bge-small-en-v1.5"
    assert resolve_embedding_model("BGE-LARGE") == "BAAI/bge-large-en-v1.5"
    assert resolve_embedding_model("medium") == "BAAI/bge-base-en-v1.5"
    assert resolve_embedding_model("BAAI/bge-base-en-v1.5") == "BAAI/bge-base-en-v1.5"

    options = list_embedding_model_options()
    assert len(options) == len(EMBEDDING_MODEL_CATALOG)
    assert {o["preset"] for o in options} == set(EMBEDDING_MODEL_CATALOG)

    assert effective_embedding_dim(Settings(tsoc_embedding_model="bge-small")) == 384
    assert effective_embedding_dim(Settings(tsoc_embedding_model="bge-base")) == 768
    assert effective_embedding_dim(Settings(tsoc_embedding_model="bge-large")) == 1024
