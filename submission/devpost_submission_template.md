# Devpost Submission Template (Ready to Fill)

## Project Name

ThinkingSOC Agentic Ops Router

## Track

**Security** (Devpost form)

## What it does

Our project receives Splunk alerts via Webhook, enriches by `sid` using Splunk REST, classifies each alert into Security or Observability, runs the corresponding analysis pipeline, and returns actionable next steps plus analyst-ready SPL suggestions.

Core capabilities:

- Auto routing (`security`, `observability`, `dual`, `manual_review`)
- Security pipeline: Defender + Hunter + Judge
- Observability pipeline: Diagnoser + Responder + Ops Judge
- Agent triage endpoint with next actions
- Splunk-native SPL via **REST `/predict`** (UI path) + **MCP `splunk_run_query`** execute (All Time); LiteLLM fallback
- MCP metadata enrichment on triage (`mcp_context`, `mcp_used`)
- PostgreSQL evidence storage
- Developer SDK + CLI for integration

## How we built it

- Backend: FastAPI (Python)
- AI orchestration: LiteLLM + LangGraph + **Splunk MCP Server** (app 7931)
- Data source: Splunk alert webhook + Splunk REST job results + MCP tools (`splunk_*`, `saia_*`)
- Storage: PostgreSQL
- Devtools: typed SDK (sync/async), CLI, evaluation runner

## Challenges we ran into

- Handling row-wise webhook payloads with shared `sid`
- Unifying Security and Observability into one route contract
- Producing deterministic fallback behavior when LLM is disabled/unavailable
- Keeping outputs consistently structured for automation and scoring

## Accomplishments that we're proud of

- End-to-end agentic alert triage flow
- Clear split between Security and Observability reasoning
- Actionable operator outputs (next actions + SPL)
- Submission-ready evidence pack generation with scoring report

## What we learned

- Agent pipelines need strong contracts and deterministic fallbacks
- Scoring and evaluation artifacts improve trust and judging clarity
- Developer experience (SDK/CLI/examples) significantly reduces integration friction

## What's next

- Frontend analyst workstation for triage workflow
- Expanded scenario matrix and benchmark suite
- Deeper MCP orchestration (multi-step agent tool loops)

## Repository and setup

- Repository: `<your_repo_url>`
- Setup instructions: `README.md`
- Architecture: `architecture_diagram.md` (repo root)
- Structure docs: `docs/` — see `docs/README.md`
- Devpost checklist (local): `project-engineering/github-extras/07-devpost-submission.md`

## Demo video

- Video URL: `<youtube_or_vimeo_url>`

## Evidence artifacts

Attach outputs from:

- `submission/evidence/<run_id>/00_evidence_summary.md`
- `submission/evidence/<run_id>/05_eval_report.json`
- `submission/evidence/<run_id>/manifest.json`
- `submission/evidence/<run_id>/06_mcp_status.json`

## Splunk MCP (bonus / Grand narrative)

- Install Splunkbase app **7931**, configure MCP bearer token (`audience=mcp`)
- Demo: `GET /api/v1/mcp/status` → `POST /api/v1/agents/triage` with `mcp_used: true` → SPL `source: splunk_mcp_saia`
- Docs: `docs/02-platform/11-splunk-mcp-integration.md`

