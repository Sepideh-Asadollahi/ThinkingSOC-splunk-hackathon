"use client"

import { CpuIcon, HardDriveIcon } from "lucide-react"

import { NeonCardHeader, NeonGlassCard } from "@/components/neon-glass"
import type { SystemResources } from "@/lib/api/types"
import { cn } from "@/lib/utils"

function formatGiB(bytes: number): string {
  if (!bytes) return "0 GB"
  return `${(bytes / 1024 ** 3).toFixed(1)} GB`
}

function usageBarColor(percent: number): string {
  if (percent >= 90) return "bg-red-500"
  if (percent >= 75) return "bg-orange-500"
  return "bg-teal-500"
}

function ResourceMeter({
  label,
  percent,
  detail,
  icon,
}: {
  label: string
  percent: number
  detail: string
  icon: React.ReactNode
}) {
  const clamped = Math.min(100, Math.max(0, percent))
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2 text-sm">
        <span className="flex items-center gap-2 text-slate-400">
          <span className="text-teal-400/80">{icon}</span>
          {label}
        </span>
        <span className="tabular-nums text-white">{clamped.toFixed(1)}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/10">
        <div
          className={cn("h-full rounded-full transition-all duration-500", usageBarColor(clamped))}
          style={{ width: `${clamped}%` }}
        />
      </div>
      <p className="text-xs text-slate-500">{detail}</p>
    </div>
  )
}

export function DashboardSystemResources({ resources }: { resources: SystemResources }) {
  return (
    <NeonGlassCard accent="teal" animatePreset="page" className="flex flex-col">
      <NeonCardHeader
        accent="teal"
        title="Host resources"
        description={
          resources.hostname
            ? `OS metrics on ${resources.hostname}`
            : "OS CPU and memory on the backend host"
        }
        className="px-4 pt-4"
      />
      <div className="flex flex-1 flex-col justify-center gap-5 px-4 pb-4">
        <ResourceMeter
          label="CPU"
          percent={resources.cpu_percent}
          detail="System-wide processor utilization"
          icon={<CpuIcon className="size-4" />}
        />
        <ResourceMeter
          label="Memory"
          percent={resources.memory_percent}
          detail={`${formatGiB(resources.memory_used_bytes)} / ${formatGiB(resources.memory_total_bytes)} used`}
          icon={<HardDriveIcon className="size-4" />}
        />
      </div>
    </NeonGlassCard>
  )
}
