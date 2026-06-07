"use client"

import { useState } from "react"
import { GitBranchIcon, RadarIcon } from "lucide-react"

import { AttackDiscoveryModal } from "@/components/correlation/attack-discovery-modal"
import { FindingsTable } from "@/components/correlation/findings-table"
import { NeonActionButton, NeonAlert, NeonAlertDescription } from "@/components/neon-glass"

export function CorrelationPageContent() {
  const [discoveryOpen, setDiscoveryOpen] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const mockMode = process.env.NEXT_PUBLIC_USE_MOCK === "true"

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-6 p-4 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <GitBranchIcon className="size-6 text-teal-400" />
            <h1 className="text-xl font-semibold text-white">Correlation</h1>
          </div>
          <p className="mt-1 max-w-2xl text-sm text-slate-400">
            Smart Attack Discovery findings — prioritize incidents, explore
            attack graphs, and run on-demand correlation.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <NeonActionButton
            accent="teal"
            onClick={() => setDiscoveryOpen(true)}
          >
            <RadarIcon className="size-4" />
            Attack Discovery
          </NeonActionButton>
        </div>
      </div>

      {mockMode ? (
        <NeonAlert>
          <NeonAlertDescription>
            Mock mode is on (<code className="text-teal-300">NEXT_PUBLIC_USE_MOCK=true</code>
            ) — API calls use static JSON fixtures.
          </NeonAlertDescription>
        </NeonAlert>
      ) : null}

      <FindingsTable refreshKey={refreshKey} />

      <AttackDiscoveryModal
        open={discoveryOpen}
        onOpenChange={setDiscoveryOpen}
        onComplete={() => setRefreshKey((k) => k + 1)}
      />
    </div>
  )
}
