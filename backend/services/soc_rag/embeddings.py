"""Local embeddings for vector RAG (FastEmbed — no extra Docker service)."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

from config import Settings

logger = logging.getLogger(__name__)

_DEFAULT_CACHE = Path("/opt/.thinking-soc-cache/fastembed")

# Short aliases for TSOC_EMBEDDING_MODEL in backend/.env (FastEmbed / BGE ONNX).
# Canonical presets — documented in backend/.env.example and docs/10-soc-vector-rag.md
EMBEDDING_MODEL_CATALOG: Dict[str, Tuple[str, int, str]] = {
    "bge-small": ("BAAI/bge-small-en-v1.5", 384, "~33MB"),
    "bge-base": ("BAAI/bge-base-en-v1.5", 768, "~220MB"),
    "bge-large": ("BAAI/bge-large-en-v1.5", 1024, "~1.2GB"),
}

EMBEDDING_MODEL_PRESETS: Dict[str, Tuple[str, int, str]] = {
    **EMBEDDING_MODEL_CATALOG,
    "small": EMBEDDING_MODEL_CATALOG["bge-small"],
    "base": EMBEDDING_MODEL_CATALOG["bge-base"],
    "medium": EMBEDDING_MODEL_CATALOG["bge-base"],
    "large": EMBEDDING_MODEL_CATALOG["bge-large"],
}


def list_embedding_model_options() -> List[Dict[str, str | int]]:
    """Supported TSOC_EMBEDDING_MODEL presets for docs, status APIs, and tooling."""
    rows: List[Dict[str, str | int]] = []
    for preset, (full_id, dim, size) in EMBEDDING_MODEL_CATALOG.items():
        alias = {"bge-small": "small", "bge-base": "base", "bge-large": "large"}[preset]
        if preset == "bge-base":
            alias = "base / medium"
        rows.append(
            {
                "preset": preset,
                "alias": alias,
                "full_id": full_id,
                "dim": dim,
                "download_size": size,
            }
        )
    return rows


def resolve_embedding_model(model_name: str) -> str:
    """Normalize TSOC_EMBEDDING_MODEL (presets or full HuggingFace id)."""
    key = (model_name or "").strip().lower()
    preset = EMBEDDING_MODEL_PRESETS.get(key)
    if preset:
        return preset[0]
    return (model_name or "").strip() or EMBEDDING_MODEL_PRESETS["bge-base"][0]


def _download_hint(model_name: str) -> str:
    resolved = resolve_embedding_model(model_name)
    for _alias, (mid, _dim, size) in EMBEDDING_MODEL_PRESETS.items():
        if mid == resolved:
            return size
    return "varies"


def effective_embedding_dim(settings: Settings) -> int:
    """Vector size for the configured model (TSOC_EMBEDDING_DIM is validated, not authoritative)."""
    return embedding_dim_for_model(resolve_embedding_model(settings.tsoc_embedding_model))


def fastembed_cache_dir(settings: Settings) -> Path:
    raw = (getattr(settings, "tsoc_fastembed_cache_dir", None) or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    env = (os.environ.get("FASTEMBED_CACHE_PATH") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return _DEFAULT_CACHE


def _model_cache_folder_name(model_name: str) -> str:
    # HuggingFace hub layout used by fastembed (e.g. qdrant/bge-large-en-v1.5-onnx)
    slug = model_name.split("/", 1)[-1].replace(".", "-").lower()
    org = model_name.split("/")[0].lower() if "/" in model_name else "qdrant"
    if "bge-large" in slug:
        return "models--qdrant--bge-large-en-v1.5-onnx"
    if "bge-base" in slug:
        return "models--qdrant--bge-base-en-v1.5-onnx-q"
    if "bge-small" in slug:
        return "models--qdrant--bge-small-en-v1.5-onnx-q"
    return "models--{0}--{1}".format(org, slug)


def _cache_has_onnx(cache_dir: Path, model_name: str) -> bool:
    folder = cache_dir / _model_cache_folder_name(model_name)
    if not folder.is_dir():
        return False
    return any(folder.rglob("model*.onnx"))


def clear_embedding_cache(settings: Settings, model_name: str | None = None) -> None:
    """Remove incomplete or corrupt fastembed download."""
    cache = fastembed_cache_dir(settings)
    if model_name:
        target = cache / _model_cache_folder_name(model_name)
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
            logger.info("cleared fastembed cache for %s", model_name)
    elif cache.is_dir():
        shutil.rmtree(cache, ignore_errors=True)
        logger.info("cleared fastembed cache dir %s", cache)


@lru_cache(maxsize=4)
def _embedder(model_name: str, cache_dir: str):
    from fastembed import TextEmbedding

    os.environ["FASTEMBED_CACHE_PATH"] = cache_dir
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    return TextEmbedding(model_name=model_name, cache_dir=cache_dir)


def embedding_dim_for_model(model_name: str) -> int:
    from fastembed import TextEmbedding

    return int(TextEmbedding.get_embedding_size(model_name))


def _warmup_sync(settings: Settings) -> None:
    model_name = resolve_embedding_model(settings.tsoc_embedding_model)
    cache = fastembed_cache_dir(settings)
    cache.mkdir(parents=True, exist_ok=True)
    os.environ["FASTEMBED_CACHE_PATH"] = str(cache)

    if not _cache_has_onnx(cache, model_name):
        logger.warning(
            "fastembed cache incomplete for %s — re-downloading (%s ONNX)",
            model_name,
            _download_hint(model_name),
        )
        clear_embedding_cache(settings, model_name)

    logger.info("loading embedding model %s (cache=%s)", model_name, cache)
    model = _embedder(model_name, str(cache))
    list(model.embed(["warmup"]))
    logger.info("embedding model ready: %s", model_name)


async def ensure_embedding_model(settings: Settings) -> None:
    """Download/load ONNX model before Qdrant indexing (avoids partial /tmp cache)."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _warmup_sync, settings)


def _embed_sync(settings: Settings, texts: List[str]) -> List[List[float]]:
    cache = str(fastembed_cache_dir(settings))
    model = _embedder(resolve_embedding_model(settings.tsoc_embedding_model), cache)
    return [list(v) for v in model.embed(texts)]


async def embed_text(settings: Settings, text: str) -> List[float]:
    chunk = (text or "").strip()[:8000] or "empty"
    loop = asyncio.get_running_loop()
    vecs = await loop.run_in_executor(None, _embed_sync, settings, [chunk])
    return vecs[0]
