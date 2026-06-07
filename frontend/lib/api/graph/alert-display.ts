import { investigationHrefForRow } from "@/lib/analysis-payload"
import type { TriageQueueItem } from "@/lib/api/types"
import type { ContributingAlert, GraphFindingDetails, GraphNode } from "@/lib/api/graph/types"

export type AlertDisplayInfo = {
  displayName: string
  alertRowId?: string
  sid?: string
  analysisHref: string | null
}

export type TriageAnalysisIndex = {
  bySid: Map<string, string>
  bySearchName: Map<string, string>
}

function normKey(value: string): string {
  return value.trim().toLowerCase()
}

export function buildTriageAnalysisIndex(
  rows: TriageQueueItem[],
): TriageAnalysisIndex {
  const bySid = new Map<string, string>()
  const bySearchName = new Map<string, string>()
  for (const row of rows) {
    const record = row as Record<string, unknown>
    const href = investigationHrefForRow(record)
    if (!href) continue
    const sid = row.sid ? String(row.sid).trim() : ""
    if (sid) bySid.set(sid, href)
    const search = row.search_name ? String(row.search_name).trim() : ""
    if (search) {
      const key = normKey(search)
      if (!bySearchName.has(key)) bySearchName.set(key, href)
    }
  }
  return { bySid, bySearchName }
}

function lookupHref(
  index: TriageAnalysisIndex | null,
  opts: { sid?: string; searchName?: string },
): string | null {
  if (!index) return null
  if (opts.sid) {
    const hit = index.bySid.get(opts.sid.trim())
    if (hit) return hit
  }
  if (opts.searchName) {
    const hit = index.bySearchName.get(normKey(opts.searchName))
    if (hit) return hit
  }
  return null
}

function contributingForNode(
  node: GraphNode,
  finding: GraphFindingDetails | null,
): ContributingAlert | undefined {
  const rowId = node.properties?.alert_row_id
  if (typeof rowId !== "string" || !rowId.trim()) return undefined
  return finding?.details?.contributing_alerts?.find(
    (a) => a.alert_row_id === rowId.trim(),
  )
}

export function resolveAlertDisplayInfo(
  node: GraphNode,
  finding: GraphFindingDetails | null,
  index: TriageAnalysisIndex | null,
): AlertDisplayInfo {
  const contrib = contributingForNode(node, finding)
  const props = node.properties ?? {}
  const sid =
    (typeof contrib?.sid === "string" && contrib.sid.trim()) ||
    (typeof props.sid === "string" && props.sid.trim()) ||
    undefined
  const searchName =
    (typeof contrib?.search_name === "string" && contrib.search_name.trim()) ||
    (typeof contrib?.alert_name === "string" && contrib.alert_name.trim()) ||
    (typeof props.search_name === "string" && props.search_name.trim()) ||
    (typeof props.name === "string" && props.name.trim()) ||
    node.label.trim()

  const displayName =
    (typeof contrib?.alert_name === "string" && contrib.alert_name.trim()) ||
    (typeof props.search_name === "string" && props.search_name.trim()) ||
    (typeof props.name === "string" && props.name.trim()) ||
    node.label.trim() ||
    "Alert"

  const alertRowId =
    (typeof contrib?.alert_row_id === "string" && contrib.alert_row_id) ||
    (typeof props.alert_row_id === "string" ? props.alert_row_id : undefined)

  const analysisHref = lookupHref(index, { sid, searchName })

  return {
    displayName,
    alertRowId,
    sid,
    analysisHref,
  }
}

export function buildAlertDisplayByNodeId(
  nodes: GraphNode[],
  finding: GraphFindingDetails | null,
  index: TriageAnalysisIndex | null,
): Map<string, AlertDisplayInfo> {
  const out = new Map<string, AlertDisplayInfo>()
  for (const node of nodes) {
    if (!node.group.includes("Alert")) continue
    out.set(node.id, resolveAlertDisplayInfo(node, finding, index))
  }
  return out
}
