"""Docker Compose / PostgreSQL readiness."""

from __future__ import annotations

import asyncio
import os
import time
from typing import List, Optional, Sequence, Tuple

from setup_tool.log import LOG
from setup_tool.paths import COMPOSE_FILE
from setup_tool.prerequisites import HINT_DOCKER_INSTALL, find_compose_cmd
from setup_tool.subprocess_util import run, run_live, stream_output_enabled

# Must match backend/docker-compose.yml container_name / volume `name:` and install/modules/docker_stack.sh
COMPOSE_PROJECT_NAME = "tsoc"
POSTGRES_CONTAINER = "tsoc-postgres"
POSTGRES_IMAGE = "postgres:16-alpine"
POSTGRES_VOLUME = "tsoc_pgdata"
QDRANT_CONTAINER = "tsoc-qdrant"
QDRANT_IMAGE = "qdrant/qdrant:v1.18.0"
QDRANT_VOLUME = "tsoc_qdrant_data"
QDRANT_HTTP_URL = "http://127.0.0.1:6333"
NEO4J_CONTAINER = "tsoc-neo4j"
NEO4J_IMAGE = "neo4j:5.26-community"
NEO4J_VOLUME = "tsoc_neo4j_data"

STACK_IMAGES: Tuple[str, ...] = (POSTGRES_IMAGE, QDRANT_IMAGE, NEO4J_IMAGE)

_DOCKER_PULL_ATTEMPTS = int(os.environ.get("TSOC_DOCKER_PULL_ATTEMPTS", "5"))
_DOCKER_PULL_DELAY_SEC = int(os.environ.get("TSOC_DOCKER_PULL_DELAY", "5"))
_DOCKER_UP_ATTEMPTS = int(os.environ.get("TSOC_DOCKER_UP_ATTEMPTS", "3"))


def compose_cmd() -> Optional[List[str]]:
    return find_compose_cmd()


def _is_transient_pull_error(output: str) -> bool:
    text = output.lower()
    return any(
        token in text
        for token in ("eof", "tls", "timeout", "connection reset", "i/o timeout", "failed to fetch")
    )


def pull_image_with_retry(image: str) -> bool:
    """Pull one image with retries (handles flaky Docker Hub / network)."""
    for attempt in range(1, _DOCKER_PULL_ATTEMPTS + 1):
        if attempt > 1:
            LOG.warning(
                "[DOCKER] Retrying pull %s (%s/%s) in %ss …",
                image,
                attempt,
                _DOCKER_PULL_ATTEMPTS,
                _DOCKER_PULL_DELAY_SEC,
            )
            time.sleep(_DOCKER_PULL_DELAY_SEC)
        LOG.info("[DOCKER] Pulling image %s …", image)
        proc = run_live(["docker", "pull", image], check=False) if stream_output_enabled() else run(
            ["docker", "pull", image], check=False
        )
        if proc.returncode == 0:
            LOG.info("[DOCKER] Pulled %s", image)
            return True
        out = (proc.stderr or "") + (proc.stdout or "")
        if attempt == _DOCKER_PULL_ATTEMPTS:
            LOG.error("[DOCKER] Failed to pull %s after %s attempts", image, _DOCKER_PULL_ATTEMPTS)
            if out.strip():
                LOG.error("[DOCKER] %s", out.strip()[-2000:])
    return False


def pull_stack_images(images: Sequence[str] = STACK_IMAGES) -> bool:
    ok = True
    for image in images:
        if not pull_image_with_retry(image):
            ok = False
    if not ok:
        LOG.error(
            "[DOCKER] Could not pull all stack images. Check access to registry-1.docker.io "
            "(proxy/firewall/DNS). Then rerun setup or: docker pull %s",
            " && docker pull ".join(images),
        )
    return ok


def _image_present_locally(image: str) -> bool:
    proc = run(["docker", "image", "inspect", image], check=False)
    return proc.returncode == 0


def ensure_stack_images(images: Sequence[str] = STACK_IMAGES) -> bool:
    """Pull images that are not already present locally."""
    missing = [img for img in images if not _image_present_locally(img)]
    if not missing:
        LOG.info("[DOCKER] Stack images already present locally")
        return True
    LOG.info("[DOCKER] Pulling %s missing image(s) …", len(missing))
    return pull_stack_images(missing)


def compose_up_with_retry(compose: List[str]) -> bool:
    os.environ.setdefault("COMPOSE_PROJECT_NAME", COMPOSE_PROJECT_NAME)
    for attempt in range(1, _DOCKER_UP_ATTEMPTS + 1):
        if attempt > 1:
            LOG.warning(
                "[DOCKER] Retrying docker compose up (%s/%s) …",
                attempt,
                _DOCKER_UP_ATTEMPTS,
            )
            time.sleep(_DOCKER_PULL_DELAY_SEC)
        if stream_output_enabled():
            up = run_live([*compose, "-f", str(COMPOSE_FILE), "up", "-d"], check=False)
        else:
            up = run([*compose, "-f", str(COMPOSE_FILE), "up", "-d"], check=False)
        if up.returncode == 0:
            return True
        out = (up.stderr or "") + (up.stdout or "")
        if attempt < _DOCKER_UP_ATTEMPTS and _is_transient_pull_error(out):
            ensure_stack_images()
            continue
    return False


def postgres_container_running_docker() -> bool:
    ps = run(
        [
            "docker",
            "ps",
            "--filter",
            f"name=^{POSTGRES_CONTAINER}$",
            "--filter",
            "status=running",
            "-q",
        ],
        check=False,
    )
    return bool((ps.stdout or "").strip())


def try_start_existing_postgres_container() -> bool:
    """Start a stopped tsoc-postgres container without recreating it."""
    if postgres_container_running_docker():
        return True
    ps = run(
        ["docker", "ps", "-a", "--filter", f"name=^{POSTGRES_CONTAINER}$", "-q"],
        check=False,
    )
    if not (ps.stdout or "").strip():
        return False
    LOG.info("[DOCKER] Starting stopped container %s …", POSTGRES_CONTAINER)
    start = run(["docker", "start", POSTGRES_CONTAINER], check=False)
    return start.returncode == 0


def remove_stale_stack_containers() -> None:
    """Remove exited/rename-mangled containers that break docker-compose v1 recreate."""
    run(["docker", "rm", "-f", POSTGRES_CONTAINER, QDRANT_CONTAINER, NEO4J_CONTAINER], check=False)
    ps = run(
        ["docker", "ps", "-a", "--filter", f"ancestor={POSTGRES_IMAGE}", "--format", "{{.Names}}"],
        check=False,
    )
    for name in (ps.stdout or "").splitlines():
        n = name.strip()
        if n and ("tsoc" in n.lower() or n == POSTGRES_CONTAINER):
            run(["docker", "rm", "-f", n], check=False)


def start_qdrant_docker_run() -> bool:
    """Start Qdrant with plain docker run (matches backend/docker-compose.yml)."""
    if _container_running(QDRANT_CONTAINER):
        LOG.info("[DOCKER] Qdrant container already running (%s)", QDRANT_CONTAINER)
        return True
    LOG.info("[DOCKER] Starting qdrant via docker run …")
    up = run_live(
        [
            "docker",
            "run",
            "-d",
            "--name",
            QDRANT_CONTAINER,
            "-p",
            "127.0.0.1:6333:6333",
            "-p",
            "127.0.0.1:6334:6334",
            "-v",
            f"{QDRANT_VOLUME}:/qdrant/storage",
            "-e",
            "QDRANT__SERVICE__HTTP_PORT=6333",
            "-e",
            "QDRANT__SERVICE__GRPC_PORT=6334",
            "--health-cmd",
            "bash -c ':> /dev/tcp/127.0.0.1/6333' || exit 1",
            "--health-interval",
            "10s",
            "--health-timeout",
            "5s",
            "--health-retries",
            "8",
            QDRANT_IMAGE,
        ],
        check=False,
    )
    if up.returncode != 0:
        LOG.error("[DOCKER] qdrant docker run failed (see output above)")
        return False
    return True


def start_postgres_docker_run() -> bool:
    """Start Postgres with plain docker run (matches backend/docker-compose.yml)."""
    remove_stale_stack_containers()
    if postgres_container_running_docker():
        LOG.info("[DOCKER] Postgres container already running (%s)", POSTGRES_CONTAINER)
        return True
    LOG.info("[DOCKER] Starting postgres via docker run …")
    up = run_live(
        [
            "docker",
            "run",
            "-d",
            "--name",
            POSTGRES_CONTAINER,
            "-e",
            "POSTGRES_DB=tsoc",
            "-e",
            "POSTGRES_USER=tsoc",
            "-e",
            "POSTGRES_PASSWORD=tsoc",
            "-p",
            "127.0.0.1:5432:5432",
            "-v",
            f"{POSTGRES_VOLUME}:/var/lib/postgresql/data",
            "--health-cmd",
            "pg_isready -U tsoc -d tsoc || exit 1",
            "--health-interval",
            "10s",
            "--health-timeout",
            "5s",
            "--health-retries",
            "5",
            POSTGRES_IMAGE,
        ],
        check=False,
    )
    if up.returncode != 0:
        LOG.error("[DOCKER] docker run failed (see output above)")
        return False
    return True


def start_neo4j_docker_run() -> bool:
    """Start Neo4j with plain docker run (matches backend/docker-compose.yml)."""
    if _container_running(NEO4J_CONTAINER):
        LOG.info("[DOCKER] Neo4j container already running (%s)", NEO4J_CONTAINER)
        return True
    LOG.info("[DOCKER] Starting neo4j via docker run …")
    up = run_live(
        [
            "docker",
            "run",
            "-d",
            "--name",
            NEO4J_CONTAINER,
            "-p",
            "127.0.0.1:7474:7474",
            "-p",
            "127.0.0.1:7687:7687",
            "-v",
            f"{NEO4J_VOLUME}:/data",
            "-e",
            "NEO4J_AUTH=neo4j/tsoc-tsoc",
            "-e",
            "NEO4J_server_memory_heap_initial__size=512m",
            "-e",
            "NEO4J_server_memory_heap_max__size=512m",
            "--health-cmd",
            "wget --no-verbose --tries=1 --spider http://127.0.0.1:7474 || exit 1",
            "--health-interval",
            "10s",
            "--health-timeout",
            "5s",
            "--health-retries",
            "10",
            NEO4J_IMAGE,
        ],
        check=False,
    )
    if up.returncode != 0:
        LOG.error("[DOCKER] neo4j docker run failed (see output above)")
        return False
    return True


def start_stack_docker_run() -> bool:
    """Fallback when compose up fails: start postgres, qdrant, neo4j individually."""
    return (
        start_postgres_docker_run()
        and start_qdrant_docker_run()
        and start_neo4j_docker_run()
    )


def _container_running(name: str) -> bool:
    ps = run(
        [
            "docker",
            "ps",
            "--filter",
            f"name=^{name}$",
            "--filter",
            "status=running",
            "-q",
        ],
        check=False,
    )
    return bool((ps.stdout or "").strip())


def compose_stack_running(compose: List[str]) -> bool:
    os.environ.setdefault("COMPOSE_PROJECT_NAME", COMPOSE_PROJECT_NAME)
    ps = run([*compose, "-f", str(COMPOSE_FILE), "ps", "--status", "running"], check=False)
    text = (ps.stdout or "").lower()
    return (
        "postgres" in text
        and "qdrant" in text
        and "neo4j" in text
        and "running" in text
    )


def postgres_container_running(compose: List[str]) -> bool:
    if compose_stack_running(compose):
        return True
    return postgres_container_running_docker()


def wait_postgres_ready(dsn: str, timeout_sec: int = 60) -> bool:
    LOG.info("[DOCKER] Waiting for PostgreSQL to accept connections (up to %ss) …", timeout_sec)

    async def probe() -> bool:
        import asyncpg

        deadline = time.monotonic() + timeout_sec
        last_err: Optional[Exception] = None
        while time.monotonic() < deadline:
            try:
                conn = await asyncpg.connect(dsn=dsn, timeout=5)
                await conn.close()
                return True
            except Exception as e:
                last_err = e
                await asyncio.sleep(2)
        LOG.debug("[DOCKER] Last connection error: %s", last_err)
        return False

    try:
        import asyncpg  # noqa: F401
    except ImportError:
        LOG.warning("[DOCKER] asyncpg not installed yet — skip readiness probe")
        time.sleep(5)
        return True

    if asyncio.run(probe()):
        LOG.info("[DOCKER] PostgreSQL is ready")
        return True
    LOG.error("[DOCKER] PostgreSQL not reachable at %s", dsn.split("@")[-1])
    return False


def wait_qdrant_ready(url: str = QDRANT_HTTP_URL, timeout_sec: int = 60) -> bool:
    LOG.info("[DOCKER] Waiting for Qdrant HTTP (up to %ss) …", timeout_sec)
    import urllib.request

    deadline = time.monotonic() + timeout_sec
    last_err: Optional[Exception] = None
    ready_url = url.rstrip("/") + "/readyz"
    # Bypass any system proxy for the local Qdrant readiness probe (proxy hijack -> SSL/EOF).
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while time.monotonic() < deadline:
        try:
            with opener.open(ready_url, timeout=5) as resp:
                if resp.status == 200:
                    LOG.info("[DOCKER] Qdrant is ready at %s", url)
                    return True
        except Exception as e:
            last_err = e
            time.sleep(2)
    LOG.warning("[DOCKER] Qdrant not reachable at %s (%s)", url, last_err)
    return False


def step_docker_postgres(start_postgres: bool, skip_docker: bool, dsn: str) -> bool:
    if skip_docker:
        LOG.info("[DOCKER] Skipped (--skip-docker)")
        return wait_postgres_ready(dsn) if dsn else True

    compose = compose_cmd()
    if not compose:
        LOG.error("[DOCKER] docker compose not available (run setup without --skip-docker after installing Docker)")
        LOG.error("%s", HINT_DOCKER_INSTALL)
        return False

    if not COMPOSE_FILE.is_file():
        LOG.error("[DOCKER] Missing %s", COMPOSE_FILE)
        return False

    if compose_stack_running(compose) or (
        postgres_container_running_docker()
        and _container_running(QDRANT_CONTAINER)
        and _container_running(NEO4J_CONTAINER)
    ):
        LOG.info("[DOCKER] Stack already running (postgres + qdrant + neo4j)")
        pg_ok = wait_postgres_ready(dsn)
        qd_ok = wait_qdrant_ready()
        return pg_ok and qd_ok

    if not start_postgres:
        LOG.error(
            "[DOCKER] Postgres is not running. Use: python setup.py --start-postgres  "
            "or: cd backend && docker-compose up -d"
        )
        return False

    if try_start_existing_postgres_container():
        if not _container_running(QDRANT_CONTAINER):
            start_qdrant_docker_run()
        pg_ok = wait_postgres_ready(dsn)
        qd_ok = wait_qdrant_ready()
        return pg_ok and qd_ok

    remove_stale_stack_containers()
    if not ensure_stack_images():
        LOG.warning("[DOCKER] Image pull incomplete — compose up may still try to pull")

    LOG.info("[DOCKER] Starting stack (postgres + qdrant + neo4j) via docker compose up -d …")
    if not compose_up_with_retry(compose):
        LOG.warning("[DOCKER] docker compose up failed; trying docker run fallback")
        remove_stale_stack_containers()
        if not ensure_stack_images():
            LOG.error("[DOCKER] Cannot start stack without required images (see pull errors above)")
            return False
        if not start_stack_docker_run():
            LOG.error("[DOCKER] Failed to start stack (see output above)")
            return False
        LOG.info("[DOCKER] Stack started via docker run fallback")
    else:
        LOG.info("[DOCKER] Compose up finished (postgres + qdrant + neo4j)")
    pg_ok = wait_postgres_ready(dsn)
    qd_ok = wait_qdrant_ready()
    return pg_ok and qd_ok
