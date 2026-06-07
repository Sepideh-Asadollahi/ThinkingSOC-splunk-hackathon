"use client"

import Link from "next/link"
import { ArrowLeftIcon, NetworkIcon } from "lucide-react"

import { useGraphState } from "@/components/correlation/explorer/graph-context"
import { useFilteredGraphView } from "@/hooks/correlation/use-filtered-graph"
import { GraphFilterModal } from "@/components/correlation/explorer/graph-filter-modal"
import { RiskScoreBadge } from "@/components/correlation/risk-score-badge"
import { isDefaultGraphViewFilters } from "@/lib/api/graph/graph-filters"
import { NeonBadge } from "@/components/neon-glass"

export function GraphExplorerHeader({
  findingId,
  showFilters = true,
}: {
  findingId: string
  showFilters?: boolean
}) {
  const { finding, viewFilters } = useGraphState()
  const { topology } = useFilteredGraphView()
  const isDefault = isDefaultGraphViewFilters(viewFilters)

  return (
    <div className="flex flex-wrap items-start justify-between gap-4 border-b border-white/10 pb-4">
      <div className="flex min-w-0 items-start gap-3">
        <Link
          href="/correlation"
          className="mt-0.5 inline-flex size-8 shrink-0 items-center justify-center rounded-md border border-white/10 text-slate-400 transition-colors hover:bg-white/5 hover:text-white"
          aria-label="Back to Correlation"
        >
          <ArrowLeftIcon className="size-4" />
        </Link>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <NetworkIcon className="size-5 text-teal-400" />
            <h1 className="truncate text-lg font-medium text-white">
              {finding?.title ?? "Graph Explorer"}
            </h1>
            {finding ? <RiskScoreBadge score={finding.risk_score} /> : null}
          </div>
          <p className="mt-1 font-mono text-xs text-slate-500">
            {finding?.display_id ?? findingId} ·{" "}
            {isDefault ? "alert → alert (CAUSED)" : "custom filter"}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
        {showFilters ? <GraphFilterModal /> : null}
        <NeonBadge className="border-white/10 bg-white/5">
          {topology?.nodes.length ?? 0} nodes
        </NeonBadge>
        <NeonBadge className="border-white/10 bg-white/5">
          {topology?.edges.length ?? 0} links
        </NeonBadge>
      </div>
    </div>
  )
}
