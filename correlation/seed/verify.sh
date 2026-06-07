#!/usr/bin/env bash
set -euo pipefail
BASE="${GRAPH_DEMO_BASE:-http://127.0.0.1:9876/api/v1/graph}"
KEY="${DEMO_API_KEY:-dev-key}"

echo "== health =="
curl -s "$BASE/health" | python3 -m json.tool

echo "== correlate =="
curl -s -X POST "$BASE/internal/correlate" \
  -H "X-Demo-Api-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"entity_identifiers":["hostname:SERVER01"],"current_alert_row_id":"ALERT-101","depth":2,"max_questions":0}' \
  | python3 -m json.tool

echo "== findings =="
curl -s "$BASE/findings?limit=10&offset=0&finding_type=smart_attack_discovery" \
  | python3 -m json.tool

echo "== topology =="
curl -s "$BASE/topology/7fda487b-c5fe-4b88-b153-0958d74e4aec" \
  | python3 -m json.tool

echo "== discover =="
RESP=$(curl -s -X POST "$BASE/analysis/discover-attack-paths" \
  -H "Content-Type: application/json" \
  -d '{"analysis_types":["smart"],"limit_to_latest_alerts":50,"force_reanalysis":true}')
echo "$RESP" | python3 -m json.tool
OP=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['operation_id'])")

echo "== poll =="
for _ in 1 2 3 4 5 6 7 8 9 10; do
  curl -s "$BASE/analysis/operations/$OP/status" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'], d.get('message',''))"
  sleep 2
done

echo "verify.sh done"
