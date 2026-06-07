"use client"

import { useCallback, useState } from "react"

import { useDelayedGraphTooltip } from "@/components/correlation/explorer/graph-canvas-tooltip"
import type { AlertFrameworkContext } from "@/lib/api/graph/attack-framework"

import { buildNodeTooltipLines, nodeTooltipWorthShowing } from "./node-tooltip"

export function useGraphNodeHover() {
  const [hoverId, setHoverId] = useState<string | null>(null)
  const { tooltip, show: showTooltip, hide: hideTooltip, move: moveTooltip } =
    useDelayedGraphTooltip()

  const onNodeMouseEnter = useCallback(
    (
      nodeId: string,
      e: React.MouseEvent,
      alertLabel: string,
      fw: AlertFrameworkContext | undefined,
      alertRowId?: string,
    ) => {
      setHoverId(nodeId)
      if (!nodeTooltipWorthShowing(alertLabel, fw)) return
      showTooltip(
        buildNodeTooltipLines(alertLabel, fw, alertRowId),
        e.clientX,
        e.clientY,
      )
    },
    [showTooltip],
  )

  const onNodeMouseMove = useCallback(
    (e: React.MouseEvent) => {
      moveTooltip(e.clientX, e.clientY)
    },
    [moveTooltip],
  )

  const onNodeMouseLeave = useCallback(() => {
    setHoverId(null)
    hideTooltip()
  }, [hideTooltip])

  return {
    hoverId,
    tooltip,
    hideTooltip,
    onNodeMouseEnter,
    onNodeMouseMove,
    onNodeMouseLeave,
  }
}
