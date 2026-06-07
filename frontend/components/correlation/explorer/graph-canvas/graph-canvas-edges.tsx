import type { LayoutNode } from "@/lib/api/graph/alert-centric"
import type { GraphEdge } from "@/lib/api/graph/types"

import { edgeCaption, edgeLabelPosition, edgePath } from "./edge-utils"

type GraphCanvasEdgesProps = {
  edges: GraphEdge[]
  nodeById: Map<string, LayoutNode>
  selectedNodeId: string | null
  hoverId: string | null
}

export function GraphCanvasEdges({
  edges,
  nodeById,
  selectedNodeId,
  hoverId,
}: GraphCanvasEdgesProps) {
  return (
    <>
      {edges.map((edge) => {
        const from = nodeById.get(edge.from)
        const to = nodeById.get(edge.to)
        if (!from || !to) return null
        const highlighted =
          selectedNodeId === edge.from ||
          selectedNodeId === edge.to ||
          hoverId === edge.from ||
          hoverId === edge.to
        const { labelX, labelY } = edgeLabelPosition(from, to)
        return (
          <g key={edge.id}>
            <path
              d={edgePath(from, to)}
              fill="none"
              stroke={highlighted ? "#2dd4bf" : "rgba(148,163,184,0.35)"}
              strokeWidth={highlighted ? 2 : 1}
              markerEnd="url(#arrow)"
            />
            <text
              x={labelX}
              y={labelY}
              textAnchor="middle"
              dominantBaseline="middle"
              className="pointer-events-none select-none fill-slate-400/90 text-[7px] font-medium"
            >
              {edgeCaption(edge)}
            </text>
          </g>
        )
      })}
    </>
  )
}
