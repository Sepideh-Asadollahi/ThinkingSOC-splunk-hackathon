# Submission / Evidence Pack

Scripts to generate **local** evidence artifacts for hackathon demos and review. Generated output is **gitignored** under `submission/evidence/`.

**Public submission documentation:** [`docs/README.md`](../docs/README.md)  
**Hackathon product and evidence guide:** [`docs/26-hackathon-forge-product-guide.md`](../docs/26-hackathon-forge-product-guide.md)

**Forge U.S. SOC impact model:** [`docs/27-forge-us-soc-economic-impact.md`](../docs/27-forge-us-soc-economic-impact.md)

## Generate evidence pack

```bash
bash submission/build_evidence_pack.sh
```

Prerequisites: backend at `http://127.0.0.1:9876`, optional `TSOC_INGEST_TOKEN`.

To capture the complete Forge workflow, use two different acknowledged/synthetic
`soc_analysis` records with the same `search_name`:

```bash
python submission/generate_evidence_pack.py \
  --forge-source-record-id 582 \
  --forge-target-record-id 583 \
  --forge-manual-minutes 25
```

## Output (per run)

- `submission/evidence/<run_id>/00_evidence_summary.md`
- `01_classification_response.json` … `06_mcp_status.json`
- `07_forge_source_record.json` … `11_forge_metrics.json`
- `05_eval_report.json`, `manifest.json`

## Hackathon submission artifacts (not in this folder)

- [`architecture_diagram.md`](../architecture_diagram.md) (repo root)
- [`docs/`](../docs/README.md)
- [`LICENSE`](../LICENSE) at repo root

Keep the public hackathon narrative and evidence instructions in the repository documentation linked above.
