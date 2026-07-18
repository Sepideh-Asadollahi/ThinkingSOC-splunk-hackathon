# Hackathon change log

## Baseline

- Inspected baseline: commit `8b31a69` (`2026-06-13`, `chore: sync local code changes`).
- Pre-existing capabilities: alert ingest, routing, SOC/observability analysis, investigation questions, SPL generation/validation/execution, PostgreSQL JSON storage, analyst acknowledgment, and the Investigation UI.

## Added for the hackathon — ThinkingSOC Lite

- Strict verified-runbook Pydantic contracts and an intent-only compilation prompt.
- Source eligibility and minimized evidence snapshot rules.
- GPT/LiteLLM compilation with configured/provider model and token metadata.
- Deterministic source verification through the existing SPL pipeline.
- Append-only draft, approval, and reuse artifacts in `tsoc_records`.
- Authenticated build/read/approval/reuse Investigation APIs.
- Exact-detection target compatibility, stale-approval protection, and measured time savings.
- Payload-free compatible-target discovery with newest-candidate preselection and a manual-ID fallback for guided reuse.
- ThinkingSOC Lite panel in the Security Investigation Overview with evidence, errors, approval, reuse, and honest status labels.
- Dedicated Runbooks Sidebar section and NeonGlass ThinkingSOC Lite Settings page with feature flag, step cap, manual baseline, artifact limit, dependency readiness, and fixed trust-policy display.
- Alert-name Runbook Library Sidebar page with all immutable revisions, complete analyst editing, exact-name filtering, and safe per-runbook/per-alert/all JSON export plus schema-validated import.
- Portable `thinking-soc.runbook-library/v1` exchange contract that excludes evidence and approvals; imported procedures remain inert until explicitly attached and freshly source-verified.
- Observable MCP-to-Splunk-REST execution fallback with per-result transport provenance and combined failure diagnostics.
- Separate generation/verification metrics, evidence counters, target link, and measured savings percentage.
- Shadow Replay and Evaluation Dashboard for same-name, different-SID historical validation, technical quality, latency, token cost, and projected labor value.
- Safe Response Preview with evidence-sensitive action allowlists, command-text blocking, explicit rollback/verification, append-only manual approval, and no execution endpoint.
- Bounded Runbook Autopilot orchestration across Supervisor, Evidence Scout, Runbook Engineer, Policy Guard, and Response Advisor, with durable real Tool-call/handoff traces and hard-coded human/zero-auto-execution gates.
- Runbook-aware SOC Chat indexing for revisions, approvals, reuse/shadow results, response previews/decisions, and Autopilot traces, plus Investigation-to-Chat contextual handoff.
- Sync and async SDK parity plus non-secret runtime-settings API.
- SDK methods, live submission evidence capture, backend unit/API tests, and frontend component/API tests.
- Corrected the internal storage query cap so the documented ThinkingSOC Lite artifact scan range (`50..1000`) is effective.
- Reframed the root README around the hackathon ThinkingSOC Lite delta and added public product/demo plus U.S. SOC economic-impact documents with sourced, reproducible capacity and ROI formulas.

The feature does not add a service, database migration, worker, marketplace, semantic matcher, automatic containment action, or Splunk write operation. Response recommendations remain preview-only and any approval is for manual action under the organization's existing process.
