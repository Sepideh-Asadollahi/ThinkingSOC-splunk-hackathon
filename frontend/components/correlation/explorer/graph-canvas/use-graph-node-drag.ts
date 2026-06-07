"use client"

import { useCallback, useRef } from "react"

import {
  CANVAS_HEIGHT,
  NODE_RADIUS,
  type LayoutNode,
} from "@/lib/api/graph/alert-centric"

type DragState = {
  nodeId: string
  pointerId: number
  startClientX: number
  startClientY: number
  moved: boolean
  offsetX: number
  offsetY: number
}

type UseGraphNodeDragOptions = {
  svgRef: React.RefObject<SVGSVGElement | null>
  layout: LayoutNode[]
  width: number
  selectedNodeId: string | null
  onSelectNode: (nodeId: string | null) => void
  onDragStart?: () => void
  setPositions: React.Dispatch<
    React.SetStateAction<Record<string, { x: number; y: number }>>
  >
}

export function useGraphNodeDrag({
  svgRef,
  layout,
  width,
  selectedNodeId,
  onSelectNode,
  onDragStart,
  setPositions,
}: UseGraphNodeDragOptions) {
  const dragRef = useRef<DragState | null>(null)

  const clientToSvg = useCallback((clientX: number, clientY: number) => {
    const svg = svgRef.current
    if (!svg) return null
    const ctm = svg.getScreenCTM()
    if (!ctm) return null
    const pt = svg.createSVGPoint()
    pt.x = clientX
    pt.y = clientY
    const local = pt.matrixTransform(ctm.inverse())
    return { x: local.x, y: local.y }
  }, [svgRef])

  const onPointerDown = useCallback(
    (nodeId: string, e: React.PointerEvent) => {
      const svg = svgRef.current
      if (!svg) return
      const pt = clientToSvg(e.clientX, e.clientY)
      const node = layout.find((n) => n.id === nodeId)
      if (!pt || !node) return
      e.preventDefault()
      onDragStart?.()
      svg.setPointerCapture(e.pointerId)
      dragRef.current = {
        nodeId,
        pointerId: e.pointerId,
        startClientX: e.clientX,
        startClientY: e.clientY,
        moved: false,
        offsetX: pt.x - node.x,
        offsetY: pt.y - node.y,
      }
    },
    [clientToSvg, layout, onDragStart, svgRef],
  )

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      const drag = dragRef.current
      if (!drag || drag.pointerId !== e.pointerId) return
      if (
        !drag.moved &&
        (Math.abs(e.clientX - drag.startClientX) > 4 ||
          Math.abs(e.clientY - drag.startClientY) > 4)
      ) {
        drag.moved = true
      }
      const pt = clientToSvg(e.clientX, e.clientY)
      if (!pt) return
      const x = Math.max(NODE_RADIUS, Math.min(width - NODE_RADIUS, pt.x - drag.offsetX))
      const y = Math.max(
        NODE_RADIUS,
        Math.min(CANVAS_HEIGHT - NODE_RADIUS, pt.y - drag.offsetY),
      )
      setPositions((prev) => ({
        ...prev,
        [drag.nodeId]: { x, y },
      }))
    },
    [clientToSvg, setPositions, width],
  )

  const onPointerUp = useCallback(
    (e: React.PointerEvent) => {
      const drag = dragRef.current
      if (!drag || drag.pointerId !== e.pointerId) return
      svgRef.current?.releasePointerCapture(e.pointerId)
      if (!drag.moved) {
        onSelectNode(selectedNodeId === drag.nodeId ? null : drag.nodeId)
      }
      dragRef.current = null
    },
    [onSelectNode, selectedNodeId, svgRef],
  )

  return { onPointerDown, onPointerMove, onPointerUp }
}
