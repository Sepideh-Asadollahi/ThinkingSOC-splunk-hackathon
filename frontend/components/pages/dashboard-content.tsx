"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import {
  BrainCircuitIcon,
  BookOpenCheckIcon,
  GitBranchIcon,
  LayoutDashboardIcon,
  PlugIcon,
  RefreshCwIcon,
  MessageSquareTextIcon,
  UsersIcon,
} from "lucide-react"

import {
  DashboardActivityChart,
  DashboardHealthGauge,
  DashboardKpiGrid,
  DashboardPriorityChart,
  DashboardRecordTypesChart,
  DashboardRunbookOperations,
  DashboardSystemResources,
  DashboardTopPriorityTable,
  DashboardVerdictChart,
} from "@/components/dashboard"
import {
  NeonActionButton,
  NeonAlert,
  NeonAlertDescription,
  NeonAlertTitle,
  NeonFloatingIconBox,
  NeonGlassCard,
} from "@/components/neon-glass"
import { ApiError } from "@/lib/api/client"
import { fetchDashboardOverview } from "@/lib/api/dashboard"
import type { DashboardOverview } from "@/lib/api/types"
import { cn } from "@/lib/utils"

const quickLinks = [
  { title: "Runbook Library", href: "/runbooks/library", icon: BookOpenCheckIcon },
  { title: "SOC Chat", href: "/soc-chat", icon: MessageSquareTextIcon },
  { title: "Inventory", href: "/inventory", icon: UsersIcon },
  { title: "Relationships", href: "/relationships", icon: GitBranchIcon },
  { title: "Analysis", href: "/analysis", icon: BrainCircuitIcon },
  { title: "Integrations", href: "/splunk-connection", icon: PlugIcon },
]

function formatGeneratedAt(iso: string | null): string {
  if (!iso) return "—"
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString()
}

function metricsErrorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 401) {
      return (
        "Ingest token mismatch: backend expects TSOC_INGEST_TOKEN but the UI proxy did not send it. " +
        "Set the same value in frontend/.env.local and backend/.env, then restart tsoc-frontend."
      )
    }
    if (e.status === 503) {
      return "PostgreSQL is not configured. Set TSOC_POSTGRES_DSN on the backend to enable live dashboard metrics."
    }
    return e.message
  }
  return "Failed to load live metrics"
}

export function DashboardContent() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null)
  const [metricsError, setMetricsError] = useState<string | null>(null)
  const [initialLoading, setInitialLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async (options?: { background?: boolean }) => {
    const background = options?.background ?? false
    if (background) {
      setRefreshing(true)
    } else {
      setInitialLoading(true)
    }
    setMetricsError(null)
    try {
      const data = await fetchDashboardOverview()
      setOverview(data)
    } catch (e) {
      setOverview(null)
      setMetricsError(metricsErrorMessage(e))
    } finally {
      if (background) {
        setRefreshing(false)
      } else {
        setInitialLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timer)
  }, [load])

  useEffect(() => {
    const timer = window.setInterval(() => {
      void load({ background: true })
    }, 60_000)
    return () => window.clearInterval(timer)
  }, [load])

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <NeonFloatingIconBox accent="teal" className="animate-float">
            <LayoutDashboardIcon className="size-5 text-teal-400" />
          </NeonFloatingIconBox>
          <div>
            <h1 className="text-2xl font-semibold text-transparent bg-clip-text bg-gradient-to-r from-white via-slate-200 to-teal-400/90">
              Overview
            </h1>
            <p className="text-sm text-slate-400">
              Live platform status — ingest, triage, Forge, Autopilot, Chat, and inventory
              {overview?.generated_at ? (
                <span className="text-slate-500">
                  {" "}
                  · Updated {formatGeneratedAt(overview.generated_at)}
                </span>
              ) : null}
            </p>
          </div>
        </div>
        <NeonActionButton
          accent="teal"
          onClick={() => void load({ background: Boolean(overview) })}
          disabled={initialLoading || refreshing}
        >
          <RefreshCwIcon className={cn("size-4", (initialLoading || refreshing) && "animate-spin")} />
          Refresh
        </NeonActionButton>
      </div>

      <section className="space-y-4" aria-label="Live metrics">
        {metricsError ? (
          <NeonAlert variant="destructive">
            <NeonAlertTitle>Live metrics unavailable</NeonAlertTitle>
            <NeonAlertDescription>
              {metricsError}{" "}
              <Link href="/splunk-connection" className="text-teal-400 underline-offset-2 hover:underline">
                Check integrations
              </Link>
            </NeonAlertDescription>
          </NeonAlert>
        ) : null}

        {initialLoading && !overview ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <NeonGlassCard key={i} accent="teal" className="h-24 animate-pulse p-4" />
            ))}
          </div>
        ) : null}

        {overview?.postgres_configured ? (
        <>
          <DashboardKpiGrid kpis={overview.kpis} />

          <DashboardRunbookOperations ops={overview.runbook_ops} />

          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2 flex [&>*]:min-h-0 [&>*]:w-full">
              <DashboardActivityChart timeline={overview.activity_timeline} />
            </div>
            <div className="flex flex-col gap-4">
              <DashboardHealthGauge
                healthScore={overview.health_score}
                integrations={overview.integrations}
              />
              <DashboardSystemResources resources={overview.system_resources} />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <DashboardVerdictChart items={overview.triage_by_verdict} />
            <DashboardPriorityChart items={overview.triage_by_priority} />
          </div>

          <DashboardRecordTypesChart counts={overview.record_type_counts} />

          <DashboardTopPriorityTable items={overview.top_priority} />
        </>
        ) : null}
      </section>

      <div className="flex flex-wrap gap-2 border-t border-white/[0.06] pt-4">
        <span className="w-full text-xs font-medium uppercase tracking-wide text-slate-500">
          Quick navigation
        </span>
        {quickLinks.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-slate-300 transition-colors hover:border-teal-500/30 hover:text-white"
          >
            <link.icon className="size-4 text-teal-400/80" />
            {link.title}
          </Link>
        ))}
      </div>
    </div>
  )
}
