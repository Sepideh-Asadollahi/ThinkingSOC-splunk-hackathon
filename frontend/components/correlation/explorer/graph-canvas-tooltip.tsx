"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import { cn } from "@/lib/utils"

export const GRAPH_TOOLTIP_DELAY_MS = 480

export type GraphTooltipState = {
  lines: string[]
  clientX: number
  clientY: number
}

export function useDelayedGraphTooltip(delayMs = GRAPH_TOOLTIP_DELAY_MS) {
  const [tooltip, setTooltip] = useState<GraphTooltipState | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pendingRef = useRef<GraphTooltipState | null>(null)

  const show = useCallback(
    (lines: string[], clientX: number, clientY: number) => {
      if (!lines.length) return
      if (timerRef.current) clearTimeout(timerRef.current)
      pendingRef.current = { lines, clientX, clientY }
      timerRef.current = setTimeout(() => {
        if (pendingRef.current) setTooltip(pendingRef.current)
        pendingRef.current = null
        timerRef.current = null
      }, delayMs)
    },
    [delayMs],
  )

  const hide = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = null
    pendingRef.current = null
    setTooltip(null)
  }, [])

  const move = useCallback((clientX: number, clientY: number) => {
    if (pendingRef.current) {
      pendingRef.current = { ...pendingRef.current, clientX, clientY }
    }
    setTooltip((prev) => (prev ? { ...prev, clientX, clientY } : null))
  }, [])

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    },
    [],
  )

  return { tooltip, show, hide, move }
}

export function truncateLabel(text: string, max: number): string {
  if (text.length <= max) return text
  return `${text.slice(0, max - 1)}…`
}

export function isTruncated(text: string, max: number): boolean {
  return text.length > max
}

export function GraphCanvasTooltip({
  tooltip,
  className,
}: {
  tooltip: GraphTooltipState | null
  className?: string
}) {
  if (!tooltip) return null

  return (
    <div
      role="tooltip"
      className={cn(
        "pointer-events-none fixed z-[100] max-w-md rounded-lg border border-white/15",
        "bg-[#12121a]/95 px-3 py-2 text-xs text-slate-100 shadow-xl backdrop-blur-sm",
        className,
      )}
      style={{
        left: tooltip.clientX + 14,
        top: tooltip.clientY + 14,
      }}
    >
      {tooltip.lines.map((line, i) => (
        <p
          key={`${i}-${line.slice(0, 24)}`}
          className={cn(
            "leading-snug",
            i > 0 && "mt-1 text-slate-400",
            i === 0 && "font-medium text-white",
          )}
        >
          {line}
        </p>
      ))}
    </div>
  )
}
