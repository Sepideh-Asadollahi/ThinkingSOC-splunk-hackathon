# Devpost Submission Template (Ready to Fill)

## Project Name

ThinkingSOC Lite — Verified Incident-to-Runbook Compiler

## Track

**Hackathon track:** Work & Productivity

## What it does

ThinkingSOC Lite turns one acknowledged SOC investigation into a reusable, executable investigation procedure. GPT-5.6 compiles accepted evidence and questions into one to three generalized intents. ThinkingSOC Lite then generates fresh read-only SPL, validates and executes every step on Splunk, shows the evidence, requires human approval, and can rerun the approved runbook on a different stored alert with the same detection name.

Core capabilities:

- Strict GPT-5.6 structured compilation that emits intents, never trusted SPL
- Deterministic `PARSER_VALID`, `SOURCE_VERIFIED`, `REUSED`, `NO_EVIDENCE`, and `FAILED` status
- Existing SAIA/LiteLLM generation, sanitizer, Splunk parser, MCP/REST execution, and refinement path
- Separate analyst acknowledgment and runbook approval gates
- Exact-`search_name` reuse with target-specific SPL and evidence
- Append-only PostgreSQL audit artifacts and observed time-saved metrics
- One integrated ThinkingSOC Lite panel in the existing Security Investigation workflow

## How we built it

- Backend: FastAPI (Python)
- AI orchestration: GPT-5.6 through the existing LiteLLM gateway; LangGraph remains part of the baseline SOC analysis
- Data source: Splunk alert webhook + Splunk REST job results + MCP tools (`splunk_*`, `saia_*`)
- Storage: PostgreSQL
- Devtools: typed SDK, focused backend/frontend tests, and live evidence-pack generator
- Development: Codex implemented and tested the new vertical slice; humans selected the scope, verification semantics, safety gates, and demo evidence

## Challenges we ran into

- Generalizing one incident without leaking source-specific entities into durable runbook intent
- Keeping “verified” honest: one source execution is useful evidence, not universal proof
- Reusing the existing SPL pipeline without creating a second compiler or unsafe execution path
- Invalidating stale approvals whenever a new immutable draft is compiled

## Accomplishments that we're proud of

- One coherent acknowledge → compile → verify → approve → reuse workflow
- Model output cannot choose its own status or approval
- Every target run regenerates and revalidates SPL against current alert context
- Live artifacts record model metadata, parser/execution results, runtime, and time saved

## Potential impact and measurable economics

ThinkingSOC Lite measures runtime and keeps the analyst-entered manual baseline visible, so a buyer can calculate value from local alert volume rather than an unsupported industry-wide savings percentage.

An illustrative six-analyst U.S. private-sector SOC case uses official BLS wage and benefit inputs plus explicit operational assumptions. At 30 approved compatible repeats per business day, a measured reduction from 25 to 5 minutes would return 2,600 analyst hours/year (1.25 FTE of capacity) and about $223,000/year in gross capacity value. The eligible repeat lane would be five times faster. These are scenario outputs, not claimed customer results; live evidence-pack timings, local ticket baselines, failure/rework rates, and actual operating cost must replace the assumptions.

Full sources, formulas, sensitivity, break-even, and cash-vs-capacity treatment: `docs/27-lite-us-soc-economic-impact.md`.

## What we learned

- Structured AI becomes operationally useful when deterministic evidence gates surround it
- Reusable intent is safer than persisting source-specific generated queries
- Honest status labels and visible failures build more trust than a single opaque AI score

## What's next

- Historical replay over a labeled cohort and a quality scorecard
- Semantic matching only after an approved runbook corpus exists
- Version history, drift detection, and revalidation without rewriting audit history

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
- `submission/evidence/<run_id>/07_lite_source_record.json`
- `submission/evidence/<run_id>/08_lite_compile.json`
- `submission/evidence/<run_id>/09_lite_approval.json`
- `submission/evidence/<run_id>/10_lite_target_run.json`
- `submission/evidence/<run_id>/11_lite_metrics.json`

## Runtime integrations

- Install Splunkbase app **7931**, configure MCP bearer token (`audience=mcp`)
- Demo: acknowledge a stored source record → build and approve ThinkingSOC Lite runbook → execute on an exact-match target
- Docs: `docs/25-verified-runbook-lite.md` and `docs/15-splunk-mcp-integration.md`
- Product/demo narrative: `docs/26-hackathon-lite-product-guide.md`
- U.S. SOC impact model: `docs/27-lite-us-soc-economic-impact.md`
