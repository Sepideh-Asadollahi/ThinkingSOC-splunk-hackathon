"""Repository paths and setup constants."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
SETUP_SCRIPT = REPO_ROOT / "setup.py"
BACKEND_DIR = REPO_ROOT / "backend"
VENV_DIR = BACKEND_DIR / ".venv"
REQUIREMENTS = BACKEND_DIR / "requirements.txt"
ENV_EXAMPLE = BACKEND_DIR / ".env.example"
ENV_FILE = BACKEND_DIR / ".env"
SCHEMA_SQL = BACKEND_DIR / "db" / "schema.sql"
COMPOSE_FILE = BACKEND_DIR / "docker-compose.yml"
DEMO_DATA_DIR = BACKEND_DIR / "data" / "demo"
DEFAULT_LOG_FILE = REPO_ROOT / "setup.log"

DEFAULT_POSTGRES_DSN = "postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc"

EXPECTED_TABLES: Tuple[str, ...] = (
    "tsoc_records",
    "tsoc_users",
    "tsoc_assets",
    "tsoc_relationships",
)

# Pip package name (requirements.txt) -> import module (after install)
REQUIRED_IMPORTS: Dict[str, str] = {
    "fastapi": "fastapi",
    "uvicorn[standard]": "uvicorn",
    "pydantic": "pydantic",
    "pydantic-settings": "pydantic_settings",
    "python-dotenv": "dotenv",
    "httpx": "httpx",
    "litellm": "litellm",
    "langgraph": "langgraph",
    "asyncpg": "asyncpg",
    "neo4j": "neo4j",
    "qdrant-client": "qdrant_client",
    "fastembed": "fastembed",
    "splunk-sdk": "splunklib",
    "psutil": "psutil",
    "pytest": "pytest",
    "pytest-asyncio": "pytest_asyncio",
}
