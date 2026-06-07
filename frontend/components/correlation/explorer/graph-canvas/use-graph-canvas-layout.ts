"use client"

import { useEffect, useMemo, useState } from "react"

import {
  layoutAlertChain,
  type LayoutNode,
} from "@/lib/api/graph/alert-centric"
import type { GraphEdge, GraphNode } from "@/lib/api/graph/types"

import { layoutSeedKey } from "./edge-utils"

export function useGraphCanvasLayout(nodes: GraphNode[], edges: GraphEdge[]) {
  const { layout: defaultLayout, width } = useMemo(
    () => layoutAlertChain(nodes, edges),
    [nodes, edges],
  )

  const seedKey = useMemo(() => layoutSeedKey(nodes, edges), [nodes, edges])

  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>(
    {},
  )

  useEffect(() => {
    const { layout } = layoutAlertChain(nodes, edges)
    setPositions((prev) => {
      const next: Record<string, { x: number; y: number }> = {}
      for (const node of layout) {
        next[node.id] = { x: node.x, y: node.y }
      }
      const prevIds = Object.keys(prev)
      const nextIds = Object.keys(next)
      if (
        prevIds.length === nextIds.length &&
        nextIds.every(
          (id) =>
            prev[id]?.x === next[id]?.x && prev[id]?.y === next[id]?.y,
        )
      ) {
        return prev
      }
      return next
    })
  }, [seedKey, nodes, edges])

  const layout: LayoutNode[] = useMemo(() => {
    return defaultLayout.map((node) => {
      const pos = positions[node.id]
      return pos ? { ...node, x: pos.x, y: pos.y } : node
    })
  }, [defaultLayout, positions])

  const nodeById = useMemo(() => {
    const map = new Map<string, LayoutNode>()
    for (const n of layout) map.set(n.id, n)
    return map
  }, [layout])

  return { layout, width, nodeById, setPositions }
}
