import type { MouseEvent, PointerEvent } from "react"

import { GraphAlertNodeMark } from "@/components/correlation/explorer/graph-alert-node-mark"
import { truncateLabel } from "@/components/correlation/explorer/graph-canvas-tooltip"
import type { AlertDisplayInfo } from "@/lib/api/graph/alert-display"
import type { AlertFrameworkContext } from "@/lib/api/graph/attack-framework"
import { NODE_RADIUS, type LayoutNode } from "@/lib/api/graph/alert-centric"
import { nodeColorByRisk } from "@/lib/api/graph/risk-score"

import {
  ALERT_LABEL_MAX,
  KC_LABEL_MAX,
  MITRE_ID_MAX,
  MITRE_NAME_TAIL_MAX,
} from "./constants"

type GraphCanvasNodeProps = {
  node: LayoutNode
  isSelected: boolean
  isHover: boolean
  framework?: AlertFrameworkContext
  display?: AlertDisplayInfo
  onPointerDown: (nodeId: string, e: PointerEvent) => void
  onMouseEnter: (e: MouseEvent) => void
  onMouseMove: (e: MouseEvent) => void
  onMouseLeave: () => void
}

export function GraphCanvasNode({
  node,
  isSelected,
  isHover,
  framework,
  display,
  onPointerDown,
  onMouseEnter,
  onMouseMove,
  onMouseLeave,
}: GraphCanvasNodeProps) {
  const risk = node.properties?.risk_score as number | undefined
  const isAlert = node.group.includes("Alert")
  const fill = nodeColorByRisk(risk, node.group)
  const r = isSelected || isHover ? NODE_RADIUS + 4 : NODE_RADIUS
  const alertLabel = display?.displayName ?? node.label
  const analysisHref = display?.analysisHref
  const kc = framework?.killChainPhase
  const mitreId = framework?.mitreTechniqueId
  const mitreName = framework?.mitreTechniqueName

  return (
    <g
      className="cursor-grab active:cursor-grabbing"
      onPointerDown={(e) => onPointerDown(node.id, e)}
      onMouseEnter={onMouseEnter}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
    >
      {kc ? (
        <text
          x={node.x}
          y={node.y - r - 22}
          textAnchor="middle"
          className="fill-amber-300/95 text-[9px] font-semibold pointer-events-none select-none"
        >
          {truncateLabel(kc, KC_LABEL_MAX)}
        </text>
      ) : null}
      {isAlert ? (
        <GraphAlertNodeMark
          x={node.x}
          y={node.y}
          radius={r}
          risk={risk}
          selected={isSelected}
          hover={isHover}
        />
      ) : (
        <circle
          cx={node.x}
          cy={node.y}
          r={r}
          fill={fill}
          fillOpacity={0.85}
          stroke={isSelected ? "#fff" : "rgba(255,255,255,0.25)"}
          strokeWidth={isSelected ? 2 : 1}
        />
      )}
      <circle
        cx={node.x}
        cy={node.y}
        r={r + 8}
        fill="transparent"
        className="pointer-events-auto"
      />
      {analysisHref ? (
        <a
          href={analysisHref}
          target="_blank"
          rel="noopener noreferrer"
          className="pointer-events-auto"
          onClick={(e) => e.stopPropagation()}
          onPointerDown={(e) => e.stopPropagation()}
        >
          <text
            x={node.x}
            y={node.y + r + 14}
            textAnchor="middle"
            className="fill-orange-200 text-[10px] font-medium underline decoration-orange-400/60"
          >
            {truncateLabel(alertLabel, ALERT_LABEL_MAX)}
          </text>
        </a>
      ) : (
        <text
          x={node.x}
          y={node.y + r + 14}
          textAnchor="middle"
          className="fill-slate-200 text-[10px] pointer-events-none select-none"
        >
          {truncateLabel(alertLabel, ALERT_LABEL_MAX)}
        </text>
      )}
      {mitreId || mitreName ? (
        <text
          x={node.x}
          y={node.y + r + 28}
          textAnchor="middle"
          className="fill-violet-300/95 text-[8px] font-mono pointer-events-none select-none"
        >
          {mitreId
            ? truncateLabel(mitreId, MITRE_ID_MAX)
            : truncateLabel(mitreName ?? "", 16)}
          {mitreId && mitreName
            ? ` ${truncateLabel(mitreName, MITRE_NAME_TAIL_MAX)}`
            : ""}
        </text>
      ) : null}
      {analysisHref ? (
        <a
          href={analysisHref}
          target="_blank"
          rel="noopener noreferrer"
          className="pointer-events-auto"
          onClick={(e) => e.stopPropagation()}
          onPointerDown={(e) => e.stopPropagation()}
        >
          <text
            x={node.x}
            y={node.y + r + (mitreId || mitreName ? 42 : 28)}
            textAnchor="middle"
            className="fill-orange-300/90 text-[8px]"
          >
            Analysis ↗
          </text>
        </a>
      ) : null}
    </g>
  )
}
