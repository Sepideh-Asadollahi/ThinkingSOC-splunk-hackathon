"use client"

import { useMemo } from "react"

import { AlertAnalysisLink } from "@/components/correlation/explorer/alert-analysis-link"
import { FrameworkBadges } from "@/components/correlation/explorer/framework-badges"
import { useGraphState } from "@/components/correlation/explorer/graph-context"
import { useAlertDisplayMap } from "@/hooks/correlation/use-alert-display-map"
import { useAlertFrameworkMap } from "@/hooks/correlation/use-alert-framework-map"
import {
  buildTimelineFromView,
  useFilteredGraphView,
} from "@/hooks/correlation/use-filtered-graph"
import { RiskScoreBadge } from "@/components/correlation/risk-score-badge"
import { NeonBadge } from "@/components/neon-glass"

export function TopologyOverviewPanel() {
  const { viewFilters } = useGraphState()
  const { topology, attackTrees, rawNodes } = useFilteredGraphView()
  const { byNodeId } = useAlertFrameworkMap()
  const { byNodeId: displayByNodeId } = useAlertDisplayMap()

  const timeline = useMemo(
    () => buildTimelineFromView(rawNodes, attackTrees, byNodeId, displayByNodeId),
    [rawNodes, attackTrees, byNodeId, displayByNodeId],
  )

  const onlyAlerts =
    viewFilters.nodeKinds.length === 1 && viewFilters.nodeKinds[0] === "Alert"

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden text-sm">
      <div className="flex flex-wrap gap-2 text-xs text-slate-400">
        <NeonBadge className="border-white/10 bg-white/5">
          {timeline.length} {onlyAlerts ? "alerts" : "items"}
        </NeonBadge>
        <NeonBadge className="border-white/10 bg-white/5">
          {topology?.edges.length ?? 0} links
        </NeonBadge>
      </div>
      <ul className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
        {timeline.map((item) => (
          <li key={item.key}>
            {item.bridge ? (
              <p className="mb-1 pl-6 text-[10px] uppercase tracking-wide text-teal-400/80">
                {item.bridge}
              </p>
            ) : null}
            <div className="rounded-lg border border-white/10 bg-black/30 px-3 py-2">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-[10px] font-semibold uppercase text-teal-400/90">
                    Step {item.step}
                  </p>
                  <span className="font-medium text-white">{item.label}</span>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  {item.riskScore != null ? (
                    <RiskScoreBadge score={item.riskScore} />
                  ) : null}
                  <AlertAnalysisLink info={item.display} variant="button" />
                </div>
              </div>
              <FrameworkBadges ctx={item.framework} className="mt-2" />
              <p className="mt-1 text-xs text-slate-500">
                {item.type}
                {item.node?.properties?.alert_row_id
                  ? ` · ${String(item.node.properties.alert_row_id)}`
                  : null}
                {item.timestamp ? ` · ${item.timestamp}` : null}
              </p>
              {item.framework?.description ? (
                <p className="mt-1 text-[11px] leading-snug text-slate-400">
                  {item.framework.description}
                </p>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
