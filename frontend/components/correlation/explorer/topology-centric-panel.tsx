"use client"

import { useState } from "react"

import { AttackNarrative } from "@/components/correlation/attack-narrative"
import { AlertAnalysisLink } from "@/components/correlation/explorer/alert-analysis-link"
import { FrameworkBadges } from "@/components/correlation/explorer/framework-badges"
import { useAlertDisplayMap } from "@/hooks/correlation/use-alert-display-map"
import { TopologyOverviewPanel } from "@/components/correlation/explorer/topology-overview-panel"
import { useSelectedRawDetails } from "@/components/correlation/explorer/use-selected-raw-details"
import { useGraphState } from "@/components/correlation/explorer/graph-context"
import { useAlertFrameworkMap } from "@/hooks/correlation/use-alert-framework-map"
import { RiskScoreBadge } from "@/components/correlation/risk-score-badge"
import { cn } from "@/lib/utils"

type PanelTab = "story" | "overview" | "node"

export function TopologyCentricPanel() {
  const [tab, setTab] = useState<PanelTab>("story")
  const { selectedNodeId, statusMessage, finding } = useGraphState()
  const details = useSelectedRawDetails()
  const { byNodeId } = useAlertFrameworkMap()
  const { byNodeId: displayByNodeId } = useAlertDisplayMap()
  const framework = selectedNodeId ? byNodeId.get(selectedNodeId) : undefined
  const display = selectedNodeId ? displayByNodeId.get(selectedNodeId) : undefined

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <div className="flex gap-1 rounded-lg border border-white/10 bg-black/30 p-1 text-xs">
        <button
          type="button"
          className={cn(
            "flex-1 rounded-md px-2 py-1.5 transition-colors",
            tab === "story"
              ? "bg-teal-500/20 text-teal-200"
              : "text-slate-400 hover:text-white",
          )}
          onClick={() => setTab("story")}
        >
          Attack story
        </button>
        <button
          type="button"
          className={cn(
            "flex-1 rounded-md px-2 py-1.5 transition-colors",
            tab === "overview"
              ? "bg-teal-500/20 text-teal-200"
              : "text-slate-400 hover:text-white",
          )}
          onClick={() => setTab("overview")}
        >
          Execution order
        </button>
        <button
          type="button"
          className={cn(
            "flex-1 rounded-md px-2 py-1.5 transition-colors",
            tab === "node"
              ? "bg-teal-500/20 text-teal-200"
              : "text-slate-400 hover:text-white",
          )}
          onClick={() => setTab("node")}
        >
          Node details
        </button>
      </div>

      {statusMessage && statusMessage !== "Success." ? (
        <p className="text-xs text-amber-300/90">{statusMessage}</p>
      ) : null}

      {tab === "story" ? (
        <div className="min-h-0 flex-1 overflow-y-auto pr-1">
          <AttackNarrative
            executiveSummary={finding?.details?.executive_summary ?? finding?.summary}
            steps={finding?.details?.attack_analysis_steps}
          />
        </div>
      ) : tab === "overview" ? (
        <TopologyOverviewPanel />
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto text-sm">
          {!selectedNodeId ? (
            <p className="text-slate-500">Select a node on the graph.</p>
          ) : !details ? (
            <p className="text-slate-500">No details for this node.</p>
          ) : (
            <dl className="space-y-3">
              <div>
                <dt className="text-xs uppercase text-slate-500">Alert</dt>
                <dd className="mt-0.5 flex flex-wrap items-center gap-2">
                  <span className="font-medium text-white">
                    {display?.displayName ?? details.name}
                  </span>
                  <AlertAnalysisLink info={display} variant="button" />
                </dd>
              </div>
              {details.alert_row_id ? (
                <div>
                  <dt className="text-xs uppercase text-slate-500">Row ID</dt>
                  <dd className="mt-0.5 font-mono text-xs text-slate-300">
                    {details.alert_row_id}
                  </dd>
                </div>
              ) : null}
              {details.timestamp ? (
                <div>
                  <dt className="text-xs uppercase text-slate-500">Timestamp</dt>
                  <dd className="mt-0.5 text-slate-300">{details.timestamp}</dd>
                </div>
              ) : null}
              {details.risk_score != null ? (
                <div>
                  <dt className="text-xs uppercase text-slate-500">Risk</dt>
                  <dd className="mt-1">
                    <RiskScoreBadge score={details.risk_score} />
                  </dd>
                </div>
              ) : null}
              {details.threat_status ? (
                <div>
                  <dt className="text-xs uppercase text-slate-500">Status</dt>
                  <dd className="mt-0.5 text-slate-300">{details.threat_status}</dd>
                </div>
              ) : null}
              {framework ? (
                <div>
                  <dt className="text-xs uppercase text-slate-500">MITRE & Kill chain</dt>
                  <dd className="mt-1">
                    <FrameworkBadges ctx={framework} size="sm" />
                  </dd>
                  {framework.description ? (
                    <dd className="mt-1 text-xs text-slate-400">{framework.description}</dd>
                  ) : null}
                </div>
              ) : null}
              <p className="text-[10px] text-slate-600">
                Source:{" "}
                {details.source === "contributing_alert"
                  ? "finding contributing_alerts"
                  : "Neo4j node properties"}
              </p>
            </dl>
          )}
        </div>
      )}
    </div>
  )
}
