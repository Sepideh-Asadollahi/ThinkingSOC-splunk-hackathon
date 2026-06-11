# SOC RAG Service

SOC vector RAG (Retrieval-Augmented Generation) knowledge layer. Indexes alerts, analyses, inventory, and graph correlations into PostgreSQL and Qdrant. Provides semantic retrieval, similar-alert lookup, and an analyst chat interface with Text-to-SQL support.

## Key files

| File | Description |
|------|-------------|
| `chat.py` | SOC analyst chat over indexed alerts, analyses, and inventory |
| `chat_store.py` | PostgreSQL persistence for chat conversations and messages |
| `chat_history.py` | Session-scoped RAG for long SOC chat conversations |
| `embeddings.py` | Local embeddings via FastEmbed; `TSOC_EMBEDDING_MODEL` presets (`bge-small` / `bge-base` / `bge-large`) |
| `retrieve.py` | Unified retrieval: Qdrant semantic search with PostgreSQL fallback |
| `qdrant_store.py` | Qdrant vector index for semantic RAG |
| `pg_store.py` | PostgreSQL-backed RAG document store |
| `index_writer.py` | Indexes alerts and analyses into PostgreSQL + Qdrant |
| `similar.py` | Finds similar past alerts for SOC analysis context |
| `models.py` | Pydantic models for the RAG subsystem |
| `backfill.py` | Backfills RAG index from existing PostgreSQL records and inventory |
| `compact_alert.py` | Compact RAG documents from Splunk alerts (essential fields) |
| `compact_analysis.py` | Compact RAG documents from persisted SOC analyses |
| `compact_observability.py` | Compact observability analysis for chat retrieval |
| `compact_inventory.py` | Compact inventory rows for chat retrieval |
| `compact_correlation.py` | Compact RAG documents from graph correlation findings |
| `index_correlation.py` | Indexes graph correlation findings and Neo4j alerts into RAG |
| `sql_schema.py` | PostgreSQL schema context for SOC Chat Text-to-SQL |
| `sql_chat/` | Text-to-SQL sub-package (intent detection, SQL generation, validation, execution) |

## Embedding model (`TSOC_EMBEDDING_MODEL`)

Configured in `backend/.env`. Presets in `embeddings.py` → `EMBEDDING_MODEL_PRESETS`:

| Preset | Alias | Full id | Download | Dim |
|--------|-------|---------|----------|-----|
| `bge-small` | `small` | `BAAI/bge-small-en-v1.5` | ~33 MB | 384 |
| `bge-base` | `base` | `BAAI/bge-base-en-v1.5` | ~220 MB | 768 | **Default** |
| `bge-large` | `large` | `BAAI/bge-large-en-v1.5` | ~1.2 GB | 1024 |

See [Embedding model selection](../../../docs/10-soc-vector-rag.md#embedding-model-selection) and commented options in [`backend/.env.example`](../../.env.example).

## Related docs

- [SOC Vector RAG](../../../docs/10-soc-vector-rag.md)
- [Environment configuration](../../../docs/11-environment-configuration.md)
