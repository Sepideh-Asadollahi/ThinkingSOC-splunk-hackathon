"use client"

import {
  AlertTriangleIcon,
  DatabaseIcon,
  GaugeIcon,
  ServerIcon,
  ShieldAlertIcon,
  UsersIcon,
} from "lucide-react"

import { NeonGlassCard } from "@/components/neon-glass"
import type { DashboardKpis } from "@/lib/api/types"
import { cn } from "@/lib/utils"

type KpiItem = {
  label: string
  value: string
  hint?: string
  icon: React.ReactNode
  accent: "teal" | "violet" | "orange"
}

function accentText(accent: KpiItem["accent"]) {
  if (accent === "violet") return "text-violet-400"
  if (accent === "orange") return "text-orange-400"
  return "text-teal-400"
}

function accentBg(accent: KpiItem["accent"]) {
  if (accent === "violet") return "bg-violet-500/10 border-violet-500/20"
  if (accent === "orange") return "bg-orange-500/10 border-orange-500/20"
  return "bg-teal-500/10 border-teal-500/20"
}

export function DashboardKpiGrid({ kpis }: { kpis: DashboardKpis }) {
  const items: KpiItem[] = [
    {
      label: "Total records",
      value: kpis.total_records.toLocaleString(),
      icon: <DatabaseIcon className="size-4" />,
      accent: "teal",
    },
    {
      label: "Analyses (24h)",
      value: kpis.analyses_24h.toLocaleString(),
      icon: <ShieldAlertIcon className="size-4" />,
      accent: "violet",
    },
    {
      label: "Needs review",
      value: kpis.needs_human_review.toLocaleString(),
      hint: "Human triage queue",
      icon: <AlertTriangleIcon className="size-4" />,
      accent: "orange",
    },
    {
      label: "Avg triage score",
      value: kpis.avg_triage_score.toFixed(1),
      icon: <GaugeIcon className="size-4" />,
      accent: "teal",
    },
    {
      label: "Users",
      value: kpis.users.toLocaleString(),
      icon: <UsersIcon className="size-4" />,
      accent: "violet",
    },
    {
      label: "Assets",
      value: kpis.assets.toLocaleString(),
      icon: <ServerIcon className="size-4" />,
      accent: "teal",
    },
  ]

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
      {items.map((item) => (
        <NeonGlassCard key={item.label} accent={item.accent} animatePreset="page" className="p-4">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="text-xs text-slate-500">{item.label}</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-white">{item.value}</p>
              {item.hint ? (
                <p className="mt-0.5 truncate text-xs text-slate-500">{item.hint}</p>
              ) : null}
            </div>
            <div
              className={cn(
                "flex size-9 shrink-0 items-center justify-center rounded-lg border",
                accentBg(item.accent),
                accentText(item.accent)
              )}
            >
              {item.icon}
            </div>
          </div>
        </NeonGlassCard>
      ))}
    </div>
  )
}
