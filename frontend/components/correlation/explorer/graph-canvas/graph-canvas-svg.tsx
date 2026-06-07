"use client"

import type { RefObject } from "react"

import type { AlertDisplayInfo } from "@/lib/api/graph/alert-display"
import type { AlertFrameworkContext } from "@/lib/api/graph/attack-framework"
import { CANVAS_HEIGHT, type LayoutNode } from "@/lib/api/graph/alert-centric"
import type { GraphEdge } from "@/lib/api/graph/types"

import { GraphCanvasArrowDef } from "./graph-canvas-arrow-def"
import { GraphCanvasEdges } from "./graph-canvas-edges"
import { GraphCanvasNode } from "./graph-canvas-node"

type GraphCanvasSvgProps = {
  svgRef: RefObject<SVGSVGElement | null>
  width: number
  edges: GraphEdge[]
  layout: LayoutNode[]
  nodeById: Map<string, LayoutNode>
  selectedNodeId: string | null
  hoverId: string | null
  frameworkByNodeId: Map<string, AlertFrameworkContext>
  displayByNodeId: Map<string, AlertDisplayInfo>
  onPointerMove: (e: React.PointerEvent) => void
  onPointerUp: (e: React.PointerEvent) => void
  onPointerDown: (nodeId: string, e: React.PointerEvent) => void
  onNodeMouseEnter: (
    nodeId: string,
    e: React.MouseEvent,
    alertLabel: string,
    fw: AlertFrameworkContext | undefined,
    alertRowId?: string,
  ) => void
  onNodeMouseMove: (e: React.MouseEvent) => void
  onNodeMouseLeave: () => void
}

export function GraphCanvasSvg({
  svgRef,
  width,
  edges,
  layout,
  nodeById,
  selectedNodeId,
  hoverId,
  frameworkByNodeId,
  displayByNodeId,
  onPointerMove,
  onPointerUp,
  onPointerDown,
  onNodeMouseEnter,
  onNodeMouseMove,
  onNodeMouseLeave,
}: GraphCanvasSvgProps) {
  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${width} ${CANVAS_HEIGHT}`}
      className="w-full touch-none rounded-xl border border-white/10 bg-[#0a0a0f]"
      role="img"
      aria-label="Alert chronology graph"
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    >
      <defs>
        <GraphCanvasArrowDef />
      </defs>
      <GraphCanvasEdges
        edges={edges}
        nodeById={nodeById}
        selectedNodeId={selectedNodeId}
        hoverId={hoverId}
      />
      {layout.map((node) => {
        const fw = frameworkByNodeId.get(node.id)
        const display = displayByNodeId.get(node.id)
        const alertLabel = display?.displayName ?? node.label
        const alertRowId =
          typeof node.properties?.alert_row_id === "string"
            ? node.properties.alert_row_id
            : display?.alertRowId
        return (
          <GraphCanvasNode
            key={node.id}
            node={node}
            isSelected={selectedNodeId === node.id}
            isHover={hoverId === node.id}
            framework={fw}
            display={display}
            onPointerDown={onPointerDown}
            onMouseEnter={(e) =>
              onNodeMouseEnter(node.id, e, alertLabel, fw, alertRowId)
            }
            onMouseMove={onNodeMouseMove}
            onMouseLeave={onNodeMouseLeave}
          />
        )
      })}
    </svg>
  )
}
