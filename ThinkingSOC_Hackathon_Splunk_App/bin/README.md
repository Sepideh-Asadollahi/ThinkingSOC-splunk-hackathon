# ThinkingSOC_Hackathon_Splunk_App/bin

Parent: [README.md](../README.md)

## `thinkingsoc_hackathon.py`

Splunk modular alert action (`--execute`). Reads JSON settings from stdin, builds webhook body, `POST` to configured backend URL.

### Splunk-provided settings (stdin)

Typical keys: `sid`, `search_name`, `result`, `results_file`, `results_link`, `app`, `owner`, `configuration` (includes `url`, optional `auth_token`).

`results_file` points at `{dispatch_dir}/results.csv.gz` — **gzip-compressed CSV**, not plain text.

### Row collection

1. If `results_file` exists → `gzip.open` + `csv.DictReader` → all rows.
2. Else → single `result` dict from Splunk.

When 2+ rows: body includes `result` (first row) and `results` (full array).

### Outbound webhook

```json
{
  "sid": "scheduler__…",
  "search_name": "New TesT",
  "result": { … },
  "results": [ { … }, { … } ]
}
```

Stderr logs a one-line summary (`rows=N`, `bytes=…`) — avoid multi-line JSON on stderr (Splunk marks continuation lines as ERROR).

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | POST succeeded (HTTP 2xx) |
| 2 | HTTP error from backend |
| 3 | Unexpected error (e.g. corrupt results file) |
