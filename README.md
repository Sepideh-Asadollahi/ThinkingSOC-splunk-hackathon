# ThinkingSOC Agentic Ops Router

Splunk **10+** alert handoff → external FastAPI backend → identity resolution → **Security / Observability** agent pipelines → **Judge** verdict and structured outputs (PostgreSQL). Optional **Next.js** analyst UI for the hackathon demo.

| Resource | Description |
|----------|-------------|
| [Installation](#installation) | **Start here** — automatic install (recommended) or manual steps |
| [Architecture diagram](#architecture-diagram) | System integration (Mermaid, in README) · [full doc](architecture_diagram.md) |
| [docs/](docs/README.md) | HLD, LLD, agents, integration boundaries |
| [Developer SDK & CLI](docs/22-developer-sdk.md) | Typed Python SDK, CLI, evaluation runner |
| [Submission & evidence pack](submission/README.md) | Devpost evidence scripts; judging criteria mapping (local: `project-engineering/github-extras/08-judging-evidence.md`) |
| [docs/code-graph/graph.html](docs/code-graph/graph.html) | Interactive codebase graph |
| [Analyst UI](#analyst-ui-screenshots) | Demo screenshots — dashboard, investigation, correlation graph, inventory relationships |

---

## Architecture Diagram

High-level integration and data flow for the **ThinkingSOC Agentic Ops Router** (Splunk **10+** → FastAPI → agent pipelines → PostgreSQL / Qdrant / Neo4j → analyst UI).

```mermaid
flowchart LR
  subgraph splunk ["Splunk 10+"]
    SavedSearch["Saved / Correlation Searches"]
    Webhook["Alert Webhook"]
    REST["REST API :8089"]
    MCP["MCP Server\n(App 7931)"]
    SAIA["AI Assistant\n/predict"]
  end

  subgraph entry ["Entry Points"]
    SDK["Devtools SDK / CLI"]
    ManualAPI["REST APIs\n/analysis · /agents · /observability"]
  end

  subgraph backend ["FastAPI Backend :9876"]
    Ingest["Ingest API\nPOST /alerts/splunk-ingest"]
    Enrich["Inventory Enrichment\nusers / assets / relationships"]
    Router{"Agentic Ops Router\nLLM classifier (exclusive)"}

    subgraph secPipeline ["Security Pipeline (LangGraph)"]
      SecPrep["prepare → risk_engine → virustotal"]
      Defender["Defender"]
      Hunter["Hunter\n+ MCP hunt queries"]
      Judge["Judge\n+ MCP SAIA verify"]
      SecPost["framework_mapping\n+ investigation_questions"]
      InvSPL["Investigation SPL\nSAIA /predict + MCP execute"]
      SecPrep --> Defender --> Hunter --> Judge --> SecPost --> InvSPL
    end

    subgraph obsPipeline ["Observability Pipeline"]
      Entity["Entity Resolution"]
      Impact["Impact Context"]
      Diagnoser["Diagnoser"]
      Responder["Responder"]
      OpsJudge["Ops Judge"]
      Entity --> Impact --> Diagnoser --> Responder --> OpsJudge
    end

    Triage["Triage Priority\nscore + verdict + queue"]
    AdminOrg["Admin Org GAP\n(Security post-step)"]
    Correlation["Graph Correlation\n/api/v1/graph/*"]
    SOCChat["SOC Chat\nRAG + Text-to-SQL"]
    Dashboard["Dashboard\nKPIs + health + timeline"]
    Timeline["Investigation Workflow\ntimeline + analyst actions"]
    Integrations["Integration Settings\n+ post-install wizard"]
    LLM["LLM Service\nLiteLLM wrapper"]
  end

  subgraph stores ["Data Stores"]
    PG[("PostgreSQL\ntsoc_records + inventory\nchat + graph_findings")]
    Qdrant[("Qdrant\nvector embeddings\nSOC RAG")]
    Neo4j[("Neo4j\nalert graph\ncorrelation")]
  end

  subgraph frontend ["Next.js UI :3000"]
    AnalystUI["Analyst UI\nDashboard · Triage · Analysis\nCorrelation · Chat\nInventory · Relationships\nSplunk Connection"]
  end

  subgraph external ["External"]
    LLMProvider["LLM Provider\nOpenAI / Anthropic\nNVIDIA NIM / Qwen"]
    VTApi["VirusTotal API v3"]
  end

  SavedSearch --> Webhook
  Webhook -->|"sid + sample row"| Ingest
  SDK --> ManualAPI
  ManualAPI --> Router
  ManualAPI --> Ingest

  Ingest -->|"GET /jobs/{sid}/results"| REST
  Ingest --> Enrich --> Router
  Router -->|"optional MCP context"| MCP

  Router -->|security| SecPrep
  Router -->|observability| Entity
  Router -->|manual_review| Triage

  SecPrep --> VTApi
  Hunter -->|"MCP hunt"| MCP
  Judge -->|"MCP SAIA"| MCP
  InvSPL -->|"/predict"| SAIA
  InvSPL -->|"splunk_run_query"| MCP

  InvSPL --> AdminOrg --> Triage
  OpsJudge --> Triage

  Triage --> PG
  Triage --> Qdrant
  Ingest --> Correlation
  PG --> Correlation
  Correlation --> Neo4j
  Correlation --> PG

  PG --> Dashboard
  PG --> SOCChat
  PG --> Timeline
  Qdrant --> SOCChat

  LLM --> LLMProvider
  Router -.-> LLM
  Defender -.-> LLM
  Hunter -.-> LLM
  Judge -.-> LLM
  Diagnoser -.-> LLM
  Responder -.-> LLM
  OpsJudge -.-> LLM
  SOCChat -.-> LLM

  PG --> AnalystUI
  Qdrant --> AnalystUI
  Neo4j --> AnalystUI
  Integrations --> AnalystUI
```

| Flow | Mechanism |
|------|-----------|
| **Alert handoff** | Splunk webhook → `POST /api/v1/alerts/splunk-ingest` (`sid` + sample row) |
| **Full context** | Splunk REST v2 loads all job rows by `sid` |
| **Routing** | LLM-only Agentic Ops Router → **Security** or **Observability** (exclusive); `manual_review` when unclear |
| **Security analysis** | LangGraph: prepare → risk_engine → virustotal → Defender → Hunter → Judge → SPL |
| **Observability analysis** | Entity → Impact → Diagnoser → Responder → Ops Judge |
| **Splunk AI tools** | MCP (`splunk_run_query`, `saia_*`) + SAIA `/predict` for investigation SPL |
| **Persistence** | PostgreSQL `tsoc_records` + Qdrant (RAG) + Neo4j (correlation graph) |

**Deeper views:** [architecture_diagram.md](architecture_diagram.md) (data-flow table) · [docs/architecture-views.md](docs/architecture-views.md) (8 multi-perspective diagrams) · [docs/03-architecture.md](docs/03-architecture.md) (runtime layers).

### Architecture highlights

- **Full-context analysis:** alert `sid` is expanded to full Splunk job rows (not only the first webhook row).
- **Context-aware decisions:** inventory enrichment (`users/assets/relationships`) is applied before verdicting.
- **Exclusive routing:** each alert goes to **Security** or **Observability** (or `manual_review` when unclear) — never both pipelines at once.
- **Autonomous Splunk reasoning:** MCP + SAIA `/predict` are used for evidence gathering and investigation SPL.
- **Actionable outputs:** final verdict, triage priority, investigation SPL, and analyst-ready evidence.
- **Operational resilience:** fallback paths (including REST execution fallback) prevent single-point AI/tool failures.

---

## SOC challenges and why AI matters

Modern SOCs run on Splunk (and similar platforms) that already **detect** threats well. The bottleneck is no longer “finding events” it is **turning alerts into timely, correct decisions** at scale. That gap is where AI earns its place: not to replace analysts, but to **compress investigation time**, **standardize reasoning**, and **surface what humans should look at first**.

### Challenges analysts face every day

| SOC challenge | What goes wrong without help |
|---------------|------------------------------|
| **Alert fatigue** | Thousands of correlated events; analysts cannot open every `sid` with full job context before the next wave arrives. |
| **Thin alert handoffs** | Webhooks often ship one sample row; the real story lives in the full search result set. |
| **Security vs observability mix-ups** | The same platform fires auth failures, CPU spikes, and malware signals manual routing is slow and inconsistent. |
| **Missing business context** | Raw `src`/`user`/`dest` fields do not say whether the asset is crown-jewel or a lab VM, or who owns the account. |
| **Unstructured verdicts** | Free-text “looks bad” comments do not sort a queue, feed automation, or survive audits. |
| **Investigation expertise gap** | Writing correct CIM-aligned SPL across indexes and time ranges is a specialist skill under time pressure. |
| **Threat intel overload** | IOCs need interpretation (prevalence, context, false-positive patterns) not just a score from VirusTotal. |
| **Adversarial reasoning** | Good analysts argue *both* sides (false positive vs true positive); one-pass rules rarely do. |
| **Correlation at human scale** | Related alerts across hosts/users/incidents are hard to hold in working memory during a single shift. |
| **Low-confidence cases** | Models and rules disagree; tickets stall because nobody knows *who* should decide *what* next. |

Traditional SOAR playbooks and static correlation rules help for **known** patterns. They break on **ambiguous** alert titles, **dual-use** signals (e.g. auth anomaly + performance degradation), and **novel** TTPs exactly the cases that consume senior analyst time.

### What AI solves in this demo (and how)

ThinkingSOC uses AI **inside structured pipelines** (LangGraph + LiteLLM), with **deterministic fallbacks** when the LLM is off or unreachable so the hackathon flow stays demo-stable while showing where AI adds value.

| Problem | AI-assisted capability in ThinkingSOC | Where it lives |
|---------|----------------------------------------|----------------|
| Expand alert context beyond one row | Load full Splunk job results via REST (`sid`); optional MCP/SAIA for live evidence | Ingest + [Splunk REST / MCP](docs/02-integration-boundaries.md) |
| Route Security vs Observability | **Agentic Ops Router**: LLM reads full alert payload + metadata; **one** pipeline per alert | `alert_classifier_llm` + `prompt_alert_classifier_system.md` |
| Attach org risk to raw fields | Inventory enrichment → `risk_context` for verdicting | PostgreSQL inventory + enrichment resolver |
| Adversarial analysis | **Defender** (benign hypotheses) vs **Hunter** (attack expansion) before **Judge** | [Security pipeline](docs/04-agents-and-pipelines.md) |
| Authoritative, auditable outcome | **Judge** / **Ops Judge** final verdict, priority, next steps | LangGraph SOC + Observability pipelines |
| Sortable analyst queue | Post-analysis **triage** (`TRUE_POSITIVE`, `FALSE_POSITIVE`, `NEEDS_HUMAN_REVIEW`, priority score) | [Triage layer](docs/08-triage-priority-layer.md) |
| Investigation SPL under pressure | SAIA `/predict` + MCP execute + LiteLLM refine for CIM-style follow-up queries | [Investigation SPL](docs/13-cim-investigation-spl-mcp.md) |
| IOC interpretation | VirusTotal enrichment folded into LLM context | [Threat intel](docs/09-virustotal-threat-intel.md) |
| “What should I ask IT/admin?” | **Admin org GAP** one targeted org question after Security analysis | Post-Judge GAP attach |
| Shift-long memory / chat | **SOC Chat**: vector RAG over past analyses + Text-to-SQL over `tsoc_records` | [SOC vector RAG](docs/10-soc-vector-rag.md) |
| Cross-alert storyline | Correlation graph (Neo4j) + findings for explorer UI | [Correlation graph](docs/12-correlation-graph-service.md) |

**Design principle:** AI proposes and structures; **humans remain in the loop** for `manual_review`, low-confidence escalation, and investigation acknowledge/escalate workflows ([investigation workflow](docs/20-investigation-workflow.md)).

### Hackathon narrative (Security track)

- **Splunk** remains the system of record for detection and alerting.
- **ThinkingSOC** is the external **reasoning layer**: ingest → enrich → classify → multi-agent analysis → triage → persist → analyst UI.
- **Splunk MCP + SAIA** (optional) show Splunk-native AI **combined** with your own agent pipelines not a replacement for Splunk, but an orchestration story judges can run end-to-end.

Deeper problem/solution framing: [docs/01-system-overview.md](docs/01-system-overview.md) · Agent design: [docs/04-agents-and-pipelines.md](docs/04-agents-and-pipelines.md).

---

## Analyst UI (screenshots)

After [installation](#installation) and demo data seed, open the UI at `http://<server-ip>:3000/` (login: `admin` / `123456@a`).

### Overview dashboard

Live platform status — ingest volume, triage queue, pipeline activity, integration health (PostgreSQL, Neo4j, LiteLLM, Splunk MCP).

![ThinkingSOC overview dashboard — metrics, pipeline activity, and platform health](docs/images/overview-dashboard.png)

### Investigation workflow

Per-alert investigation view: triage verdict, Defender/Hunter/Judge timeline, analyst acknowledge/escalate gate, and recommended next steps.

![Investigation view — C2 alert with analyst gate and pipeline timeline](docs/images/investigation-workflow.png)

### Correlation graph explorer

Cross-alert kill-chain storyline with MITRE ATT&CK mapping — phishing → lateral movement (Neo4j-backed graph explorer).

![Correlation graph explorer — phishing-driven RDP and PsExec lateral movement](docs/images/correlation-graph-explorer.png)

### Inventory relationships

User-to-asset relationship map for enrichment — linked inventory attributes and alert field matching when alerts match only one side of a link.

![Inventory relationships — user–asset links with linked attributes and enrichment keys](docs/images/inventory-relationships.png)

---

## Installation

> **Start here.** This section gets ThinkingSOC running on your server.
>
> | Setting | Default |
> |---------|---------|
> | Install path | `/opt/thinking-soc-splunk-hackathon` |
> | Splunk home (this VM) | `/opt/splunk` |
> | API port | `9876` |
> | UI port | `3000` |
> | Demo login | `admin` / `123456@a` |

---

### Choose your install path

| Mode | Use when |
|------|----------|
| **[Automatic installation](#automatic-installation-recommended)** (recommended) | Fresh Ubuntu VM, hackathon demo, fastest path — one script installs Docker, Python, Node.js, DB stack, and production UI |
| **[Manual installation](#manual-installation)** | Air-gapped host, strict Docker policy, or you prefer not to run `install.sh` as root |

---

### After install (both modes)

Complete these three steps once the stack is up:

1. **Integration wizard** — Answer **Yes** when prompted (Splunk REST, LiteLLM, MCP), or run:
   ```bash
   sudo bash scripts/configure-integration.sh
   ```
2. **Splunk setup** — Follow the **[Splunk installation guide](#splunk-installation-guide)** (webhook + optional MCP/SAIA)
3. **Smoke test** — Validate with **[Testing with sample data](#testing-with-sample-data)** (no real Splunk alert required)

---

### Automatic installation (recommended)

`install.sh` installs everything in [Manual installation → Prerequisites](#prerequisites-manual-path-only) for you — no need to install Docker, Python, or Node.js by hand.

| Reference | Link / command |
|-----------|----------------|
| Install path | `/opt/thinking-soc-splunk-hackathon` (created if missing) |
| Override path | `TSOC_INSTALL_DIR=/other/path` (not recommended for hackathon demo) |
| Installer guide | [install/README.md](install/README.md) |
| Help | `sudo bash install.sh --help` |

#### Option A — Fresh server (recommended)

`install/bootstrap.sh` clones the repo, then runs the full installer.

> Use **`bootstrap.sh`**, not raw `install.sh` from GitHub — CDN cache can serve a stale `install.sh` for several minutes after a push. Requires **`sudo bash`**.

```bash
curl -fsSL https://raw.githubusercontent.com/Sepideh-Asadollahi/ThinkingSOC-splunk-hackathon/main/install/bootstrap.sh | sudo bash
```

#### Option B — Already have the repo

Run the installer from your checkout:

```bash
cd /opt/thinking-soc-splunk-hackathon
sudo bash install.sh
```

#### Option C — Clone manually, then install

Equivalent to Option A:

```bash
sudo mkdir -p /opt && cd /opt
sudo git clone --branch main --depth 1 https://github.com/Sepideh-Asadollahi/ThinkingSOC-splunk-hackathon.git thinking-soc-splunk-hackathon
cd /opt/thinking-soc-splunk-hackathon
sudo bash install.sh
```

---

#### Service mode

Chosen during install:

| Mode | Best for | Manage with |
|------|----------|-------------|
| **With systemd** (default) | Demo / production servers, auto-start on boot | `systemctl`, `journalctl` → [Service control with systemd](#service-control-with-systemd) |
| **Without systemd** | Quick trial, manual control | `scripts/start-tsoc-services.sh`, `logs/*.log` → [Production services (no systemd)](#production-services-no-systemd) |

---

#### Installer prompts

The installer will ask:

| Prompt | Default | What it does |
|--------|---------|--------------|
| Server IP for web access | detected LAN IP | Sets `NEXT_PUBLIC_TSOC_APP_URL` and `TSOC_DEV_ORIGIN` in `frontend/.env.local` |
| Load demo data? | Yes | Restores the full demo database backup (inventory + records + RAG + correlation findings) — see [docs/24-demo-postgresql-data.md](docs/24-demo-postgresql-data.md) |
| **Create systemd services?** | **Yes** | See [Installer: systemd or background](#installer-systemd-or-background) |

---

#### Installer: systemd or background

During `sudo bash install.sh`, step **Service deployment (systemd)** asks how to run the stack.

Both options use **production** frontend: `npm run build` then `npm run start` — not `npm run dev`.

| Your answer | Installer creates | Start / stop / logs |
|-------------|-------------------|---------------------|
| **Yes** — with systemd | `tsoc-backend.service`, `tsoc-frontend.service` under `/etc/systemd/system/` | `sudo systemctl start\|stop\|restart tsoc-backend tsoc-frontend` · `sudo journalctl -u tsoc-backend -f` |
| **No** — without systemd | Background PIDs + `logs/backend.log`, `logs/frontend.log` | `sudo bash scripts/start-tsoc-services.sh` · `tail -f logs/*.log` |

**Run after install — with systemd:**

```bash
sudo systemctl status tsoc-backend tsoc-frontend
curl -s http://127.0.0.1:9876/health
```

**Run after install — without systemd:**

```bash
sudo bash scripts/start-tsoc-services.sh
tail -f logs/backend.log logs/frontend.log
```

At the end of install, the full cheat sheet for your choice is printed. See also [install/README.md](install/README.md).

**Missed systemd during install?** Run once (same result as answering Yes):

```bash
cd /opt/thinking-soc-splunk-hackathon
sudo bash scripts/install-systemd.sh
```

---

#### What gets installed automatically

- **Docker** + Docker Compose (official repo)
- **Python 3.12+** (system packages; deadsnakes only on Ubuntu when needed)
- **Node.js 24 LTS** (NodeSource repo; `20+` minimum supported by this project)
- Backend virtual environment (`backend/.venv`) + all Python dependencies
- Frontend dependencies (`npm install`) + **production build** (`npm run build`) — always, not only with systemd
- **FastEmbed embedding model** pre-download (~220 MB default `bge-base` / medium) with progress bar before backend start
- Docker containers (PostgreSQL, Qdrant, Neo4j) + database schema
- **`backend/.env`** copied from `backend/.env.example` if missing (Postgres/Neo4j/Qdrant defaults match `docker-compose.yml`)
- **`frontend/.env.local`** generated with demo login and your server IP for LAN access

---

#### Post-install integration wizard

After install, the wizard runs automatically (default **Yes**). It sets Splunk REST, LiteLLM model/key, Splunk MCP (app 7931), runs a **live smoke test**, and prints editable `.env` values.

Re-run anytime:

```bash
sudo bash scripts/configure-integration.sh
sudo bash install/smoke-integration-config.sh   # verification only
```

See [docs/23-post-install-integration-wizard.md](docs/23-post-install-integration-wizard.md) and [install/README.md](install/README.md#post-install-integration-wizard-splunk-litellm-mcp). Manual edits: [Minimal changes you must make](#minimal-changes-you-must-make).

---

#### Troubleshooting the automatic installer

**One-liner / bootstrap issues**

| Symptom | Cause | Fix |
|---------|-------|-----|
| `BASH_SOURCE[0]: unbound variable` then `Missing required installer module: …/install/modules/common.sh` | Piped **`install.sh`** from GitHub raw (stale cache or pre-bootstrap version) | Use **`install/bootstrap.sh`** one-liner above, or clone manually under `/opt` |
| `Installer must run as root` | Missing `sudo` on the curl pipe | `curl … \| sudo bash` |
| Clone fails | No network / git / GitHub access | Clone manually (Option C above), or set `TSOC_REPO_URL` to a mirror |

**Verbose output**

By default the installer prints **full command output** in the console (`apt`, `pip`, `git`, `npm`, `curl` progress, `docker compose` image pulls, `setup.py`) so you can see where it stalls.

For minimal output only: `TSOC_INSTALL_QUIET=1 sudo bash install.sh`

**pip SSL errors**

If `pip` fails with SSL errors to `pypi.org`, the installer **auto-detects** SSL issues and switches to `trusted-host` mode (saved in `.tsoc-pip-trusted-host`).

- Force on/off: `TSOC_PIP_TRUSTED_HOST=1` or `=false`
- Also try: `sudo apt install -y ca-certificates && sudo update-ca-certificates`

**Docker pull failures**

If Docker fails with `EOF` or timeout pulling from `registry-1.docker.io`, check firewall/proxy/DNS to Docker Hub.

The installer retries image pulls (`TSOC_DOCKER_PULL_ATTEMPTS`, default 5) and asks before retrying project setup.

Manual pull: `docker pull postgres:16-alpine` (and qdrant/neo4j images from `backend/docker-compose.yml`).

**Network retries & resume**

Every installer step (apt, pip, npm, Docker, `setup.py`) auto-retries `${TSOC_STEP_AUTO_ATTEMPTS:-3}` times, then asks **Retry?** or **Stop?**

Completed steps are recorded in `$INSTALL_DIR/.tsoc-install-progress` so `sudo bash install.sh` can **resume** without redoing successful steps.

---

### Manual installation

> **Not the default path.** Use [Automatic installation](#automatic-installation-recommended) unless you need full control: existing Splunk/Docker policies, air-gapped hosts, or you prefer not to run `install.sh` as root.

The steps below mirror what the automated installer does, in order.

---

#### Prerequisites (manual path only)

| Component | Version / notes |
|-----------|-----------------|
| **CPU / RAM** | Minimum **12 CPU cores** and **12 GB RAM** (ThinkingSOC software only) |
| **Storage** | **100 GB SSD** recommended (ThinkingSOC software only) |
| **OS** | Ubuntu 24.04 LTS (tested) |
| **Splunk Enterprise or Cloud** | **10.x+** (REST v2 job results, webhook alert actions) — see [Splunk installation guide](#splunk-installation-guide) |
| **Python** | 3.12+ (+ `venv` and `pip` modules) |
| **Node.js** | 20+ (frontend only) |
| **Docker** | Docker Engine + Docker Compose v2 |
| **git** | Any recent version |
| **Core tools** | `curl`, `openssl`, `gpg` |

**Ubuntu/Debian install hints:**

```bash
# Docker (official apt repo; see docs.docker.com/engine/install/{ubuntu,debian})
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Python 3.12+
sudo apt update && sudo apt install -y python3.12 python3.12-venv python3-pip
# Debian note: do not use deadsnakes PPA on Debian; use distro packages or pyenv/source when needed.

# Node.js 24 LTS (NodeSource)
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo bash -
sudo apt install -y nodejs

# Core tools
sudo apt install -y curl openssl gnupg git
```

| Port | Service |
|------|---------|
| `9876` | API |
| `3000` | UI |
| `5432` / `6333` / `7474` | Postgres / Qdrant / Neo4j (on `127.0.0.1`) |

> Splunk configuration is **not** part of either install path — complete it after the stack is up: **[Splunk installation guide](#splunk-installation-guide)**.

---

#### Step overview

| Step | What you do | Automated equivalent |
|------|-------------|----------------------|
| 1 | Install OS prerequisites | `install.sh` → prerequisite checks (automatic path skips this section) |
| 2 | Clone the repository | `install.sh` → `git clone` |
| 3 | Python venv + `pip install` | `install.sh` → `setup_venv` |
| 4 | Docker stack + `setup.py` (schema, seed) | `install.sh` → `docker compose up` + `run_project_setup` |
| 5 | Frontend `npm install` + `.env.local` | `install.sh` → `setup_frontend` |
| 6 | Configure `backend/.env` + Splunk | `setup.py` creates `.env` from `.env.example`; edit Splunk creds + [Splunk-side setup](#splunk-side-setup) |
| 7 | Start backend + frontend | Optional systemd in `install.sh` |
| 8 | Verify installation | Installer smoke test |
| 9 | Optional: systemd services | `install.sh` → systemd prompt |

Default install path: **`/opt/thinking-soc-splunk-hackathon`** (same for automatic and manual installs).

---

#### Step 1 — Install prerequisites

Install everything in [Prerequisites (manual path only)](#prerequisites-manual-path-only) before continuing.

**Verify:**

```bash
docker --version && docker compose version
python3 --version    # 3.12+ recommended (3.11+ minimum)
node --version       # v20+
git --version
```

**Ensure the Docker daemon is running:**

```bash
sudo systemctl enable --now docker
docker info
```

---

#### Step 2 — Clone the repository

```bash
sudo mkdir -p /opt
cd /opt
sudo git clone https://github.com/Sepideh-Asadollahi/ThinkingSOC-splunk-hackathon.git thinking-soc-splunk-hackathon
cd /opt/thinking-soc-splunk-hackathon
```

---

#### Step 3 — Python virtual environment

Create the backend venv and install dependencies.

> Do **not** use a repo-root `.venv` — use `backend/.venv`.

```bash
cd /opt/thinking-soc-splunk-hackathon
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install --upgrade pip
backend/.venv/bin/pip install -r backend/requirements.txt
```

---

#### Step 4 — Project setup (Docker stack + database schema)

**Start all data services** (PostgreSQL, Qdrant, Neo4j):

```bash
cd backend
docker compose up -d
```

This brings up every service defined in `backend/docker-compose.yml`.

**Wait until they are healthy:**

```bash
docker ps --filter name=tsoc-
docker exec tsoc-postgres pg_isready -U tsoc -d tsoc
curl -s http://127.0.0.1:6333/readyz
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:7474
```

**Apply schema and demo data** from the repository root (`setup.py` does not start Docker — containers are already running):

```bash
cd ..   # repo root (if you are still in backend/)
backend/.venv/bin/python setup.py --skip-docker -v
```

This creates `backend/.env` from `.env.example` if missing, applies `backend/db/schema.sql`, and loads demo data (postgres snapshot or CSV fallback).

- To skip demo data only: add `--no-seed`
- See [docs/24-demo-postgresql-data.md](docs/24-demo-postgresql-data.md)

---

#### Step 5 — Frontend dependencies and environment

```bash
cd frontend
cp .env.example .env.local
npm install
```

Edit `frontend/.env.local` for your deployment (see [Minimal changes](#minimal-changes-you-must-make)):

| Variable | Action |
|----------|--------|
| `AUTH_SECRET` | Long random string (`openssl rand -base64 42`) |
| `TSOC_DEV_ORIGIN` | Hostname/IP you use in the browser (LAN demo) |
| `NEXT_PUBLIC_TSOC_APP_URL` | Same as `TSOC_DEV_ORIGIN` |
| `TSOC_BACKEND_URL` | Keep `http://127.0.0.1:9876` when API runs on same host |

```bash
cd ..   # back to repo root
```

---

#### Step 6 — Backend configuration (Splunk + secrets)

```bash
cd backend
# Skip if setup.py already created .env
test -f .env || cp .env.example .env
```

Edit `backend/.env` minimum for Splunk integration:

| Variable | Action |
|----------|--------|
| `SPLUNK_MGMT_URL` | Your Splunk management URL (default `https://127.0.0.1:8089`) |
| `SPLUNK_USERNAME` / `SPLUNK_PASSWORD` | Service account with search + REST access |
| `TSOC_INGEST_TOKEN` | Optional; must match frontend if set |
| `LITELLM_API_KEY` | **Required** for AI-assisted Defender/Hunter/Judge (post-install wizard prompts for it) |

Then complete [Splunk-side setup](#splunk-side-setup):

- Install `ThinkingSOC_Hackathon_Splunk_App`
- Webhook URL: `http://<backend-ip>:9876/api/v1/alerts/splunk-ingest`
- Optional: MCP/SAIA

---

#### Step 7 — Run the stack

**Recommended** (production UI — matches installer):

```bash
sudo bash scripts/start-tsoc-services.sh
```

**Or two terminals:**

```bash
# Terminal 1 — backend
cd backend && .venv/bin/python run.py
curl -s http://127.0.0.1:9876/health

# Terminal 2 — frontend (build once, then start)
cd frontend && npm run build && npm run start
```

Open the UI at `http://127.0.0.1:3000/` or `http://<server-ip>:3000/`.

Demo login: `admin` / `123456@a` (from `TSOC_DEMO_*` in `.env.local`).

**Optional — frontend development only** (hot reload, webpack-hmr; not used after `install.sh`):

```bash
cd frontend && npm run dev
```

---

#### Step 8 — Verify installation

Manual checks equivalent to the installer smoke test:

```bash
# Files and venv
test -f backend/.venv/bin/python && test -f backend/.env && test -f frontend/.env.local

# Python imports
backend/.venv/bin/python -c "import fastapi, uvicorn, asyncpg, litellm"

# Containers
docker ps --filter name=tsoc-postgres --filter name=tsoc-qdrant --filter name=tsoc-neo4j

# Postgres schema
docker exec tsoc-postgres psql -U tsoc -d tsoc -c "\dt" | grep tsoc_

# Demo data (if you ran setup / install with demo seed)
docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc "SELECT COUNT(*) FROM tsoc_users;"
docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc "SELECT COUNT(*) FROM tsoc_records;"
```

---

#### Step 9 — Optional: systemd services (manual)

Prefer **`sudo bash scripts/install-systemd.sh`** after a normal install — it builds the frontend and installs the same units as `install.sh`.

Full command reference: [Service control with systemd](#service-control-with-systemd).

To create units by hand (adjust `INSTALL_DIR`):

```bash
INSTALL_DIR=/opt/thinking-soc-splunk-hackathon

sudo tee /etc/systemd/system/tsoc-backend.service <<EOF
[Unit]
Description=ThinkingSOC Backend (FastAPI)
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=${INSTALL_DIR}/backend
ExecStart=${INSTALL_DIR}/backend/.venv/bin/python run.py
Restart=on-failure
RestartSec=5
Environment=TSOC_HTTP_HOST=127.0.0.1
Environment=TSOC_HTTP_PORT=9876

[Install]
WantedBy=multi-user.target
EOF

# Frontend: run `npm run build` in frontend/ first
sudo tee /etc/systemd/system/tsoc-frontend.service <<EOF
[Unit]
Description=ThinkingSOC Frontend (Next.js)
After=network.target tsoc-backend.service

[Service]
Type=simple
WorkingDirectory=${INSTALL_DIR}/frontend
ExecStart=$(command -v node) ${INSTALL_DIR}/frontend/node_modules/.bin/next start -H 0.0.0.0 -p 3000
Restart=on-failure
RestartSec=5
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now tsoc-backend tsoc-frontend
```

See [Service control with systemd](#service-control-with-systemd) for start/stop, logs, and troubleshooting.

---

## Service control with systemd

Use this when you answered **Yes** to the systemd prompt in `install.sh`, or after `scripts/install-systemd.sh`.

| Unit | Role | Port |
|------|------|------|
| `tsoc-backend` | FastAPI API (uvicorn via `backend/run.py`) | `9876` (localhost only) |
| `tsoc-frontend` | Next.js production UI (`next start`) | `3000` (all interfaces) |

**Requires:** Docker running (`tsoc-postgres`, `tsoc-qdrant`, `tsoc-neo4j` containers). Backend startup may take 1–3 minutes on first boot while embeddings load.

### Enable systemd after install (if you chose No in install.sh)

```bash
cd /opt/thinking-soc-splunk-hackathon
sudo bash scripts/install-systemd.sh
```

Stops using background PIDs; installs the same units as the installer would have, enables boot, and starts both services. Prefer answering **Yes** during `install.sh` instead of running this script.

### Status and health

```bash
sudo systemctl status tsoc-backend tsoc-frontend
curl -s http://127.0.0.1:9876/health
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/login
```

### Start, stop, restart

```bash
# Start (backend first is fine; units declare After= dependencies)
sudo systemctl start tsoc-backend tsoc-frontend

# Stop UI before API
sudo systemctl stop tsoc-frontend tsoc-backend

# Restart both (after config or code changes)
sudo systemctl restart tsoc-backend tsoc-frontend
```

### Boot (auto-start on power-on)

```bash
sudo systemctl enable tsoc-backend tsoc-frontend   # enable
sudo systemctl disable tsoc-backend tsoc-frontend  # disable
```

### Logs

```bash
# Follow live
sudo journalctl -u tsoc-backend -f
sudo journalctl -u tsoc-frontend -f
sudo journalctl -u tsoc-backend -u tsoc-frontend -f

# Last 100 lines
sudo journalctl -u tsoc-backend -n 100 --no-pager
sudo journalctl -u tsoc-frontend -n 100 --no-pager

# Since last boot
sudo journalctl -u tsoc-backend -b --no-pager
```

### After editing unit files

```bash
sudo systemctl daemon-reload
sudo systemctl restart tsoc-backend tsoc-frontend
```

Unit paths:

- `/etc/systemd/system/tsoc-backend.service`
- `/etc/systemd/system/tsoc-frontend.service`

### Frontend rebuild (production UI)

Systemd runs `next start` (not dev/HMR). After UI code changes:

```bash
cd frontend && npm run build
sudo systemctl restart tsoc-frontend
```

### Troubleshooting

| Symptom | Check |
|---------|--------|
| `tsoc-backend` failed | `journalctl -u tsoc-backend -n 80`; Docker up? `docker ps`; Postgres ready? |
| `active` but `/health` fails | Wait for embedding model on first start; retry `curl` after ~2 min |
| UI 502 / empty dashboard | Backend must be up on `127.0.0.1:9876`; `TSOC_BACKEND_URL` in `frontend/.env.local` |
| Login works, no data | Expected until Splunk/webhook configured; backend logs show ingest/API errors |

---

## Production services (no systemd)

When `install.sh` did **not** use systemd, the installer runs:

| Process | Command | Mode |
|---------|---------|------|
| Backend | `backend/.venv/bin/python run.py` | API on `127.0.0.1:9876` |
| Frontend | `npm run start` (after `npm run build`) | Production UI on `:3000` |

**Not** `npm run dev` — dev mode is only for local UI hacking (see [Quick start (developers)](#quick-start-developers)).

```bash
# Start or restart (builds .next if missing, then npm run start)
sudo bash scripts/start-tsoc-services.sh

# Logs
tail -f logs/backend.log logs/frontend.log
```

After changing frontend code:

```bash
cd frontend && npm run build
sudo bash scripts/start-tsoc-services.sh
```

Manual terminals (production):

```bash
cd backend && .venv/bin/python run.py
cd frontend && npm run build && npm run start
```

To switch to systemd later: `sudo bash scripts/install-systemd.sh`.

---

## Splunk installation guide

Target platform: **Splunk Enterprise or Cloud 10.x+**. On this hackathon VM, Splunk home is typically **`/opt/splunk`** (`$SPLUNK_HOME`).

### What to install in Splunk

| Component | Required? | Purpose |
|-----------|-----------|---------|
| **`ThinkingSOC_Hackathon_Splunk_App`** | **Yes** | Defines index `thinking_soc`; documents webhook contract (no product UI in Splunk) |
| **Built-in Webhook Alert Action** | No (use **ThinkingSOC_Hackathon_Splunk_App** action below) | Legacy generic Webhook — prefer the app action |
| **ThinkingSOC_Hackathon_Splunk_App Alert Action** | **Yes** | Branded action; sends `sid` + first result row to backend |
| **Service account** | **Yes** | REST on **8089** backend loads **full** job results via `GET /services/search/v2/jobs/{sid}/results` |
| **Splunk MCP Server** (Splunkbase [7931](https://splunkbase.splunk.com/)) | Optional | Live SPL, metadata, Hunter/Judge MCP context |
| **Splunk AI Assistant (SAIA)** | Optional | `/predict` and `saia_ask_splunk_question` when MCP is enabled |

Inventory (users, assets, relationships) lives in **PostgreSQL**, not in the Splunk app. See [docs/02-integration-boundaries.md](docs/02-integration-boundaries.md).

### 1. Install `ThinkingSOC_Hackathon_Splunk_App`

From the repository root, copy or symlink the app into Splunk’s apps directory:

```bash
export SPLUNK_HOME=/opt/splunk   # adjust if different

sudo cp -r ThinkingSOC_Hackathon_Splunk_App "$SPLUNK_HOME/etc/apps/"
# Dev alternative (live edits without copy):
# sudo ln -sf "$(pwd)/ThinkingSOC_Hackathon_Splunk_App" "$SPLUNK_HOME/etc/apps/ThinkingSOC_Hackathon_Splunk_App"

"$SPLUNK_HOME/bin/splunk" restart
```

Verify the app is enabled:

```bash
"$SPLUNK_HOME/bin/splunk" list app | grep thinking_soc
```

The app creates index **`thinking_soc`** (`default/indexes.conf`). You do not need to index demo CSVs there for the hackathon path webhook + REST `sid` expansion is what the backend uses.

More detail: [ThinkingSOC_Hackathon_Splunk_App/README.md](ThinkingSOC_Hackathon_Splunk_App/README.md).

### 2. Create a Splunk service account

Create a dedicated user (e.g. `tsoc_svc`) with at least:

- **`search`** read job results for alert `sid`
- **`list_*`** (or equivalent) list/search metadata as needed for REST
- Access to indexes your saved searches/alerts use (often `*` for demo)

Set credentials in **`backend/.env`**:

```bash
SPLUNK_MGMT_URL=https://127.0.0.1:8089
SPLUNK_USERNAME=tsoc_svc
SPLUNK_PASSWORD=<your-password>
```

Test REST credentials (replace user/password; `-k` only for self-signed TLS):

```bash
curl -sk -u "tsoc_svc:YOUR_PASSWORD" \
  "https://127.0.0.1:8089/services/server/info?output_mode=json" | head
```

With the backend running, open **Splunk connection** in the UI (`/splunk-connection`) or call `GET /api/v1/mcp/status` when MCP is configured.

If TLS uses a self-signed cert, use the same trust settings as your Splunk deployment (see [docs/11-environment-configuration.md](docs/11-environment-configuration.md)).

### 3. Configure ThinkingSOC_Hackathon_Splunk_App alert action

For each alert that should trigger ThinkingSOC:

1. In Splunk: **Settings → Searches, reports, and alerts** → open the alert → **Trigger Actions**.
2. Add action **ThinkingSOC_Hackathon_Splunk_App** (not the generic **Webhook** action).
3. **Backend URL:** `http://<backend-host>:9876/api/v1/alerts/splunk-ingest`  
   - Same machine: `http://127.0.0.1:9876/api/v1/alerts/splunk-ingest`  
   - Remote backend: use the server LAN IP (e.g. `http://192.168.1.150:9876/...`).
4. **Bearer token:** only when **`TSOC_INGEST_TOKEN`** is set in `backend/.env` (must match `frontend/.env.local` when UI proxy is used). Leave empty for local demos. See [docs/11-environment-configuration.md](docs/11-environment-configuration.md#tsoc_ingest_token-optional-ingest-auth) for how to generate and sync the token.
5. Ensure the alert’s search produces a **`sid`** when it fires (normal for scheduled/real-time alerts).

Payload contract: `sid`, `search_name`, `result` (first row). Backend normalizes fields and fetches all rows for that job via REST.

**Auto triage (default):** `install.sh` sets `TSOC_INGEST_AUTO_ANALYZE=true` in `backend/.env`. Ingest returns **HTTP 202** and runs triage in the background. Do **not** add query parameters to the URL — config overrides via query string are rejected with **HTTP 400**.

#### Ingest token quick reference

| `TSOC_INGEST_TOKEN` in backend | Splunk Bearer field | Ingest works? |
|--------------------------------|---------------------|---------------|
| Empty | Empty | Yes (default) |
| Set | Empty | No (`401`) |
| Set | Same value | Yes |

Generate: `openssl rand -hex 24`, or run `sudo bash scripts/configure-integration.sh` and enable the shared ingest token.

### 4. Optional: Splunk MCP + SAIA

For Hunter/Judge live evidence and investigation SPL execution:

1. Run the **post-install wizard** (or `sudo bash scripts/configure-integration.sh`) — it installs/enables **Splunk MCP Server** (Splunkbase **7931**), grants `mcp_tool_execute`, mints `SPLUNK_MCP_TOKEN`, and verifies via smoke test. See [docs/23-post-install-integration-wizard.md](docs/23-post-install-integration-wizard.md).
2. **Restart Splunk** after app changes: `$SPLUNK_HOME/bin/splunk restart` (printed at end of wizard).
3. Enable **Splunk AI Assistant** if you want SAIA tools.
4. Manual fallback: `backend/.venv/bin/python scripts/setup_splunk_mcp.py` or `scripts/mint_splunk_mcp_token.py` — [docs/15-splunk-mcp-integration.md](docs/15-splunk-mcp-integration.md).

The demo works without MCP: pipelines use rule/LLM fallbacks when MCP or REST is unavailable.

### Splunk install checklist

| Step | Done? |
|------|-------|
| `ThinkingSOC_Hackathon_Splunk_App` under `$SPLUNK_HOME/etc/apps/` | ☐ |
| Splunk restarted | ☐ |
| Service account in `backend/.env` | ☐ |
| Webhook URL points to running backend `:9876` | ☐ |
| (Optional) MCP + SAIA configured | ☐ |

---

## Testing with sample data

You can validate the full pipeline **without** waiting for Splunk to fire a real alert. Sample **webhook JSON** files mimic Splunk’s POST body; **`setup.py`** or **`install.sh`** (demo data = Yes) seeds PostgreSQL so enrichment and triage have context.

### 1. Seed backend demo data (PostgreSQL)

From repo root (Docker Postgres must be up — after [Automatic installation](#automatic-installation-recommended) or [Manual installation](#manual-installation)):

```bash
backend/.venv/bin/python setup.py --skip-docker -v
# Skip demo seed only: add --no-seed
```

**Default:** restores the bundled **full database backup** `backend/data/demo/postgres_dump/tsoc_demo.sql` (`pg_dump`) — a byte-for-byte replica of the source server: inventory, all `tsoc_records`, all `graph_findings` (Correlation), and all `tsoc_rag_documents` (SOC Chat RAG). If the backup is missing it falls back to the JSON moment snapshot under `backend/data/demo/postgres_snapshot/`, then CSV packs. Refresh with `bash scripts/backup-demo-db.sh`; restore manually with `bash scripts/restore-demo-db.sh`.

Details: [docs/24-demo-postgresql-data.md](docs/24-demo-postgresql-data.md).

Confirm:

```bash
docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc "SELECT COUNT(*) FROM tsoc_users;"
docker exec tsoc-postgres psql -U tsoc -d tsoc -tAc "SELECT COUNT(*) FROM tsoc_records;"
```

Start the stack (production — same as `install.sh`):

```bash
sudo bash scripts/start-tsoc-services.sh
# or manually:
# Terminal 1: cd backend && .venv/bin/python run.py
# Terminal 2: cd frontend && npm run build && npm run start
```

UI: `http://127.0.0.1:3000/` demo login `admin` / `123456@a`. For hot-reload UI dev only: `cd frontend && npm run dev`.

### 2. Sample webhook payloads (`scripts/samples/`)

| File | Scenario |
|------|----------|
| [splunk-webhook-example.json](scripts/samples/splunk-webhook-example.json) | Security brute force (`src_ip`, `domain` for threat-intel demo) |
| [splunk-webhook-botsv1-osk-sysmon.json](scripts/samples/splunk-webhook-botsv1-osk-sysmon.json) | Security BOTSv1 Sysmon / MITRE T1218 |
| [splunk-webhook-observability-cpu-latency.json](scripts/samples/splunk-webhook-observability-cpu-latency.json) | Observability CPU + latency on `payment-api` |
| [ATTACKS/attack_step_*.json](scripts/samples/ATTACKS/) | Four-step kill chain (correlation / graph demo) |

See [scripts/samples/README.md](scripts/samples/README.md).

### 3. Run tests with `test_splunk_webhook.py`

Script: [scripts/test_splunk_webhook.py](scripts/test_splunk_webhook.py). Requires backend on **9876** (reads `backend/.env` and optional `TSOC_INGEST_TOKEN`).

**Default (console)** same path as the UI “route analysis”; uses rows from the JSON file when Splunk is offline:

```bash
python3 scripts/test_splunk_webhook.py scripts/samples/splunk-webhook-example.json
```

**Webhook ingest** posts to `POST /api/v1/alerts/splunk-ingest` (like Splunk):

```bash
python3 scripts/test_splunk_webhook.py scripts/samples/splunk-webhook-example.json --mode webhook
```

**Full** webhook ingest, then poll stored events:

```bash
python3 scripts/test_splunk_webhook.py scripts/samples/splunk-webhook-botsv1-osk-sysmon.json --mode full -v
```

**Live Splunk REST** (needs working `SPLUNK_*` creds and a real `sid` in the JSON):

```bash
python3 scripts/test_splunk_webhook.py scripts/samples/splunk-webhook-example.json --live-splunk
```

**Without a configured LiteLLM API key**, SOC/Observability pipelines still run but use **rule-based fallbacks** when LLM calls fail (lower quality than full AI analysis). For demos, set `LITELLM_MODEL` and `LITELLM_API_KEY` in `backend/.env` (or run the post-install wizard).

```bash
python3 scripts/test_splunk_webhook.py scripts/samples/splunk-webhook-observability-cpu-latency.json
```

**ATTACKS correlation campaign** (Neo4j + inventory for t8372):

```bash
cd backend && source .venv/bin/activate
python scripts/seed/enrich_attacks_correlation.py --seed-inventory --verify
python3 ../scripts/test_splunk_webhook.py ../scripts/samples/ATTACKS/attack_step_1_phishing.json --mode webhook
# Repeat for attack_step_2 … attack_step_4
```

Details: [scripts/samples/ATTACKS/README.md](scripts/samples/ATTACKS/README.md).

### 4. Quick `curl` webhook test

With default auto-analyze (`TSOC_INGEST_AUTO_ANALYZE=true`), expect **HTTP 202**:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:9876/api/v1/alerts/splunk-ingest \
  -H "Content-Type: application/json" \
  -d @scripts/samples/splunk-webhook-example.json
```

Do not use URL query parameters for configuration (e.g. `?auto_analyze=true` returns **400**).

If ingest token is enabled:

```bash
curl -sS -X POST http://127.0.0.1:9876/api/v1/alerts/splunk-ingest \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TSOC_INGEST_TOKEN" \
  -d @scripts/samples/splunk-webhook-example.json
```

### 5. What to check after a sample run

| Where | What to verify |
|-------|----------------|
| Script output | `RESULT SUMMARY` track (security/observability), Judge verdict, ingest status |
| UI → **Triage** | New item with priority and verdict |
| UI → **Analysis** | Defender / Hunter / Judge phases (when LLM enabled) |
| UI → **Dashboard** / **SOC Chat** | Stored events (after ingest + optional background triage) |
| Postgres | `docker exec tsoc-postgres psql -U tsoc -d tsoc -c "SELECT record_type, created_at FROM tsoc_records ORDER BY created_at DESC LIMIT 5;"` |

Background analysis after ingest is **on by default** (`TSOC_INGEST_AUTO_ANALYZE=true` in `backend/.env`; returns HTTP 202). Set to `false` to ingest-only. Not overridable via URL. See [docs/11-environment-configuration.md](docs/11-environment-configuration.md).

### Sample testing checklist

| Step | Done? |
|------|-------|
| `setup.py` / `install.sh` loaded full demo backup (inventory + records + RAG + correlation) | ☐ |
| Backend `GET /health` OK | ☐ |
| `test_splunk_webhook.py` on at least one `scripts/samples/*.json` | ☐ |
| Result visible in UI Triage or Analysis | ☐ |
| (Optional) Real Splunk alert → same webhook URL | ☐ |

---

## Quick start (developers)

> **First time?** Use [Installation](#installation) — **`curl … \| sudo bash`** (one-liner) or **`cd /opt/thinking-soc-splunk-hackathon && sudo bash install.sh`** after clone.
> This section is for developers who already have dependencies and want to run or hack on the stack without re-running the full installer.

### 1. One-time setup (repo root)

If you skipped `install.sh`, creates `backend/.venv`, installs Python deps, starts Postgres, applies schema:

```bash
sudo mkdir -p /opt && cd /opt
sudo git clone https://github.com/Sepideh-Asadollahi/ThinkingSOC-splunk-hackathon.git thinking-soc-splunk-hackathon
cd /opt/thinking-soc-splunk-hackathon
python3 setup.py
```

`setup.py` is equivalent to `python3 setup.py --start-postgres` (Postgres via Docker when needed).

### 2. Minimal configuration (copy env templates)

**Backend** required for Splunk + storage:

```bash
cd backend
cp .env.example .env
```

**Frontend** required for UI + demo login:

```bash
cd frontend
cp .env.example .env.local
npm install
```

See [Minimal changes](#minimal-changes-you-must-make) below for what to edit.

### 3. Run backend (terminal 1)

```bash
cd backend
python3 run.py
```

`run.py` will:

- Use `backend/.venv` automatically when present
- **Start Docker stack** (Postgres + Qdrant + Neo4j) if `TSOC_POSTGRES_DSN` is set but services are down (compose with docker-run fallback); Neo4j is also ensured separately when missing
- Free port **9876** if another process is listening (set `TSOC_RUN_NO_KILL=1` to skip)

API: **http://127.0.0.1:9876** health: `GET /health`

### 4. Run frontend (terminal 2)

**Production (demo / LAN / after install):**

```bash
cd frontend
npm run build
npm run start
```

**Development only** (hot reload):

```bash
cd frontend
npm run dev
```

UI listens on **`0.0.0.0:3000`** (localhost and LAN).

| How you open the app | URL |
|----------------------|-----|
| On the server | http://127.0.0.1:3000/ |
| From another machine | http://\<server-ip\>:3000/ (e.g. `http://192.168.1.150:3000/`) |

**Demo login:** `admin` / `123456@a` (set in `frontend/.env.local` via `TSOC_DEMO_*`).

The browser talks only to Next.js; API calls go through **`/api/backend/*`** → FastAPI on `127.0.0.1:9876`.

---

## Minimal changes you must make

Use the **integration wizard** first (`scripts/configure-integration.sh`) — it sets Splunk, LiteLLM, MCP, runs smoke tests, and prints a masked summary of variables to edit. Below is the manual reference if you prefer editing files directly.

Only change what matches **your** hostnames, secrets, and Splunk instance. Defaults work for a local Docker Postgres + localhost Splunk.

### `backend/.env`

| Variable | Default | Change when |
|----------|---------|-------------|
| `TSOC_POSTGRES_DSN` | `postgresql://tsoc:tsoc@127.0.0.1:5432/tsoc` | Custom DB host/credentials |
| `SPLUNK_MGMT_URL` | `https://127.0.0.1:8089` | Splunk not on localhost |
| `SPLUNK_USERNAME` / `SPLUNK_PASSWORD` | empty | **Required** for Splunk REST job results |
| `TSOC_INGEST_TOKEN` | empty | You want Bearer auth on ingest routes |
| `LITELLM_MODEL` | `gpt-4o-mini` | Different model |
| `LITELLM_API_KEY` | empty | **Set for production demos** — SOC analysis uses LiteLLM + rule fallbacks on error |

Postgres credentials match `backend/docker-compose.yml` (`tsoc` / `tsoc` / db `tsoc`).

### `frontend/.env.local`

| Variable | Default | Change when |
|----------|---------|-------------|
| `AUTH_SECRET` | placeholder | **Use a long random string** in any shared/demo deployment |
| `TSOC_BACKEND_URL` | `http://127.0.0.1:9876` | Backend on another host/port |
| `TSOC_INGEST_TOKEN` | empty | Must **match** `backend/.env` if ingest token is enabled |
| `TSOC_DEV_ORIGIN` | `127.0.0.1,localhost,192.168.1.150` | Add/remove hosts you use in the browser (comma-separated) |
| `NEXT_PUBLIC_TSOC_APP_URL` | `http://192.168.1.150:3000` | Set to the **exact URL** you open in the browser |
| `NEXT_PUBLIC_TSOC_SPLUNK_HOST` / `PORT` | `127.0.0.1` / `8089` | Splunk UI hints only |

**LAN access:** ensure `TSOC_DEV_ORIGIN` and `NEXT_PUBLIC_TSOC_APP_URL` include your server IP (not only `127.0.0.1`).

Never commit `.env` or `.env.local`.

**Full reference:** [docs/11-environment-configuration.md](docs/11-environment-configuration.md) (all backend and frontend variables).  
**Wizard / smoke / Splunk MCP setup:** [docs/23-post-install-integration-wizard.md](docs/23-post-install-integration-wizard.md).

---

## Optional: Splunk app

Same app as [Splunk installation guide](#splunk-installation-guide) install path:

```text
$SPLUNK_HOME/etc/apps/ThinkingSOC_Hackathon_Splunk_App/
```

See [ThinkingSOC_Hackathon_Splunk_App/README.md](ThinkingSOC_Hackathon_Splunk_App/README.md) and [docs/02-integration-boundaries.md](docs/02-integration-boundaries.md).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Backend: `Connection refused` to Postgres | Run `python3 run.py` (auto-starts Docker stack) or `cd backend && docker compose up -d` |
| Qdrant unreachable / SOC chat no semantic search | `docker compose up -d` in `backend/`, check `curl -s http://127.0.0.1:6333/readyz` |
| `docker compose up` → `KeyError: 'ContainerConfig'` | `docker rm -f tsoc-postgres tsoc-qdrant tsoc-neo4j` then `cd backend && docker compose up -d` |
| Frontend: `EADDRINUSE` on port 3000 | `fuser -k 3000/tcp` then `npm run start` (or `scripts/start-tsoc-services.sh`) |
| UI not loading on server IP | Use production `npm run start` (binds `0.0.0.0` in `package.json`); set `TSOC_DEV_ORIGIN` + `NEXT_PUBLIC_TSOC_APP_URL` in `.env.local` |
| WebSocket `webpack-hmr` errors in browser | You are on `npm run dev`; for demo/LAN use `npm run build && npm run start` instead |
| Skip auto Docker ensure in `run.py` | `TSOC_RUN_SKIP_POSTGRES=1` and/or `TSOC_RUN_SKIP_NEO4J=1 python3 run.py` |

---

## Repository layout

| Path | Role |
|------|------|
| `backend/` | FastAPI app (`run.py`, `main.py`, agents, Splunk client) |
| `backend/devtools/` | [Developer SDK & CLI](docs/22-developer-sdk.md) typed Python client, evaluation runner |
| `frontend/` | Next.js analyst UI |
| `ThinkingSOC_Hackathon_Splunk_App/` | Minimal Splunk app (webhook, index metadata) |
| `correlation/` | Neo4j correlation graph library (API mounted on unified backend at `/api/v1/graph`) |
| `docs/` | Public architecture & structure |
| `setup_tool/` | `setup.py` implementation |
| `scripts/` | Integration wizard, Splunk MCP setup, smoke, webhooks, code graph |
| `install/modules/post_configure/` | Post-install wizard modules (Splunk, LiteLLM, MCP, smoke) |
| `submission/` | Devpost submission & evidence pack |

### Directory structure

```text
thinking-soc-splunk-hackathon/
├── backend/                          # FastAPI backend application
│   ├── api/                          #   REST API layer (routes, deps, error handlers)
│   │   └── routes/                   #   Route modules (ingest, analysis, inventory, …)
│   ├── models/                       #   Pydantic models (analysis, triage, enrichment, …)
│   ├── services/                     #   Business logic services
│   │   ├── alert/                    #     Alert classifier & pipeline
│   │   ├── inventory/                #     Asset/user/relationship resolver
│   │   ├── investigation/            #     Investigation SPL + MCP execution
│   │   ├── llm/                      #     LiteLLM wrapper & context budget
│   │   ├── observability_analysis/   #     Observability pipeline agents
│   │   ├── platform/                 #     Platform utilities (admin org, dashboard)
│   │   ├── prompts/                  #     Agent prompt templates
│   │   ├── soc_analysis/             #     Security pipeline (Hunter/Defender/Judge)
│   │   ├── soc_analysis_graph/       #     Graph-backed SOC analysis
│   │   ├── soc_rag/                  #     Qdrant RAG + Text-to-SQL chat
│   │   ├── splunk_integration/       #     Splunk REST helpers
│   │   ├── splunk_json_store/        #     Splunk KV store integration
│   │   ├── threat_intel/             #     VirusTotal IOC enrichment
│   │   └── triage/                   #     Triage priority scoring
│   ├── splunk/                       #   Splunk client, MCP, datamodel catalog
│   │   ├── client/                   #     REST client (jobs, search)
│   │   ├── datamodel/                #     CIM datamodel definitions
│   │   └── mcp/                      #     MCP + SAIA /predict integration
│   ├── devtools/                     #   SDK client & evaluation helpers
│   ├── tests/                        #   Pytest suite (75+ test modules)
│   ├── db/                           #   PostgreSQL schema (schema.sql)
│   ├── data/demo/                    #   Full pg_dump backup, JSON snapshot, CSV fallback packs
│   ├── scripts/                      #   Dev scripts (seed, enrich, predict)
│   ├── docker-compose.yml            #   Postgres + Qdrant + Neo4j compose
│   ├── config.py                     #   Env-based configuration
│   ├── main.py                       #   FastAPI app factory
│   ├── run.py                        #   Entrypoint (auto venv, docker, port)
│   └── requirements.txt
├── frontend/                         # Next.js 16 analyst UI (React 19)
│   ├── app/                          #   App Router pages
│   │   ├── (app)/                    #     Authenticated routes
│   │   │   ├── analysis/             #       Analysis list + security/ops investigation views
│   │   │   ├── correlation/          #       Findings list + Graph Explorer
│   │   │   ├── dashboard/            #       SOC dashboard
│   │   │   ├── inventory/            #       Asset & user inventory
│   │   │   ├── relationships/        #       Relationship viewer
│   │   │   ├── soc-chat/             #       RAG + SQL chat
│   │   │   ├── splunk-connection/    #       Splunk status
│   │   │   └── triage/               #       Triage queue
│   │   ├── (auth)/login/             #     Login page
│   │   └── api/                      #     Next.js API routes (auth, backend proxy)
│   ├── components/                   #   Shared React components (shadcn/ui)
│   ├── hooks/                        #   Custom React hooks
│   ├── lib/                          #   Utilities & API client
│   ├── tests/                        #   Vitest suite
│   └── package.json
├── correlation/                      # Neo4j graph library (served by backend at /api/v1/graph)
│   ├── graph_api/                    #   FastAPI routers (explorer, findings, analysis)
│   ├── graph_core/                   #   Neo4j driver, Postgres pool, sanitization
│   ├── graph_crud/                   #   Alert upsert, correlation, topology, incidents
│   ├── graph_pipelines/              #   Attack discovery, cluster merge, LLM stubs
│   ├── graph_schemas/                #   Pydantic schemas (analysis, exploration, finding)
│   ├── seed/                         #   Demo data (Cypher, SQL, fixtures)
│   └── tests/                        #   Pytest suite
├── ThinkingSOC_Hackathon_Splunk_App/          # Minimal Splunk TA
│   ├── bin/                          #   Scripted inputs / alert actions
│   ├── default/                      #   app.conf, indexes.conf, alert_actions, lookups
│   └── metadata/                     #   Splunk metadata (default.meta)
├── docs/                             # Public documentation (GitHub)
│   ├── 00-overview.md … 24-*.md      #   Architecture, design & feature docs
│   ├── architecture-views.md         #   Multi-view architecture diagrams
│   └── code-graph/                   #   Interactive code graph (graph.html)
├── setup_tool/                       # setup.py implementation modules
├── scripts/                          # Shell & Python maintenance scripts
├── submission/                       # Devpost submission materials
├── architecture_diagram.md           # Top-level Mermaid diagram
├── setup.py                          # One-command project setup
└── README.md                         # ← you are here
```

Per-folder **`README.md`** files describe local details in each major directory.

---

## Development commands

```bash
# Backend + correlation tests
cd backend && source .venv/bin/activate && pytest
python -m pytest correlation/tests/ -v

# Frontend tests
cd frontend && npm test

# Full setup log
python3 setup.py --log-file setup.log -v
```

Deeper backend/frontend notes: [backend/README.md](backend/README.md), [frontend/README.md](frontend/README.md).

---

## License

Licensed under the [Apache License, Version 2.0](LICENSE). See [NOTICE](NOTICE) for attribution.
