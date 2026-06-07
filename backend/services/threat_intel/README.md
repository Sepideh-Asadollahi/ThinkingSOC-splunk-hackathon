# Threat Intel Service

Threat intelligence enrichment via VirusTotal API v3. Looks up IOCs (IPs, domains, URLs, file hashes) extracted from alerts and produces compact analyst-friendly summaries for LLM context and API responses.

## Key files

| File | Description |
|------|-------------|
| `virustotal.py` | VirusTotal API v3 IOC enrichment (IP, domain, URL, file hash lookups) |
| `virustotal_schema.py` | VirusTotal API v3 response shapes and summary builder |
| `threat_intel_compact.py` | Compact threat-intel payloads for SOC analysis LLM context |

## Related docs

- [VirusTotal Threat Intel](../../../docs/09-virustotal-threat-intel.md)
