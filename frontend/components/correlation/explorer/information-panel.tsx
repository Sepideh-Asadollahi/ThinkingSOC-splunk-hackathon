"use client"

import { TopologyCentricPanel } from "@/components/correlation/explorer/topology-centric-panel"
import { useGraphState } from "@/components/correlation/explorer/graph-context"
import { NeonGlassCard } from "@/components/neon-glass"

export function InformationPanel() {
  const { notifications } = useGraphState()

  return (
    <NeonGlassCard className="flex h-full min-h-0 flex-col p-4">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
        Attack story · timeline · MITRE
      </h2>
      {notifications?.length ? (
        <ul className="mb-3 space-y-1 text-xs text-amber-300/90">
          {notifications.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      ) : null}
      <TopologyCentricPanel />
    </NeonGlassCard>
  )
}
