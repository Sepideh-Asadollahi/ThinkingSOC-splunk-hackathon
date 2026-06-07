import type { LayoutNode } from "@/lib/api/graph/alert-centric"
import type { GraphEdge } from "@/lib/api/graph/types"

export function edgePath(from: LayoutNode, to: LayoutNode): string {
  return `M ${from.x} ${from.y} L ${to.x} ${to.y}`
}

export function edgeLabelLines(edge: GraphEdge): {
  primary: string
  secondary?: string
} {
  const narrative =
    typeof edge.properties?.narrative === "string"
      ? edge.properties.narrative.trim()
      : ""
  const kind =
    edge.label === "CAUSED"
      ? "Caused"
      : edge.label === "RESULTED_IN"
        ? "Resulted in"
        : edge.label || "Link"
  if (!narrative) {
    return { primary: kind }
  }
  const timing = narrative.replace(/^Sequential\s+Step\s*/i, "").trim()
  if (!timing || timing.toLowerCase() === kind.toLowerCase()) {
    return { primary: kind }
  }
  return { primary: kind, secondary: timing }
}

export function edgeCaption(edge: GraphEdge): string {
  const { primary, secondary } = edgeLabelLines(edge)
  return secondary ? `${primary} ${secondary}` : primary
}

export function layoutSeedKey(
  nodes: { id: string }[],
  edges: { id: string; from: string; to: string; label: string }[],
): string {
  return `${nodes.map((n) => n.id).join("|")}::${edges.map((e) => `${e.id}:${e.from}:${e.to}:${e.label}`).join("|")}`
}

export function edgeLabelPosition(
  from: LayoutNode,
  to: LayoutNode,
): { labelX: number; labelY: number } {
  const midX = (from.x + to.x) / 2
  const midY = (from.y + to.y) / 2
  const dx = to.x - from.x
  const dy = to.y - from.y
  const len = Math.hypot(dx, dy) || 1
  const nx = -dy / len
  const ny = dx / len
  return { labelX: midX + nx * 12, labelY: midY + ny * 12 }
}
