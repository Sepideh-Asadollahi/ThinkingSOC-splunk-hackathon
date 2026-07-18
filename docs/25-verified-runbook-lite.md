# ThinkingSOC Lite — verified incident-to-runbook compiler

ThinkingSOC Lite converts one acknowledged `soc_analysis` record into a reusable one-to-three-step investigation procedure. The model writes generalized investigation intents, never trusted SPL. ThinkingSOC Lite regenerates alert-specific SPL through the existing SAIA/LiteLLM pipeline, validates it with the Splunk parser, executes it read-only, and derives status from the returned evidence.

This implementation covers every in-scope capability in the repository-specific hackathon plan. The separate full-product LLD's microservice, queue, dedicated tables, historical cohort scorecard, semantic marketplace, revalidation worker, and IAM permission registry remain intentionally deferred because the plan explicitly forbids porting that architecture into this compact repository. The dedicated `/runbooks` settings page is the requested extension to the original no-new-route MVP boundary.

## Trust model

| Status | Meaning |
|---|---|
| `DRAFT` | Structured output exists, but parser evidence is incomplete. |
| `PARSER_VALID` | Every query parsed, but at least one step returned no source evidence. |
| `SOURCE_VERIFIED` | Every step parsed, executed without error, and returned at least one source row. |
| `APPROVED` | A human approved the latest `SOURCE_VERIFIED` draft. |
| `REUSED` | Every regenerated step returned evidence on a different compatible alert. |
| `EVIDENCE_FOUND` | A pre-approval Shadow Replay returned evidence for every regenerated step. |
| `NO_EVIDENCE` | Target execution was safe but at least one step had no evidence. |
| `FAILED` | Generation, validation, execution, or persistence failed. |

`SOURCE_VERIFIED` is deliberately narrow: it means “verified on the source investigation,” not historically or universally correct. The UI always keeps that distinction visible.

## Eligibility and safety

A build request is accepted only when the record exists, is a `soc_analysis`, has investigation questions and `search_name`, is not false-positive/benign, and its latest analyst action is `acknowledge`. PostgreSQL, the configured LLM, Splunk credentials, and investigation execution must be available.

The compiler receives a minimized snapshot: summary, verdict, triage, questions without their SPL, evidence chain, and alert fields. It does not receive raw logs, credentials, unrelated records, or analyst identity. Its strict schema forbids extra fields and the prompt forbids SPL and state-changing actions.

Generated intents use the existing `finalize_investigation_questions_for_verdict` pipeline, which supplies context-specific SPL generation, sanitization, parser validation, MCP/REST execution, refinement, and result analysis. The model cannot choose verification status or approve its own output.

### Splunk transport fallback

Runbook source verification and reuse use a deterministic **MCP → Splunk REST API** transport policy. When `TSOC_SPL_EXECUTE_VIA_MCP=true` and MCP is configured, `splunk_run_query` is attempted first. If MCP is disabled, not configured, missing the query tool, unavailable, times out, returns an execution error, or returns no rows, the same sanitized read-only SPL is executed through the authenticated Splunk management REST `oneshot_search` API. A successful MCP result is not executed again through REST.

Every `SplSearchResult` records `execution_transport` as `mcp` or `rest`. If both transports fail, the returned error retains both the MCP failure and REST API failure instead of hiding the fallback outcome. REST fallback requires `SPLUNK_MGMT_URL`, `SPLUNK_USERNAME`, and `SPLUNK_PASSWORD`; runtime readiness exposes this without returning credentials.

## API

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/v1/investigation/runbook-settings` | Read non-secret policy, feature state, and dependency readiness. |
| `GET` | `/api/v1/investigation/runbooks` | List every stored revision grouped by exact Alert Name; optional `search_name` filter. |
| `GET` | `/api/v1/investigation/runbooks/export` | Export up to 100 intent-only runbooks; optional `runbook_id` or exact `search_name` filter. |
| `POST` | `/api/v1/investigation/runbooks/import` | Import versioned portable JSON as inert drafts or attach and source-verify one runbook. |
| `PATCH` | `/api/v1/investigation/runbooks/{runbook_id}` | Save complete analyst edits as a new immutable revision. |
| `POST` | `/api/v1/investigation/records/{record_id}/runbook` | Build/rebuild and source-verify. |
| `GET` | `/api/v1/investigation/records/{record_id}/runbook` | Read latest draft, approval, and run; empty state returns `draft: null`. |
| `GET` | `/api/v1/investigation/records/{record_id}/runbook/autopilot` | Read the latest append-only Agent/Tool collaboration trace. |
| `POST` | `/api/v1/investigation/records/{record_id}/runbook/autopilot` | Run bounded assessment/advancement without automatic approval or execution. |
| `GET` | `/api/v1/investigation/records/{record_id}/runbook/compatible-targets` | Return a bounded, payload-free list of exact-`search_name` reuse candidates. |
| `POST` | `/api/v1/investigation/records/{record_id}/runbook/approval` | Approve/reject the latest source-verified draft. |
| `POST` | `/api/v1/investigation/records/{target_record_id}/runbook-runs` | Regenerate and execute an approved runbook on a compatible target. |
| `POST` | `/api/v1/investigation/records/{target_record_id}/runbook-shadow-runs` | Execute a revision read-only on a same-name, different-SID historical target without approval. |
| `POST` | `/api/v1/investigation/records/{record_id}/runbook/response-preview` | Generate an allowlisted, non-executable response recommendation for the latest eligible revision. |
| `POST` | `/api/v1/investigation/records/{record_id}/runbook/response-preview/decision` | Approve the latest preview for manual handling or reject it; never executes an action. |
| `GET` | `/api/v1/investigation/runbook-evaluations` | Aggregate persisted quality, evidence, latency, token-cost, and SOC labor-value metrics. |

Replay and reuse require a different stored `soc_analysis` record, a different non-empty Splunk SID, and exact `search_name` equality. Rebuilding or editing creates a new `runbook_id`, so an older approval cannot authorize the new draft.

## Shadow Replay and measured evaluation

Shadow Replay is the pre-approval validation lane. It accepts an attached runbook revision in any trust state, re-generates fresh target-specific SPL through the same safe pipeline, and executes it read-only against one compatible historical target. It never reads or carries approval, and it cannot convert a draft to `SOURCE_VERIFIED`; its result is an independent historical observation.

Every replay stores target/source identifiers and SIDs, deterministic status, parser-valid/successful step counts, evidence rows, execution-error count, duration, explicit manual baseline, projected minutes saved, and projected loaded-labor value. Provider exceptions are recorded as a failed Shadow artifact rather than disappearing from the scorecard.

`GET /runbook-evaluations` calculates the dashboard from append-only artifacts instead of frontend estimates. It reports revision/approval/run counts, parser-valid rate, evidence-bearing replay rate, execution errors, average compile/replay latency, measured compiler tokens, configured compiler-token cost, projected Shadow value, realized approved-reuse minutes, status distribution, and recent replay summaries.

## Safe Response Preview

Safe Response Preview is an advisory lane embedded in the Investigation page's ThinkingSOC Lite tab. It accepts only the latest attached `PARSER_VALID` or `SOURCE_VERIFIED` Runbook revision. The LLM receives the minimized, credential-scrubbed investigation snapshot, portable intent-only Runbook content, evidence basis, and a deterministic allowlist. It must return one to five strict `SafeResponseAction` objects containing target, risk, rationale, prerequisites, expected effect, rollback, and manual verification.

The durable schema deliberately contains no command, script, SPL, SQL, API request, connector invocation, or executable payload. Extra fields are rejected. A second deterministic validator blocks command-like text and any action type outside the supplied evidence policy. For `ANALYSIS_ONLY` (`PARSER_VALID`) sources, only `COLLECT_FORENSICS`, `ESCALATE_INCIDENT`, and `MONITOR_ONLY` are allowed. Disruptive options are considered only for `SOURCE_EVIDENCE` and still remain `PREVIEW_ONLY` with `requires_human_approval: true` and `execution_supported: false`.

The analyst can approve the latest preview only **for manual action**, with a required review note, or reject it. Approval records `automatic_execution_performed: false`; there is no execution route in the API or connector call in the service. A newer Runbook or Preview invalidates the earlier decision target, preventing stale approval from authorizing revised content.

## Runbook Autopilot orchestration

Runbook Autopilot turns the ThinkingSOC Lite backend into a bounded, observable agent workflow. It uses five explicit roles:

| Agent | Responsibility | Tools it may use |
|---|---|---|
| `SUPERVISOR` | Opens the objective, delegates work, and returns the next safe action. | Orchestration only. |
| `EVIDENCE_SCOUT` | Checks the stored analysis and latest analyst acknowledgment. | `storage.get_record`, `analyst_actions.list` |
| `RUNBOOK_ENGINEER` | Loads current state, finds exact-name revisions, and optionally compiles/verifies a missing revision. | `runbook.state`, `runbook.library.search`, `runbook.compile_and_verify` |
| `POLICY_GUARD` | Enforces acknowledgment, read-only boundaries, evidence gates, and human control. | Deterministic policy decisions only. |
| `RESPONSE_ADVISOR` | Creates or reuses allowlisted, non-executable response options. | `runbook.safe_response_preview` |

These names represent real bounded responsibilities in one durable orchestrator, not fictitious independent processes. Each actual handoff, tool call, tool result, policy decision, and completion is written to `RunbookAutopilotEvent` with sequence, agent, status, safe summary, tool name, duration, and bounded metadata. When compile/verification runs, the trace reports the observed `mcp` or `rest` transport from the real source results.

`ASSESS` performs read-only state discovery. `ADVANCE` may additionally compile a missing immutable revision, invoke the existing read-only Splunk verification pipeline, and create or reuse a Safe Response Preview. Autopilot never acknowledges on behalf of an analyst, approves/rejects a Runbook, launches production reuse, records response approval, or executes containment. Every session hard-codes `human_approval_required: true` and `automatic_execution_performed: false`.

The Investigation UI renders the persisted trace as scrollable rectangular events so a reviewer can distinguish Agent handoffs from Tool calls and policy gates. Provider or connector failures appear in the relevant Tool result; they do not disappear behind a generic agent status.

## Runbook-aware SOC Chat

Every ThinkingSOC Lite artifact is converted into a compact RAG document after its authoritative append-only write. This indexing is scheduled asynchronously so an unavailable vector backend cannot block Runbook persistence. `POST /api/v1/soc/rag/backfill` indexes older artifacts.

Chat supports `runbook_draft`, `runbook_approval`, `runbook_run`, `runbook_shadow_run`, `runbook_response_preview`, `runbook_response_decision`, and `runbook_autopilot` documents by default. The compact form includes intents, evidence/status metrics, decisions, safe response descriptions, and Autopilot provenance. It deliberately excludes raw Splunk rows, generated SPL, credentials, and secret-shaped alert values.

SOC Chat is instructed to cite Runbook/session identifiers and never claim that Preview approval executed containment. The **Ask about this Runbook in Chat** link opens `/soc-chat` with a source-aware question already prepared; the analyst can edit it and continue the persisted conversation normally.

After approval, the Investigation panel discovers recent compatible targets and preselects the newest candidate. The endpoint returns only record id, timestamp, SID, row index, search name, summary, and verdict; it never exposes the candidate payload. A manual record-id fallback remains available when the bounded recent scan does not find the desired target. This keeps the demo one-click while the backend still rechecks every compatibility rule at execution time.

## Alert-name library, revision editing, and exchange format

The Sidebar exposes **Runbooks → Runbook Library** at `/runbooks/library`. The library groups artifacts by exact `applicable_search_name` / Splunk `search_name` and shows every stored revision rather than hiding history behind a single latest value. Each rectangular Alert Name panel includes the scope explanation, revision count, source record, origin, deterministic verification status, human-decision state, steps, and timestamps. Search, refresh, per-revision export, per-alert export, and bounded export-all are available without leaving the page.

An edit never updates a stored artifact in place. It writes a new draft with a fresh UUID, incremented `revision`, `parent_runbook_id`, editor, note, and origin metadata. The new revision defaults to `DRAFT`; it becomes independently source-verified only when the analyst explicitly requests fresh verification against its attached, acknowledged, exact-name source record. Approval from the parent is intentionally not copied.

The exchange contract is `thinking-soc.runbook-library/v1`. Exported JSON includes only portable procedure content and provenance: title, summary, exact Alert Name, one to three intent steps, expected evidence, stop conditions, decision rule, limitations, original ids, source verdict, revision, and creation time. It excludes source results, generated SPL, raw evidence rows, tokens, credentials, approval, run state, and execution metrics.

Imported content is schema-validated with unknown fields rejected. A normal multi-runbook import creates unattached, inert `DRAFT` artifacts (`source_record_id = 0`) that cannot be approved or replayed. To establish local trust, an analyst attaches one imported runbook to a stored source with the exact same Alert Name and requests fresh parser/execution verification. Bulk attach is rejected to avoid accidentally applying one source context to multiple procedures.

## Persistence

The feature is append-only in the existing PostgreSQL `tsoc_records` table; it requires no migration:

- `verified_runbook_draft` belongs to the source alert;
- `verified_runbook_approval` belongs to the source alert;
- `verified_runbook_run` belongs to the target alert;
- `verified_runbook_shadow_run` belongs to the historical target and never carries approval;
- `verified_runbook_response_preview` belongs to the source alert and is always non-executable;
- `verified_runbook_response_decision` records manual-action approval/rejection and always records that automatic execution did not occur.
- `verified_runbook_autopilot_session` stores the bounded Agent/Tool trace and always records that automatic execution did not occur.

Stored drafts include configured/provider-reported model ids, token counts, runtime, generated SPL evidence, and deterministic status. No dedicated SQL table or migration is required.

## Sidebar and settings

The application Sidebar has **Runbooks → Runbook Library** at `/runbooks/library`, **Runbooks → Shadow & Evaluation** at `/runbooks/evaluation`, and **Runbooks → ThinkingSOC Lite** at `/runbooks`. All follow the existing NeonGlass Prism system and restrained teal/slate palette, with black surfaces, shared cards and controls, responsive layouts, explicit states, and accessible labels.

Runbook operational settings are persisted through the existing integration-settings store and immediately applied to new operations:

| Setting | Default | Constraint |
|---|---:|---|
| `TSOC_RUNBOOK_ENABLED` | `true` | Disabling blocks compile, approval, and reuse while existing artifacts remain readable. |
| `TSOC_RUNBOOK_MAX_STEPS` | `3` | `1..3`; model output above the configured limit is rejected. |
| `TSOC_RUNBOOK_DEFAULT_MANUAL_MINUTES` | `25` | `5..120`; visible baseline, never an LLM estimate. |
| `TSOC_RUNBOOK_ARTIFACT_SCAN_LIMIT` | `500` | `50..1000` records per append-only artifact type. |
| `TSOC_RUNBOOK_ANALYST_HOURLY_COST_USD` | `65` | Explicit loaded hourly rate used only for projected Shadow value. |
| `TSOC_RUNBOOK_INPUT_COST_PER_1M_TOKENS` | `0` | Compiler input-token rate; keep zero for free models. |
| `TSOC_RUNBOOK_OUTPUT_COST_PER_1M_TOKENS` | `0` | Compiler output-token rate; keep zero for free models. |
| `TSOC_RUNBOOK_AUTOPILOT_ENABLED` | `true` | Enables bounded assessment/compile/verify/preview orchestration without weakening fixed human gates. |

Acknowledgment, evidence on every source step, exact `search_name` reuse, read-only SPL execution, and human approval are fixed trust policies and cannot be disabled from the UI.

The internal storage query accepts the documented 1,000-record maximum. The public generic storage API remains independently capped at 500 records per request.

## Execution graph visualization

The investigation panel renders the complete ThinkingSOC Lite path as a modern rectangular-node graph:

```text
source investigation → verified steps → human decision gate → exact-match reuse target
```

Each node contains a short operational description and deterministic status. Selecting a node—by pointer, touch, or keyboard—shows its full intent, expected evidence, stop condition, decision rule, or reuse measurements below the graph. Hover and keyboard focus add a restrained elevation and soft teal, violet, emerald, or slate emphasis; selection remains persistent so required information never depends on hover alone.

Display safeguards are implemented in [`frontend/components/structured-data/runbook-flow-graph.tsx`](../frontend/components/structured-data/runbook-flow-graph.tsx):

- rectangular cards use `min-w-0`, wrapping, and bounded summaries to prevent long model text from breaking the panel;
- narrow and medium viewports use a vertical path, while wide viewports use a horizontal path;
- a six-node path has a minimum canvas width inside a horizontal overflow viewport instead of compressing text to unreadable widths;
- connectors rotate with the layout and remain decorative to assistive technology;
- every node is a native button with an accessible name and `aria-pressed` selection state;
- motion is disabled when the operating system requests reduced motion;
- the detail region uses `aria-live="polite"` and does not expose source alert payloads.

Graph behavior, selection, approved/reused states, and overflow-safe layout contracts are covered by [`runbook-flow-graph.test.tsx`](../frontend/components/structured-data/runbook-flow-graph.test.tsx).

## Configuration and governance

Use the existing `TSOC_POSTGRES_DSN`, Splunk credentials, `TSOC_EXECUTE_INVESTIGATION_SPL`, `LITELLM_MODEL`, and provider credential/base URL settings. The submission must configure `LITELLM_MODEL` to the GPT-5.6 identifier actually exposed to the entrant account; source code intentionally does not guess or hardcode that identifier.

Runtime readiness is shown without exposing credentials. Compilation records generation and source-verification duration separately, parser-valid/successful step counts, and total evidence rows. Reuse records runtime, successful steps, evidence rows, minutes saved, and savings percentage.

The ThinkingSOC Lite settings page labels the active connectivity policy as **MCP preferred · REST API fallback** when both are configured, or **REST API fallback ready** when MCP is unavailable but Splunk REST credentials are ready.

Runtime cloud-model use is also subject to the repository's no-cloud-exfiltration policy. Synthetic data does not silently waive that policy. The project owner must explicitly authorize the provider and data flow before enabling runtime GPT-5.6.

## Backend lifecycle logs

Every Runbook operation emits bounded, single-line backend logs with the stable prefix `runbook_event=`. The logs contain operational metadata only: request/record/runbook identifiers, phase, deterministic status, step and evidence counts, model/token metadata, durations, revision, persistence outcome, and reuse savings. Alert payloads, generated SPL, evidence rows, analyst notes, API keys, passwords, tokens, and cookies are never logged by this layer.

Follow all Runbook activity on a systemd installation:

```bash
sudo journalctl -u tsoc-backend -f | rg 'runbook_event='
```

For a manually started backend, filter the uvicorn console output:

```bash
backend/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 9876 2>&1 \
  | rg --line-buffered 'runbook_event='
```

Useful event families:

| Event family | Recorded lifecycle |
|---|---|
| `api.*` | HTTP request id, requested operation, success/failure, total API duration. |
| `compile.*` | Source eligibility, LLM generation, token usage, source SPL verification, final status. |
| `artifact.*` | Storage scan diagnostics, schema-invalid skipped artifacts, persistence start/success/failure. |
| `library.*`, `export.*` | Applied filter, alert/runbook counts, export count and duration. |
| `import.*`, `revision.*` | Item/revision identity, optional source verification, result metrics and duration. |
| `approval.*` | Source/runbook identity, human decision and persistence completion; note text is excluded. |
| `response_preview.*` | Generation start/failure/success, evidence basis, action count, model duration, and the false execution capability flag. |
| `response_decision.*` | Preview identity, manual-action approval/rejection, persistence, and the false automatic-execution flag; note text is excluded. |
| `autopilot.*`, `api.autopilot_*` | Session/source identity, Agent/Tool counts, final gate status, duration, and the false automatic-execution flag. |
| `compatible_targets.*` | Exact-name candidate scan limit, match count and duration. |
| `reuse.*` | Source/target ids, execution phase, deterministic status, evidence totals and savings. |
| `shadow.*`, `evaluation.*` | Historical target/SID boundaries, replay outcome, errors, measured evidence, latency, projected value, and aggregate rates. |

Known domain failures and provider failures are logged as warnings without redundant tracebacks. Unexpected exceptions retain their traceback at the API boundary. The ordinary HTTP middleware log shares the API `rid`, allowing one request to be correlated with its `api.*` Runbook events.

## Evidence pack

With two acknowledged/synthetic stored alerts sharing a `search_name`:

```bash
python submission/generate_evidence_pack.py \
  --lite-source-record-id 582 \
  --lite-target-record-id 583 \
  --lite-manual-minutes 25
```

The generator captures live outputs as `07_lite_source_record.json` through `11_lite_metrics.json`. Failures remain in the artifacts; the generator never hand-edits a passing result.

## Related public documents

- [Hackathon product and demo guide](./26-hackathon-lite-product-guide.md)
- [U.S. SOC capacity and economic impact](./27-lite-us-soc-economic-impact.md)
- [Submission evidence guide](../submission/README.md)
- [Hackathon change log](../HACKATHON_CHANGELOG.md)
