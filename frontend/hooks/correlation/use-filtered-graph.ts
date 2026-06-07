"use client"

import { useMemo } from "react"

import { useGraphState } from "@/components/correlation/explorer/graph-context"
import { parseAlertTimestamp } from "@/lib/api/graph/alert-centric"
import {
  applyGraphViewFilters,
  filterAttackTreesForView,
  nodeKinds,
} from "@/lib/api/graph/graph-filters"
import type { AlertFrameworkContext } from "@/lib/api/graph/attack-framework"
import type { AlertDisplayInfo } from "@/lib/api/graph/alert-display"
import type { GraphNode, GraphTreeNode } from "@/lib/api/graph/types"

export function useFilteredGraphView() {
  const state = useGraphState()

  return useMemo(() => {
    const topology = applyGraphViewFilters(state.sourceTopology, state.viewFilters)
    const attackTrees = filterAttackTreesForView(
      state.sourceAttackTrees,
      state.viewFilters,
    )
    const rawNodes = topology?.nodes ?? []

    return {
      topology,
      attackTrees,
      rawNodes,
      viewFilters: state.viewFilters,
      sourceTopology: state.sourceTopology,
    }
  }, [state.sourceTopology, state.sourceAttackTrees, state.viewFilters])
}

export type TimelineItem = {
  key: string
  step: string
  label: string
  timestamp?: string
  riskScore?: number
  bridge?: string
  type: string
  node?: GraphNode
  framework?: AlertFrameworkContext
  display?: AlertDisplayInfo
}

export function buildTimelineFromView(
  rawNodes: GraphNode[],
  attackTrees: GraphTreeNode[],
  frameworkByNodeId?: Map<string, AlertFrameworkContext>,
  displayByNodeId?: Map<string, AlertDisplayInfo>,
) {
  if (attackTrees.length) {
    return attackTrees.map((step) => ({
      key: step.node_id,
      step: step.step,
      label: displayByNodeId?.get(step.node_id)?.displayName ?? step.name,
      timestamp: step.timestamp,
      riskScore: step.risk_score,
      bridge: step.edge_context,
      type: step.type,
      node: rawNodes.find((n) => n.id === step.node_id),
      framework: frameworkByNodeId?.get(step.node_id),
      display: displayByNodeId?.get(step.node_id),
    }))
  }

  return [...rawNodes]
    .sort((a, b) => parseAlertTimestamp(a.properties) - parseAlertTimestamp(b.properties))
    .map((node, index) => ({
      key: node.id,
      step: String(index + 1),
      label: displayByNodeId?.get(node.id)?.displayName ?? node.label,
      timestamp:
        typeof node.properties.timestamp === "string"
          ? node.properties.timestamp
          : undefined,
      riskScore:
        typeof node.properties.risk_score === "number"
          ? node.properties.risk_score
          : undefined,
      bridge: undefined as string | undefined,
      type: nodeKinds(node)[0] ?? "Node",
      node,
      framework: frameworkByNodeId?.get(node.id),
      display: displayByNodeId?.get(node.id),
    }))
}

export function selectedNodeFromFilteredView(
  selectedNodeId: string | null,
  rawNodes: GraphNode[],
  topology: { nodes: GraphNode[] } | null,
): GraphNode | null {
  if (!selectedNodeId || !topology) return null
  return (
    rawNodes.find((n) => n.id === selectedNodeId) ??
    topology.nodes.find((n) => n.id === selectedNodeId) ??
    null
  )
}
