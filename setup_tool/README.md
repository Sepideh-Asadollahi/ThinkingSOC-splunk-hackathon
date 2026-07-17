<!-- folder-readme: auto -->
# setup_tool

Parent: [README.md](../README.md)

Modular implementation of root `setup.py` (venv, deps, Docker Postgres, schema, seed).

## Demo seed (`seed.py`)

When inventory tables are empty and `--no-seed` is not set:

1. If `backend/data/demo/postgres_snapshot/manifest.json` exists → load the committed full JSON snapshot (inventory, analyses, findings, RAG, Chat, and Runbooks) via `init_store()` / `restore_postgres_snapshot_if_empty()`.
2. Else → CSV inventory fallback under `backend/data/demo/`.

See [docs/24-demo-postgresql-data.md](../docs/24-demo-postgresql-data.md).

## Contents

- `__init__.py`
- `cli.py`
- `config.py`
- `database.py`
- `deps.py`
- `docker.py`
- `layout.py`
- `log.py`
- `paths.py`
- `prerequisites.py`
- `runner.py`
- `seed.py`
- `subprocess_util.py`
- `venv.py`

## See also

- [setup.py](../setup.py)
- [install/README.md](../install/README.md)
