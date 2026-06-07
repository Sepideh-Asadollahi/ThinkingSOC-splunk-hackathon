# investigation-spl

## Overview

Community of 16 nodes

- **Size**: 16 nodes
- **Cohesion**: 0.1849
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| strip_time_range_from_spl | Function | backend/services/investigation/spl_syntax_sanitize.py | 41-48 |
| strip_spl_backticks | Function | backend/services/investigation/spl_syntax_sanitize.py | 51-53 |
| quote_spl_colon_field_values | Function | backend/services/investigation/spl_syntax_sanitize.py | 56-65 |
| dedupe_search_field_clauses | Function | backend/services/investigation/spl_syntax_sanitize.py | 68-98 |
| strip_redundant_boolean_and | Function | backend/services/investigation/spl_syntax_sanitize.py | 101-103 |
| _safe_spl_alias | Function | backend/services/investigation/spl_syntax_sanitize.py | 106-110 |
| ensure_search_generating_command | Function | backend/services/investigation/spl_syntax_sanitize.py | 113-124 |
| fix_field_equals_in_pipe_clauses | Function | backend/services/investigation/spl_syntax_sanitize.py | 127-170 |
| fix_spl_quoted_string_escapes | Function | backend/services/investigation/spl_syntax_sanitize.py | 173-224 |
| discourage_values_aggregation | Function | backend/services/investigation/spl_syntax_sanitize.py | 227-238 |
| sanitize_spl_syntax | Function | backend/services/investigation/spl_syntax_sanitize.py | 241-255 |
| test_quote_any_colon_field_value | Test | backend/tests/test_spl_syntax_sanitize.py | 13-16 |
| test_dedupe_all_search_fields | Test | backend/tests/test_spl_syntax_sanitize.py | 19-27 |
| test_sanitize_fixes_missing_search_and_by_field_eq | Test | backend/tests/test_spl_syntax_sanitize.py | 30-35 |
| test_sanitize_fixes_table_field_eq_args | Test | backend/tests/test_spl_syntax_sanitize.py | 38-42 |
| test_sanitize_fixes_llm_markdown_and_duplicates | Test | backend/tests/test_spl_syntax_sanitize.py | 45-58 |

## Execution Flows

No execution flows pass through this community.

## Dependencies

### Outgoing

- `sub` (13 edge(s))
- `strip` (13 edge(s))
- `append` (11 edge(s))
- `format` (4 edge(s))
- `group` (4 edge(s))
- `match` (3 edge(s))
- `startswith` (3 edge(s))
- `split` (3 edge(s))
- `join` (3 edge(s))
- `replace` (3 edge(s))
- `len` (2 edge(s))
- `lower` (2 edge(s))
- `count` (2 edge(s))
- `isdigit` (1 edge(s))
- `find` (1 edge(s))

### Incoming

- `backend/services/investigation/spl_syntax_sanitize.py` (11 edge(s))
- `backend/tests/test_spl_syntax_sanitize.py` (5 edge(s))
- `count` (2 edge(s))
- `startswith` (1 edge(s))
- `split` (1 edge(s))
