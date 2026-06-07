# scripts/samples

Sample Splunk webhook alert payloads used for development and demo seeding.

## Key files

| File | Purpose |
|------|---------|
| `splunk-webhook-example.json` | Generic brute-force alert payload (`src_ip`, `domain` for VT demo) |
| `splunk-webhook-botsv1-osk-sysmon.json` | BOTSv1 osk.exe Sysmon alert (MITRE T1218); includes `domain: pastebin.com` for VirusTotal lookup |
| `splunk-webhook-observability-cpu-latency.json` | Observability scenario: CPU spike + latency on `payment-api` / `web-prod-01` |

Each file mirrors the JSON body Splunk sends to `POST /api/v1/alerts/splunk-ingest`.

## Related docs

- [docs/02-integration-boundaries.md](../../docs/02-integration-boundaries.md)
- [docs/09-virustotal-threat-intel.md](../../docs/09-virustotal-threat-intel.md) — which alert fields are sent to VirusTotal (§4)
