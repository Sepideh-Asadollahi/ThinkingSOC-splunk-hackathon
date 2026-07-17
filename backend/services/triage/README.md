# Triage Service

Post-analysis triage and priority scoring. Computes investigation priority from Judge/Ops verdicts, enrichment data, and classification results. Provides the shared triage queue for the Analysis page UI.

## Key files

| File | Description |
|------|-------------|
| `triage_priority.py` | Scoring engine — computes triage priority from analysis outputs and verdicts |
| `triage_queue.py` | Shared Analysis page queue with pipeline/status filtering |

## Related docs

- [Triage & Priority Layer](../../../docs/08-triage-priority-layer.md)
