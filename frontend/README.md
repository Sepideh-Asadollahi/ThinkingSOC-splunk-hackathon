# ThinkingSOC Lite Frontend (Hackathon)

External analyst UI for the hackathon demo, built around Splunk: NeonGlass theme, [Animate UI](https://animate-ui.com/) components, and FastAPI backend proxy.

## Prerequisites

- Node.js 20+
- Backend running at `http://127.0.0.1:9876` (see `backend/README.md`)
- PostgreSQL configured on the backend for inventory and stored analysis (`TSOC_POSTGRES_DSN`)
- Matching `TSOC_INGEST_TOKEN` on backend and frontend (if ingest protection is enabled)

## Setup

```bash
cd frontend
cp .env.example .env.local
npm install
npm run build
npm run start
```

After `install.sh`, the stack uses **production** mode (`npm run start`), not `npm run dev`. Use `npm run dev` only for local UI development with hot reload.

Open the app at the host root only (no path required):

- Local: [http://localhost:3000/](http://localhost:3000/)
- LAN / DNS: `http://<server-ip-or-dns>/` (frontend listens on `0.0.0.0:3000`)

Unauthenticated visits redirect to `/login`; signed-in users go to `/dashboard`.

**Demo login:** `admin` / `123456@a`

## Silent 1080p demo recording

The Playwright recorder signs in outside the recorded browser context, then captures only the
product UI at exactly `1920×1080`. It adds restrained English lower-thirds, a visible cursor,
natural scrolling, and explicit Autopilot agent/handoff context without changing product pages or
executing response actions. First produce the short ThinkingSOC Lite agent-trace quality check:

```bash
npx playwright install chromium
npm run record:devpost:sample
```

If the preview is readable, record the complete Analysis → ThinkingSOC Lite agents/graph → Library details →
Shadow Evaluation → Chat → Dashboard tour:

```bash
npm run record:devpost
```

Artifacts are written under `../artifacts/devpost-recording/`. Every run keeps the original silent
1080p WebM and, when an FFmpeg build with `libx265` is available, also produces a compact HEVC MP4
with `hvc1`, `yuv420p`, and fast-start metadata. Useful overrides:

```bash
TSOC_UI_URL=http://192.168.1.150:3000 \
TSOC_DEMO_RECORD_ID=395 \
TSOC_X265_CRF=24 \
TSOC_TRIM_START=3 \
npm run record:devpost
```

Use a lower `TSOC_X265_CRF` for larger/higher-quality output or a higher value for a smaller file.
Credentials can be overridden with `TSOC_DEMO_USER` and `TSOC_DEMO_PASSWORD`; they are never written
to the recording artifacts.

## Pages

| Route | Purpose |
|-------|---------|
| `/login` | Demo authentication |
| `/dashboard` | SOC overview — KPIs, pipeline activity, platform health |
| `/soc-chat` | SOC analyst chat (vector RAG + Text-to-SQL) |
| `/analysis` | Triage queue + stored SOC/Ops events (`/triage` redirects here) |
| `/analysis/investigation/[id]` | Security investigation, ThinkingSOC Lite Runbook execution graph, recommended action, hunter & defender, enrichment, and **Admin question** tab when an org gap is suggested |
| `/analysis/ops-investigation/[id]` | Observability investigation detail |
| `/correlation` | Graph correlation findings list |
| `/correlation/explorer` | Neo4j graph explorer (topology / attack tree) |
| `/inventory` | Users & assets CRUD |
| `/relationships` | User–asset relationship map for enrichment |
| `/runbooks` | ThinkingSOC Lite settings, dependency readiness, and fixed trust policies |
| `/runbooks/library` | Every immutable Runbook revision grouped by exact Alert Name, with search, complete editing, and portable JSON Import/Export |
| `/runbooks/evaluation` | Same-alert/different-SID Shadow Replay, evidence coverage, latency, and measured reuse outcomes |
| `/splunk-connection` | LiteLLM, Splunk REST, MCP, integration settings |

## Architecture

- **Auth:** HttpOnly `tsoc_session` cookie; credentials validated server-side only.
- **API:** Browser calls `/api/backend/*`; Next.js forwards to FastAPI with `Authorization: Bearer $TSOC_INGEST_TOKEN` (never sent to the client).
- **ThinkingSOC Lite graph:** Rectangular source/step/gate/reuse nodes stack vertically below `xl`, switch to a horizontal path on wide screens, preserve long-text wrapping, and expose persistent keyboard/touch-selectable details.
- **Runbook library:** Restrained teal/slate Alert Name panels show every revision, trust state, source, human gate, and step intent. Edits create new revisions; portable JSON excludes evidence and approval, and imports remain inert until locally attached and verified.
- **Splunk execution policy:** ThinkingSOC Lite displays `MCP preferred · REST API fallback`; when MCP is absent or fails, sanitized read-only SPL is executed through authenticated Splunk REST oneshot search.

## Build

Same as production run (`package.json` maps `start` → `next start -H 0.0.0.0 -p 3000`):

```bash
npm run build
npm run start
```
