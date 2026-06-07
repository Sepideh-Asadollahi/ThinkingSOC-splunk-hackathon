# tools

Developer and debugging tools that are **not** part of the ThinkingSOC backend.

## Key files

| Path | Purpose |
|------|---------|
| `saia-debug/` | Standalone Splunk AI Assistant debugger — compares UI `/predict` vs MCP `generatespl` vs direct cloud API |
| `saia-debug/debug_saia_paths.py` | Probe script (requires `httpx`, no backend imports) |
| `saia-debug/README.md` | Setup, usage, and common-cause summary for SAIA path mismatches |
