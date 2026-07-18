"""Setup orchestration."""

from __future__ import annotations

import os
from typing import List, Tuple

from setup_tool.cli import parse_args, resolve_log_path
from setup_tool.config import step_config
from setup_tool.database import step_database
from setup_tool.deps import step_install_requirements, step_pip_bootstrap, step_python_version
from setup_tool.docker import step_docker_postgres
from setup_tool.layout import step_project_layout
from setup_tool.log import LOG, configure_logging
from setup_tool.paths import DEFAULT_POSTGRES_DSN, ENV_FILE, REPO_ROOT, VENV_DIR
from setup_tool.prerequisites import step_prerequisites
from setup_tool.seed import step_seed
from setup_tool.subprocess_util import set_stream_output
from setup_tool.venv import ensure_running_in_venv, in_project_venv


def _setup_stream_output(verbose_cli: bool) -> None:
    env_verbose = os.environ.get("TSOC_INSTALL_VERBOSE", "").lower() in ("1", "true", "yes")
    set_stream_output(verbose_cli or env_verbose)


def main() -> int:
    args = parse_args()
    configure_logging(resolve_log_path(args), args.verbose)
    _setup_stream_output(args.verbose)

    LOG.info("=== ThinkingSOC Lite full setup (venv + deps + DB) — API not started ===")
    LOG.info("Repository: %s", REPO_ROOT)

    results: List[Tuple[str, bool]] = []
    if os.environ.get("TSOC_SETUP_PREREQ_OK") == "1":
        results.append(("prereq", True))
        ensure_running_in_venv()
    elif not in_project_venv():
        results.append(("prereq", step_prerequisites(args.skip_docker)))
        if not results[-1][1]:
            _print_summary(results)
            return 1
        ensure_running_in_venv()
    else:
        results.append(("prereq", step_prerequisites(args.skip_docker)))
        ensure_running_in_venv()

    installer_handled_deps = (
        os.environ.get("TSOC_SETUP_PREREQ_OK") == "1" and args.skip_pip
    )
    results.extend(
        [
            ("venv", True),
            ("layout", step_project_layout()),
            ("python", step_python_version()),
            ("pip", step_pip_bootstrap(skip_when_installer=installer_handled_deps)),
            ("deps", step_install_requirements(args.skip_pip)),
        ]
    )

    config_ok, env = step_config()
    results.append(("config", config_ok))
    if not config_ok:
        env = {}

    dsn = env.get("TSOC_POSTGRES_DSN", DEFAULT_POSTGRES_DSN)
    docker_ok = step_docker_postgres(args.start_postgres, args.skip_docker, dsn)
    results.append(("docker", docker_ok))
    if docker_ok:
        results.append(("database", step_database(env, apply_schema=not args.skip_schema)))
        results.append(("seed", step_seed(env, seed=not args.no_seed)))
    else:
        LOG.error(
            "[DOCKER] Skipping database/seed — Postgres is not running. "
            "Fix Docker Hub connectivity (pull images), then rerun: python setup.py --start-postgres --skip-pip"
        )
        results.append(("database", False))
        results.append(("seed", False))

    return _finish(results)


def _print_summary(results: List[Tuple[str, bool]]) -> None:
    LOG.info("=== Summary ===")
    for name, ok in results:
        LOG.info("  %-10s %s", name, "PASS" if ok else "FAIL")


def _finish(results: List[Tuple[str, bool]]) -> int:
    failed = [n for n, ok in results if not ok]
    _print_summary(results)

    if failed:
        LOG.error("Setup failed: %s", ", ".join(failed))
        return 1

    LOG.info("=== Setup complete ===")
    LOG.info("  Venv:   %s", VENV_DIR)
    LOG.info("  Config: %s", ENV_FILE)
    LOG.info("  Run API: cd backend && .venv/bin/python run.py")
    return 0
