# Submission / Evidence Pack

Scripts to generate **local** evidence artifacts for demos and judging. Generated output is **gitignored** under `submission/evidence/`.

**Public submission documentation:** [`docs/README.md`](../docs/README.md)  
**Devpost checklist:** [`project-engineering/github-extras/07-devpost-submission.md`](../project-engineering/github-extras/07-devpost-submission.md) (local)  
**Judging mapping:** [`project-engineering/github-extras/08-judging-evidence.md`](../project-engineering/github-extras/08-judging-evidence.md) (local)

## Generate evidence pack

```bash
bash submission/build_evidence_pack.sh
```

Prerequisites: backend at `http://127.0.0.1:9876`, optional `TSOC_INGEST_TOKEN`.

## Output (per run)

- `submission/evidence/<run_id>/00_evidence_summary.md`
- `01_classification_response.json` … `06_mcp_status.json`
- `05_eval_report.json`, `manifest.json`

## Devpost-required repo artifacts (not in this folder)

- [`architecture_diagram.md`](../architecture_diagram.md) (repo root)
- [`docs/`](../docs/README.md)
- [`LICENSE`](../LICENSE) at repo root

Hackathon copy: `project-engineering/github-extras/07-devpost-submission.md`. Optional: `submission/devpost_submission_template.md`.
