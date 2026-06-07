import type {
  GraphEdge,
  GraphNode,
  GraphResponse,
  GraphTreeNode,
} from "@/lib/api/graph/types"

/** Neo4j node labels exposed in the explorer filter UI. */
export type GraphNodeKind = "Alert" | "Incident" | "Identity" | "Asset" | "IOC"

/** Relationship types exposed in the explorer filter UI. */
export type GraphEdgeKind =
  | "CAUSED"
  | "RESULTED_IN"
  | "RELATED_TO"
  | "PART_OF_INCIDENT"
  | "CAUSED_BY"
  | "DETECTED_BY"

export type GraphViewFilters = {
  nodeKinds: GraphNodeKind[]
  edgeKinds: GraphEdgeKind[]
}

/** Default: only alert-to-alert causation chain. */
export const DEFAULT_GRAPH_VIEW_FILTERS: GraphViewFilters = {
  nodeKinds: ["Alert"],
  edgeKinds: ["CAUSED"],
}

export type GraphFilterOption<K extends string> = {
  id: K
  label: string
  hint: string
}

export const GRAPH_NODE_FILTER_OPTIONS: GraphFilterOption<GraphNodeKind>[] = [
  {
    id: "Alert",
    label: "Alerts",
    hint: "Security alerts on the incident timeline",
  },
  {
    id: "Incident",
    label: "Incidents",
    hint: "Incident containers grouping alerts",
  },
  {
    id: "Identity",
    label: "Identities",
    hint: "Users and accounts linked to alerts",
  },
  {
    id: "Asset",
    label: "Assets",
    hint: "Hosts and assets linked to alerts",
  },
  {
    id: "IOC",
    label: "IOCs",
    hint: "Indicators of compromise",
  },
]

export const GRAPH_EDGE_FILTER_OPTIONS: GraphFilterOption<GraphEdgeKind>[] = [
  {
    id: "CAUSED",
    label: "Alert → Alert (caused)",
    hint: "Which alert led to the next alert in time order",
  },
  {
    id: "RESULTED_IN",
    label: "Resulted in",
    hint: "Action or alert resulted in another step",
  },
  {
    id: "RELATED_TO",
    label: "Related to entity",
    hint: "Alert linked to identity, asset, or IOC",
  },
  {
    id: "PART_OF_INCIDENT",
    label: "Part of incident",
    hint: "Alert belongs to an incident",
  },
  {
    id: "CAUSED_BY",
    label: "Caused by",
    hint: "Reverse causation or dependency edge",
  },
  {
    id: "DETECTED_BY",
    label: "Detected by",
    hint: "Alert detected by an action or sensor",
  },
]

export function nodeKinds(node: GraphNode): GraphNodeKind[] {
  return node.group.filter((g): g is GraphNodeKind =>
    GRAPH_NODE_FILTER_OPTIONS.some((o) => o.id === g),
  )
}

export function nodeMatchesFilter(
  node: GraphNode,
  filters: GraphViewFilters,
): boolean {
  const kinds = nodeKinds(node)
  if (!kinds.length) return false
  return kinds.some((k) => filters.nodeKinds.includes(k))
}

export function applyGraphViewFilters(
  topology: GraphResponse | null,
  filters: GraphViewFilters,
): GraphResponse | null {
  if (!topology) return null

  const nodes = topology.nodes.filter((n) => nodeMatchesFilter(n, filters))
  const nodeIds = new Set(nodes.map((n) => n.id))
  const edgeKindSet = new Set(filters.edgeKinds)
  const edges = topology.edges.filter(
    (e) =>
      nodeIds.has(e.from) &&
      nodeIds.has(e.to) &&
      edgeKindSet.has(e.label as GraphEdgeKind),
  )

  return {
    ...topology,
    nodes,
    edges,
  }
}

export function filterAttackTreesForView(
  trees: GraphTreeNode[],
  filters: GraphViewFilters,
): GraphTreeNode[] {
  const allowed = new Set(filters.nodeKinds)
  return trees.filter((t) => allowed.has(t.type as GraphNodeKind))
}

export function toggleFilterKind<K extends string>(
  current: K[],
  kind: K,
  enabled: boolean,
): K[] {
  if (enabled) {
    return current.includes(kind) ? current : [...current, kind]
  }
  return current.filter((k) => k !== kind)
}

export function isDefaultGraphViewFilters(filters: GraphViewFilters): boolean {
  return (
    filters.nodeKinds.length === DEFAULT_GRAPH_VIEW_FILTERS.nodeKinds.length &&
    filters.nodeKinds.every((k) =>
      DEFAULT_GRAPH_VIEW_FILTERS.nodeKinds.includes(k),
    ) &&
    filters.edgeKinds.length === DEFAULT_GRAPH_VIEW_FILTERS.edgeKinds.length &&
    filters.edgeKinds.every((k) =>
      DEFAULT_GRAPH_VIEW_FILTERS.edgeKinds.includes(k),
    )
  )
}

/** Labels present in source data but not in current filter (for empty-state hints). */
export function discoverAvailableKinds(topology: GraphResponse | null): {
  nodeKinds: GraphNodeKind[]
  edgeKinds: GraphEdgeKind[]
} {
  const nodeSet = new Set<GraphNodeKind>()
  const edgeSet = new Set<GraphEdgeKind>()
  for (const n of topology?.nodes ?? []) {
    for (const k of nodeKinds(n)) nodeSet.add(k)
  }
  for (const e of topology?.edges ?? []) {
    if (GRAPH_EDGE_FILTER_OPTIONS.some((o) => o.id === e.label)) {
      edgeSet.add(e.label as GraphEdgeKind)
    }
  }
  return {
    nodeKinds: [...nodeSet],
    edgeKinds: [...edgeSet],
  }
}

export function primaryNodeKind(node: GraphNode): GraphNodeKind | string {
  return nodeKinds(node)[0] ?? node.group[0] ?? "Node"
}

export function shortNodeKindLabel(kind: string): string {
  switch (kind) {
    case "Alert":
      return "ALE"
    case "Incident":
      return "INC"
    case "Identity":
      return "IDE"
    case "Asset":
      return "ASS"
    case "IOC":
      return "IOC"
    default:
      return kind.slice(0, 3).toUpperCase()
  }
}
