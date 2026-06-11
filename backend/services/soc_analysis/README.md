# backend/services/soc_analysis

Parent: [README.md](../README.md)

Security pipeline orchestration: assembles Defender / Hunter / Judge outputs, risk scoring, MITRE-style framework mapping, and admin-org GAP hooks. LangGraph node implementations live in [`soc_analysis_graph/`](../soc_analysis_graph/).

## Key files

| File | Role |
|------|------|
| `runner.py` | Main SOC analysis entry (enrichment → LangGraph → persist) |
| `assembly.py` | Builds final `SocAnalysisResult` from graph state |
| `soc_analysis_batch.py` | Per-row batch analysis for multi-row Splunk jobs |
| `soc_analysis_risk.py` | Risk engine scoring from inventory context |
| `framework_mapping.py` | MITRE-style technique mapping |
| `soc_verdict.py` | Judge verdict normalization |
| `admin_org_gap.py` | Post-Judge organizational GAP question attach |
| `fallback_result.py` / `fallback_questions.py` | Rule-based fallbacks when LiteLLM is unavailable |

## See also

- [04-agents-and-pipelines.md](../../../docs/04-agents-and-pipelines.md)
- [soc_analysis_graph/README.md](../soc_analysis_graph/README.md)
