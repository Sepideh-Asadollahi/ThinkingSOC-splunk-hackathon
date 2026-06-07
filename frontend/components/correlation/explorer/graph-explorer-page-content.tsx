"use client"

import Link from "next/link"
import { Suspense } from "react"

import { GraphCanvas } from "@/components/correlation/explorer/graph-canvas"
import { GraphExplorerHeader } from "@/components/correlation/explorer/graph-explorer-header"
import { GraphExplorerLoadingState } from "@/components/correlation/explorer/graph-explorer-loading-state"
import {
  GraphProvider,
  useGraphState,
} from "@/components/correlation/explorer/graph-context"
import { InformationPanel } from "@/components/correlation/explorer/information-panel"
import { NeonActionButton, NeonAlert, NeonAlertDescription } from "@/components/neon-glass"
import { useGraphExplorerParams } from "@/hooks/correlation/use-graph-explorer-params"
import { useGraphQuery } from "@/hooks/correlation/use-graph-query"

function ExplorerBody() {
  const { findingId, isReady } = useGraphExplorerParams()
  const { loading, error } = useGraphState()

  useGraphQuery(findingId)

  if (!isReady || !findingId) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
        <p className="text-slate-400">
          Select a finding from the Correlation list to open Graph Explorer.
        </p>
        <Link href="/correlation">
          <NeonActionButton accent="teal">Back to Correlation</NeonActionButton>
        </Link>
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4 md:p-6">
      <GraphExplorerHeader findingId={findingId} showFilters={!loading} />

      {error ? (
        <NeonAlert variant="destructive">
          <NeonAlertDescription>{error}</NeonAlertDescription>
        </NeonAlert>
      ) : null}

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[1fr_360px]">
        <div className="min-h-[360px]">
          {loading ? <GraphExplorerLoadingState /> : <GraphCanvas />}
        </div>
        <InformationPanel />
      </div>
    </div>
  )
}

export function GraphExplorerPageContent() {
  return (
    <GraphProvider>
      <Suspense
        fallback={
          <div className="p-6">
            <GraphExplorerLoadingState />
          </div>
        }
      >
        <ExplorerBody />
      </Suspense>
    </GraphProvider>
  )
}
