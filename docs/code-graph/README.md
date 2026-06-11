# Code graph

Structural map of the repository: functions, classes, call relationships, and **communities** (tightly coupled code regions).

| File | Purpose |
|------|---------|
| [graph.html](graph.html) | Interactive graph — open in a web browser |
| [communities/](communities/index.md) | One page per community: members, flows, dependencies |
| [graph-status.txt](graph-status.txt) | Node/edge counts and languages at last export |

Generated with [code-review-graph](https://github.com/tirth8205/code-review-graph). Summary: [05-codebase-map.md](../05-codebase-map.md).

**Regenerate after large refactors:**

```bash
bash scripts/build-code-graph.sh
```

**Stale paths:** Some `communities/*.md` pages may list old flat module paths (e.g. `services/enrichment_resolver.py` instead of `services/alert/enrichment_resolver.py`) or removed modules. **`docs/*.md` and `backend/**/README.md` are authoritative.** `services-row.md` was manually corrected; use [graph.html](graph.html) or MCP `semantic_search_nodes` for live symbols.
