# Prepare SAIA prompt (pre–saia_generate_spl)

You write the **single natural-language prompt** sent to Splunk AI Assistant (`saia_generate_spl`) so it returns investigation SPL.

## Hard limits

1. **`saia_prompt` must be ≤ 1000 characters** (Splunk MCP rejects longer prompts).
2. Ask for **simple, readable SPL** that answers the investigation question (`search`, `stats`, `tstats`, etc.).
3. **Do not** ask for complex pipes: `join`, `append`, `appendcols`, `transaction`, `map`, `multisearch`, `union`.
4. Do **not** paste full JSON blobs — summarize alert fields in one short line.
5. If a CIM datamodel fits the question, name it once (e.g. `Endpoint`, `Authentication`) as a hint only.
6. Mention that the backend will convert to CIM **`| tstats`** later — focus on correct logic and alert field filters.

## Output

Return **only** JSON:

```json
{
  "saia_prompt": "string ≤1000 chars",
  "rationale": "one sentence why this wording helps SAIA"
}
```
