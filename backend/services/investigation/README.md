# Investigation Service

Investigation workflow for SOC analysis. Generates investigation SPL queries, executes them against Splunk (via MCP or REST), reviews results with LLM and SAIA, and manages analyst timeline actions.

## Key files

| File | Description |
|------|-------------|
| `investigation_workflow.py` | Investigation timeline and analyst human-in-the-loop actions |
| `investigation_questions_spl.py` | Normalizes investigation questions and generates per-question SPL |
| `investigation_question_context.py` | Alert field context and post-processing for investigation questions |
| `investigation_spl_execute.py` | Executes investigation SPL on Splunk (MCP or REST oneshot) |
| `spl_predict_pipeline.py` | SAIA REST `/predict` + MCP `splunk_run_query` shared execution |
| `spl_syntax_sanitize.py` | **Generic** SPL syntax cleanup (backticks, colon quoting, dedupe) — no domain hardcoding |
| `spl_tstats_sanitize.py` | `sanitize_spl_draft()` facade; delegates to `spl_syntax_sanitize` |
| `spl_mcp_review.py` | LLM refine on parser/execute errors; injects live Splunk catalog from MCP |
| `../../splunk/saia_config_repair.py` | SAIA KV/conf auto-repair (startup + predict retry) |
| `spl_saia_analysis.py` | SAIA MCP explain/optimize review for drafted SPL |
| `spl_results_analysis.py` | LLM analysis of executed investigation SPL result batches |
| `saia_prompt_prepare.py` | Crafts concise SAIA `saia_generate_spl` prompts via LiteLLM |
| `verified_runbook.py` | Runbook compile, verify, approval, import/export, revision, reuse, persistence, and `runbook_event=` lifecycle logs |

## SPL quality pipeline (summary)

1. **Generate** — REST `/predict`, LiteLLM, or rule-based `search`.
2. **Syntax sanitize** — `sanitize_spl_syntax()` fixes mechanical LLM output issues.
3. **Parse** — Splunk `parse_spl` (parse_only); on error → LiteLLM refine with parser message + MCP catalog.
4. **Execute** — deterministic syntax repair + MCP `splunk_run_query` (All Time); on error / 0 rows → LiteLLM execution refine (max 3).

Full design: [docs/13-cim-investigation-spl-mcp.md](../../../docs/13-cim-investigation-spl-mcp.md) — section **SPL syntax sanitize + parser-driven refine**.

Runbook logs can be followed with `journalctl -u tsoc-backend -f | rg 'runbook_event='`. See [Verified Runbook Forge — Backend lifecycle logs](../../../docs/25-verified-runbook-forge.md#backend-lifecycle-logs) for the event families and redaction contract.

## Related docs

- [CIM Investigation SPL MCP](../../../docs/13-cim-investigation-spl-mcp.md)
- [Investigation Workflow](../../../docs/20-investigation-workflow.md)
