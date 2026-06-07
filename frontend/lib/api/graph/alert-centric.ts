import type {
  AttackTreeResponse,
  GraphEdge,
  GraphNode,
  GraphResponse,
  GraphTreeNode,
} from "@/lib/api/graph/types"

export function isAlertNode(node: GraphNode): boolean {
  return node.group.includes("Alert")
}

/** One display edge per (from, to) for CAUSED — avoids stacked duplicate labels on the canvas. */
export function dedupeCausedEdges(edges: GraphEdge[]): GraphEdge[] {
  const byPair = new Map<string, GraphEdge>()
  const rest: GraphEdge[] = []
  for (const edge of edges) {
    if (edge.label !== "CAUSED") {
      rest.push(edge)
      continue
    }
    const key = `${edge.from}\0${edge.to}`
    const existing = byPair.get(key)
    if (!existing) {
      byPair.set(key, edge)
      continue
    }
    const prev = existing.properties ?? {}
    const next = edge.properties ?? {}
    const narrative =
      (typeof next.narrative === "string" && next.narrative) ||
      (typeof prev.narrative === "string" && prev.narrative) ||
      undefined
    byPair.set(key, {
      ...existing,
      properties: {
        ...prev,
        ...next,
        ...(narrative ? { narrative } : {}),
      },
    })
  }
  return [...rest, ...byPair.values()]
}

export function filterAlertTopology(topology: GraphResponse): GraphResponse {
  const nodes = topology.nodes.filter(isAlertNode)
  const ids = new Set(nodes.map((n) => n.id))
  const edges = dedupeCausedEdges(
    topology.edges.filter(
      (e) =>
        ids.has(e.from) &&
        ids.has(e.to) &&
        (e.label === "CAUSED" || e.label === "RESULTED_IN"),
    ),
  )
  return {
    ...topology,
    nodes,
    edges,
    notifications: topology.notifications,
  }
}

export function filterAlertAttackTrees(trees: GraphTreeNode[]): GraphTreeNode[] {
  return trees.filter((t) => t.type === "Alert")
}

export function filterAlertAttackTreeResponse(
  response: AttackTreeResponse,
): AttackTreeResponse {
  return {
    ...response,
    attack_trees: filterAlertAttackTrees(response.attack_trees),
  }
}

export function parseAlertTimestamp(props: Record<string, unknown>): number {
  const raw = props.timestamp
  if (typeof raw !== "string") return 0
  const t = Date.parse(raw)
  return Number.isNaN(t) ? 0 : t
}

export function orderAlertChain(
  nodes: GraphNode[],
  edges: GraphEdge[],
): GraphNode[] {
  if (nodes.length <= 1) return nodes
  const outDegree = new Map<string, number>()
  const next = new Map<string, string>()
  for (const n of nodes) outDegree.set(n.id, 0)
  for (const e of edges) {
    if (e.label !== "CAUSED" && e.label !== "RESULTED_IN") continue
    next.set(e.from, e.to)
    outDegree.set(e.to, (outDegree.get(e.to) ?? 0) + 1)
  }
  const roots = nodes.filter((n) => (outDegree.get(n.id) ?? 0) === 0)
  const start =
    roots[0] ??
    [...nodes].sort(
      (a, b) =>
        parseAlertTimestamp(a.properties) - parseAlertTimestamp(b.properties),
    )[0]
  const ordered: GraphNode[] = []
  const seen = new Set<string>()
  let cur: GraphNode | undefined = start
  while (cur && !seen.has(cur.id)) {
    ordered.push(cur)
    seen.add(cur.id)
    const nid = next.get(cur.id)
    cur = nid ? nodes.find((n) => n.id === nid) : undefined
  }
  for (const n of nodes) {
    if (!seen.has(n.id)) ordered.push(n)
  }
  return ordered
}

export type LayoutNode = GraphNode & { x: number; y: number }

const NODE_RADIUS = 22
const MIN_H_GAP = 140
const CANVAS_HEIGHT = 420

export function layoutAlertChain(
  nodes: GraphNode[],
  edges: GraphEdge[],
): { layout: LayoutNode[]; width: number; height: number } {
  const ordered = orderAlertChain(nodes, edges)
  const width = Math.max(640, ordered.length * MIN_H_GAP + 80)
  const y = CANVAS_HEIGHT / 2
  const step = width / (ordered.length + 1)
  const layout = ordered.map((node, i) => ({
    ...node,
    x: step * (i + 1),
    y,
  }))
  return { layout, width, height: CANVAS_HEIGHT }
}

export { NODE_RADIUS, MIN_H_GAP, CANVAS_HEIGHT }
