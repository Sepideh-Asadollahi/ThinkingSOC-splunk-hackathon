# soc-rag-cache

## Overview

Community of 9 nodes

- **Size**: 9 nodes
- **Cohesion**: 0.1719
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| fastembed_cache_dir | Function | backend/services/soc_rag/embeddings.py | 21-28 |
| _model_cache_folder_name | Function | backend/services/soc_rag/embeddings.py | 31-41 |
| _cache_has_onnx | Function | backend/services/soc_rag/embeddings.py | 44-48 |
| clear_embedding_cache | Function | backend/services/soc_rag/embeddings.py | 51-61 |
| _embedder | Function | backend/services/soc_rag/embeddings.py | 65-70 |
| _warmup_sync | Function | backend/services/soc_rag/embeddings.py | 79-95 |
| ensure_embedding_model | Function | backend/services/soc_rag/embeddings.py | 98-101 |
| _embed_sync | Function | backend/services/soc_rag/embeddings.py | 104-107 |
| embed_text | Function | backend/services/soc_rag/embeddings.py | 110-114 |

## Execution Flows

- **_warmup_sync** (criticality: 0.37, depth: 2)
- **_embed_sync** (criticality: 0.36, depth: 1)

## Dependencies

### Outgoing

- `info` (4 edge(s))
- `is_dir` (3 edge(s))
- `str` (3 edge(s))
- `Path` (3 edge(s))
- `strip` (3 edge(s))
- `list` (2 edge(s))
- `embed` (2 edge(s))
- `mkdir` (2 edge(s))
- `lower` (2 edge(s))
- `split` (2 edge(s))
- `rmtree` (2 edge(s))
- `get_running_loop` (2 edge(s))
- `run_in_executor` (2 edge(s))
- `resolve` (2 edge(s))
- `expanduser` (2 edge(s))

### Incoming

- `backend/services/soc_rag/embeddings.py` (9 edge(s))
