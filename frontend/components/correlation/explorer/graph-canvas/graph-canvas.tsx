"use client"

import { useCallback, useRef } from "react"

import { GraphCanvasTooltip } from "@/components/correlation/explorer/graph-canvas-tooltip"
import { useGraphDispatch, useGraphState } from "@/components/correlation/explorer/graph-context"
import { useAlertDisplayMap } from "@/hooks/correlation/use-alert-display-map"
import { useAlertFrameworkMap } from "@/hooks/correlation/use-alert-framework-map"
import {
  selectedNodeFromFilteredView,
  useFilteredGraphView,
} from "@/hooks/correlation/use-filtered-graph"
import { cn } from "@/lib/utils"

import { GraphCanvasEmpty } from "./graph-canvas-empty"
import { GraphCanvasSelection } from "./graph-canvas-selection"
import { GraphCanvasSvg } from "./graph-canvas-svg"
import { GraphCanvasToolbar } from "./graph-canvas-toolbar"
import { useGraphCanvasLayout } from "./use-graph-canvas-layout"
import { useGraphNodeDrag } from "./use-graph-node-drag"
import { useGraphNodeHover } from "./use-graph-node-hover"

export function GraphCanvas({ className }: { className?: string }) {
  const { selectedNodeId, statusMessage } = useGraphState()
  const dispatch = useGraphDispatch()
  const { topology, rawNodes } = useFilteredGraphView()
  const { byNodeId, killChainPhases, mitreTechniques } = useAlertFrameworkMap()
  const {
    byNodeId: displayByNodeId,
    indexLoading: analysisLinksLoading,
    indexError: analysisLinksError,
  } = useAlertDisplayMap()
  const svgRef = useRef<SVGSVGElement>(null)

  const nodes = topology?.nodes ?? []
  const edges = topology?.edges ?? []

  const { layout, width, nodeById, setPositions } = useGraphCanvasLayout(
    nodes,
    edges,
  )

  const {
    hoverId,
    tooltip,
    hideTooltip,
    onNodeMouseEnter,
    onNodeMouseMove,
    onNodeMouseLeave,
  } = useGraphNodeHover()

  const onSelectNode = useCallback(
    (nodeId: string | null) => {
      dispatch({ type: "SELECT_NODE", payload: nodeId })
    },
    [dispatch],
  )

  const { onPointerDown, onPointerMove, onPointerUp } = useGraphNodeDrag({
    svgRef,
    layout,
    width,
    selectedNodeId,
    onSelectNode,
    onDragStart: hideTooltip,
    setPositions,
  })

  const selected = selectedNodeFromFilteredView(
    selectedNodeId,
    rawNodes,
    topology,
  )

  if (!topology?.nodes.length) {
    return <GraphCanvasEmpty statusMessage={statusMessage} className={className} />
  }

  return (
    <div
      className={cn("relative flex flex-col gap-2", className)}
      onMouseLeave={hideTooltip}
    >
      <GraphCanvasTooltip tooltip={tooltip} />
      <GraphCanvasToolbar
        killChainPhases={killChainPhases}
        mitreTechniques={mitreTechniques}
        analysisLinksLoading={analysisLinksLoading}
        analysisLinksError={analysisLinksError}
      />
      <GraphCanvasSvg
        svgRef={svgRef}
        width={width}
        edges={edges}
        layout={layout}
        nodeById={nodeById}
        selectedNodeId={selectedNodeId}
        hoverId={hoverId}
        frameworkByNodeId={byNodeId}
        displayByNodeId={displayByNodeId}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerDown={onPointerDown}
        onNodeMouseEnter={onNodeMouseEnter}
        onNodeMouseMove={onNodeMouseMove}
        onNodeMouseLeave={onNodeMouseLeave}
      />
      {selected ? (
        <GraphCanvasSelection
          selected={selected}
          display={displayByNodeId.get(selected.id)}
          framework={byNodeId.get(selected.id)}
        />
      ) : null}
    </div>
  )
}
