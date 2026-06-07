# middleware-request

## Overview

Community of 3 nodes

- **Size**: 3 nodes
- **Cohesion**: 0.1250
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| _should_skip_request_log | Function | backend/middleware/request_logging.py | 19-20 |
| RequestLoggingMiddleware | Class | backend/middleware/request_logging.py | 23-56 |
| dispatch | Function | backend/middleware/request_logging.py | 24-56 |

## Execution Flows

- **dispatch** (criticality: 0.61, depth: 1)

## Dependencies

### Outgoing

- `perf_counter` (3 edge(s))
- `call_next` (2 edge(s))
- `BaseHTTPMiddleware` (1 edge(s))
- `strip` (1 edge(s))
- `get` (1 edge(s))
- `str` (1 edge(s))
- `uuid4` (1 edge(s))
- `exception` (1 edge(s))
- `info` (1 edge(s))

### Incoming

- `backend/middleware/request_logging.py` (2 edge(s))
