"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { BrainCircuitIcon, FileSearchIcon, RefreshCwIcon } from "lucide-react"

import {
  NeonActionButton,
  NeonAlert,
  NeonAlertDescription,
  NeonAlertTitle,
  NeonBadge,
  NeonCardHeader,
  NeonGlassCard,
  NeonTabs,
  NeonTabsContent,
  NeonTabsContents,
  NeonTabsList,
  NeonTabsTrigger,
} from "@/components/neon-glass"
import { TsocDataTable, type TsocColumn } from "@/components/tables"
import { ApiError, backendFetch } from "@/lib/api/client"
import type { TriageQueueItem, TriageQueueResponse } from "@/lib/api/types"
import { investigationHrefForRow } from "@/lib/analysis-payload"
import { formatEventCreatedAt, getStorageEventId } from "@/lib/storage-events"
import { triagePriorityBadgeClass, triageVerdictBadgeClass } from "@/lib/triage-display"
import { cn } from "@/lib/utils"

type AnalysisRow = TriageQueueItem & Record<string, unknown>

function analysisRowKey(row: AnalysisRow, index: number): string {
  const id = getStorageEventId(row)
  if (id) return id
  return `row-${index}-${String(row.sid ?? row.stored_at ?? "unknown")}`
}

function getReviewVerdict(row: AnalysisRow): string {
  if (row.review_verdict) return String(row.review_verdict)
  const triage = row.triage
  if (triage && typeof triage === "object" && "review_verdict" in triage) {
    return String((triage as { review_verdict?: string }).review_verdict ?? "—")
  }
  return "—"
}

function getNeedsHumanReview(row: AnalysisRow): boolean {
  if (row.needs_human_review === true) return true
  const triage = row.triage
  if (triage && typeof triage === "object" && (triage as { needs_human_review?: boolean }).needs_human_review === true) {
    return true
  }
  return false
}

function getTriageScore(row: AnalysisRow): number {
  if (typeof row.triage_score === "number") return row.triage_score
  const triage = row.triage
  if (triage && typeof triage === "object" && typeof (triage as { triage_score?: number }).triage_score === "number") {
    return (triage as { triage_score: number }).triage_score
  }
  return -1
}

function getInvestigationPriority(row: AnalysisRow): string {
  if (row.investigation_priority) return String(row.investigation_priority)
  const triage = row.triage
  if (triage && typeof triage === "object" && "investigation_priority" in triage) {
    return String((triage as { investigation_priority?: string }).investigation_priority ?? "—")
  }
  return "—"
}

export function AnalysisContent() {
  const [queue, setQueue] = useState<TriageQueueResponse | null>(null)
  const [track, setTrack] = useState<"all" | "security" | "observability">("all")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await backendFetch<TriageQueueResponse>(
        `/triage/queue?limit=50&track=${track}`
      )
      setQueue(data)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load analysis queue")
    } finally {
      setLoading(false)
    }
  }, [track])

  useEffect(() => {
    void load()
  }, [load])

  const rows = useMemo(
    () => (queue?.results ?? []) as AnalysisRow[],
    [queue?.results],
  )

  const reviewVerdictFilterOptions = useMemo(() => {
    const values = new Set<string>()
    for (const row of rows) {
      const v = getReviewVerdict(row)
      if (v && v !== "—") values.add(v)
    }
    return [...values].sort().map((v) => ({ label: v, value: v }))
  }, [rows])

  const priorityFilterOptions = useMemo(() => {
    const values = new Set<string>()
    for (const row of rows) {
      const p = getInvestigationPriority(row)
      if (p && p !== "—") values.add(p)
    }
    return [...values].sort().map((v) => ({ label: v, value: v }))
  }, [rows])

  const columns = useMemo<TsocColumn<AnalysisRow>[]>(
    () => [
      {
        id: "score",
        header: "Score",
        sortable: true,
        sortValue: (row) => getTriageScore(row),
        cell: (row) => (
          <span className="font-mono font-medium text-violet-300">
            {getTriageScore(row) >= 0 ? getTriageScore(row) : "—"}
          </span>
        ),
      },
      {
        id: "review_verdict",
        header: "Review",
        sortable: true,
        sortValue: (row) => {
          const v = getReviewVerdict(row)
          const needsHuman = getNeedsHumanReview(row)
          return needsHuman ? `1-${v}` : `0-${v}`
        },
        searchValue: (row) => {
          const v = getReviewVerdict(row)
          return getNeedsHumanReview(row) && v !== "NEEDS_HUMAN_REVIEW" ? `${v} Review` : v
        },
        filterable: true,
        filterLabel: "Review verdict",
        filterOptions: reviewVerdictFilterOptions,
        filterValue: (row) => {
          const v = getReviewVerdict(row)
          return v === "—" ? null : v
        },
        cell: (row) => {
          const v = getReviewVerdict(row)
          const needsHuman = getNeedsHumanReview(row)
          if (v === "—" && !needsHuman) return "—"
          return (
            <span className="inline-flex flex-wrap items-center gap-1">
              {v !== "—" ? (
                <NeonBadge className={triageVerdictBadgeClass(v)}>{v}</NeonBadge>
              ) : null}
              {needsHuman && v !== "NEEDS_HUMAN_REVIEW" ? (
                <NeonBadge className="border-amber-500/40 text-amber-200">Review</NeonBadge>
              ) : null}
            </span>
          )
        },
      },
      {
        id: "priority",
        header: "Priority",
        sortable: true,
        sortValue: (row) => getInvestigationPriority(row),
        filterable: true,
        filterLabel: "Priority",
        filterOptions: priorityFilterOptions,
        filterValue: (row) => {
          const p = getInvestigationPriority(row)
          return p === "—" ? null : p
        },
        cell: (row) => {
          const p = getInvestigationPriority(row)
          if (p === "—") return "—"
          return <NeonBadge className={triagePriorityBadgeClass(p)}>{p}</NeonBadge>
        },
      },
      {
        id: "type",
        header: "Type",
        sortable: true,
        sortValue: (row) => String(row.tsoc_record_type ?? ""),
        searchValue: (row) => String(row.tsoc_record_type ?? ""),
        cell: (row) => (
          <NeonBadge className="border-orange-500/30 text-orange-300">
            {String(row.tsoc_record_type ?? "—")}
          </NeonBadge>
        ),
      },
      {
        id: "search",
        header: "Search",
        sortable: true,
        sortValue: (row) => String(row.search_name ?? ""),
        searchValue: (row) => String(row.search_name ?? ""),
        cell: (row) => String(row.search_name ?? "—"),
      },
      {
        id: "row",
        header: "Row",
        sortable: true,
        sortValue: (row) => Number(row.row_index ?? -1),
        cell: (row) => {
          const ri = row.row_index
          if (ri == null) return "—"
          return Number.isFinite(ri) ? String(ri + 1) : "—"
        },
      },
      {
        id: "sid",
        header: "SID",
        sortable: true,
        sortValue: (row) => String(row.sid ?? ""),
        searchValue: (row) => String(row.sid ?? ""),
        cell: (row) => (
          <span className="font-mono text-xs">{String(row.sid ?? "—")}</span>
        ),
      },
      {
        id: "track",
        header: "Track",
        sortable: true,
        sortValue: (row) => String(row.source_track ?? ""),
        cell: (row) => String(row.source_track ?? "—"),
      },
      {
        id: "created",
        header: "Created",
        sortable: true,
        sortValue: (row) => new Date(String(row.stored_at ?? "")).getTime() || 0,
        searchValue: (row) => formatEventCreatedAt(row.stored_at),
        cell: (row) => formatEventCreatedAt(row.stored_at),
      },
      {
        id: "investigation",
        header: "Investigation",
        headClassName: "text-right",
        cellClassName: "text-right",
        cell: (row) => {
          const href = investigationHrefForRow(row)
          if (!href) return "—"
          const isObs = row.source_track === "observability" || row.tsoc_record_type === "observability_analysis"
          return (
            <Link
              href={href}
              className={cn(
                "inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-medium transition-colors",
                isObs
                  ? "border-teal-500/30 text-teal-300 hover:bg-teal-500/10"
                  : "border-orange-500/30 text-orange-300 hover:bg-orange-500/10"
              )}
            >
              <FileSearchIcon className="size-3.5" />
              View
            </Link>
          )
        },
      },
    ],
    [reviewVerdictFilterOptions, priorityFilterOptions]
  )

  return (
    <div className="grid gap-4">
      <NeonGlassCard accent="orange">
        <NeonCardHeader
          accent="orange"
          icon={<BrainCircuitIcon className="size-5 text-orange-400" />}
          title="Analysis & triage"
          description="Pipeline results with post-analysis priority — newest first by default"
          actions={
            <>
              <NeonActionButton accent="orange" onClick={() => void load()} disabled={loading}>
                <RefreshCwIcon className="size-4" />
                Refresh
              </NeonActionButton>
            </>
          }
        />
        <div className="px-6 pb-6">
          <NeonTabs
            value={track}
            onValueChange={(v) => setTrack(v as "all" | "security" | "observability")}
          >
            <NeonTabsList accent="orange">
              <NeonTabsTrigger accent="orange" value="all">
                All tracks
              </NeonTabsTrigger>
              <NeonTabsTrigger accent="orange" value="security">
                Security
              </NeonTabsTrigger>
              <NeonTabsTrigger accent="orange" value="observability">
                Observability
              </NeonTabsTrigger>
            </NeonTabsList>

            <NeonTabsContents>
              {(["all", "security", "observability"] as const).map((t) => (
                <NeonTabsContent key={t} value={t} className="space-y-4">
                  {error ? (
                    <NeonAlert variant="destructive">
                      <NeonAlertTitle>Error</NeonAlertTitle>
                      <NeonAlertDescription>{error}</NeonAlertDescription>
                    </NeonAlert>
                  ) : null}

                  <NeonCardHeader
                    accent="orange"
                    title="Triage queue"
                    description={`${queue?.count ?? 0} analyzed alerts (newest first)`}
                    className="px-0 pt-0"
                  />
                  <TsocDataTable
                    accent="orange"
                    columns={columns}
                    rows={rows}
                    getRowKey={(row) => {
                      const idx = rows.indexOf(row)
                      return analysisRowKey(row, idx >= 0 ? idx : 0)
                    }}
                    loading={loading}
                    loadingMessage="Loading analysis & triage…"
                    emptyMessage="No analyzed alerts yet. Enable ingest auto-triage or submit alerts via the API."
                    searchPlaceholder="Search alerts…"
                    defaultPageSize={10}
                    defaultSortColumnId="created"
                    defaultSortDirection="desc"
                    maxHeight="520px"
                    enableTimeFilter
                    getRowTime={(row) => row.stored_at}
                    timeFilterStorageKey="analysis"
                  />
                </NeonTabsContent>
              ))}
            </NeonTabsContents>
          </NeonTabs>
        </div>
      </NeonGlassCard>
    </div>
  )
}
