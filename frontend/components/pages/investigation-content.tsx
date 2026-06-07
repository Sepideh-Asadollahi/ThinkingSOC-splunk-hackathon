"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useParams } from "next/navigation"
import { ArrowLeftIcon, FileSearchIcon } from "lucide-react"

import { InvestigationExportButton } from "@/components/investigation-export-button"
import {
  NeonAlert,
  NeonAlertDescription,
  NeonAlertTitle,
  NeonBadge,
  NeonCardHeader,
  NeonGlassCard,
} from "@/components/neon-glass"
import { StorageEventDetail } from "@/components/structured-data"
import { pickJudgeFromData } from "@/components/structured-data/soc-analysis-view"
import { pickTriageFromPayload } from "@/components/structured-data/triage-section"
import { asRecord } from "@/components/structured-data/utils"
import {
  hasActiveAdminOrgGap,
  mergeAdminOrgGapIntoAnalysis,
  normalizeAdminOrgGap,
  pickActiveAdminOrgGapFromStorageRows,
  pickAdminOrgGap,
} from "@/lib/admin-org-gap"
import { pickSecurityAnalysis } from "@/lib/analysis-payload"
import { ApiError, backendFetch } from "@/lib/api/client"
import {
  investigationLog,
  summarizeStoredEventPayload,
} from "@/lib/api/investigation-log"
import type { StorageEventsResponse, StoredEventRecord } from "@/lib/api/types"
import { triagePriorityBadgeClass, triageVerdictBadgeClass, pickTriageRiskScore, triageRiskScoreBadgeClass } from "@/lib/triage-display"
import { cn } from "@/lib/utils"

function InvestigationLoadingSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading investigation">
      <div className="h-24 animate-pulse rounded-xl border border-white/10 bg-white/[0.03]" />
      <div className="grid gap-4 md:grid-cols-2">
        <div className="h-40 animate-pulse rounded-xl border border-white/10 bg-white/[0.03]" />
        <div className="h-40 animate-pulse rounded-xl border border-white/10 bg-white/[0.03]" />
      </div>
      <div className="h-56 animate-pulse rounded-xl border border-white/10 bg-white/[0.03]" />
    </div>
  )
}

async function enrichEventWithAdminOrgGap(event: StoredEventRecord): Promise<StoredEventRecord> {
  const payload = asRecord(event.payload) ?? {}
  const analysis = pickSecurityAnalysis(payload)
  if (!analysis) {
    investigationLog("enrich.skip", { reason: "no_security_analysis" })
    return event
  }
  const embedded = normalizeAdminOrgGap(analysis.admin_org_gap)
  if (hasActiveAdminOrgGap(embedded)) {
    investigationLog("enrich.skip", { reason: "active_admin_org_gap_embedded" })
    return event
  }

  const sid = event.sid ?? payload.sid
  if (!sid || typeof sid !== "string") {
    investigationLog("enrich.skip", { reason: "missing_sid" })
    return event
  }

  const t0 = performance.now()
  try {
    investigationLog("enrich.fetch_admin_gap.start", { sid, hadInactiveEmbedded: embedded != null })
    const listed = await backendFetch<StorageEventsResponse>(
      `/storage/events?sid=${encodeURIComponent(sid)}&record_type=admin_org_gap_suggest&limit=10`
    )
    const gap = pickActiveAdminOrgGapFromStorageRows(listed.results)
    if (!gap) {
      investigationLog("enrich.fetch_admin_gap.empty", {
        sid,
        rows: listed.results?.length ?? 0,
        elapsedMs: Math.round(performance.now() - t0),
      })
      return event
    }

    const nextAnalysis = mergeAdminOrgGapIntoAnalysis(analysis, { admin_org_gap: gap }) ?? {
      ...analysis,
      admin_org_gap: gap,
    }
    const nextPayload = { ...payload }
    if (asRecord(payload.analysis)) {
      nextPayload.analysis = nextAnalysis
    } else if (asRecord(payload.security_result)) {
      nextPayload.security_result = nextAnalysis
    } else {
      nextPayload.analysis = nextAnalysis
    }
    investigationLog("enrich.fetch_admin_gap.ok", {
      sid,
      elapsedMs: Math.round(performance.now() - t0),
    })
    return { ...event, payload: nextPayload }
  } catch (e) {
    investigationLog(
      "enrich.fetch_admin_gap.failed",
      {
        sid,
        elapsedMs: Math.round(performance.now() - t0),
        status: e instanceof ApiError ? e.status : undefined,
        message: e instanceof Error ? e.message : String(e),
      },
      "warn"
    )
    return event
  }
}

function InvestigationHeaderChips({ event }: { event: StoredEventRecord }) {
  const payload = asRecord(event.payload) ?? {}
  const triage = pickTriageFromPayload(payload)
  const analysis = pickSecurityAnalysis(payload)
  const adminGap = pickAdminOrgGap(payload) ?? (analysis ? pickAdminOrgGap(analysis) : null)
  const judge = analysis ? pickJudgeFromData(analysis) : null

  const reviewVerdict = triage ? String(triage.review_verdict ?? "") : ""
  const invPriority = triage ? String(triage.investigation_priority ?? "") : ""
  const judgeVerdict = judge ? String(judge.verdict ?? "") : ""
  const judgePriority = judge ? String(judge.priority ?? "") : ""

  const chips: { label: string; className: string }[] = []
  if (reviewVerdict) {
    chips.push({ label: reviewVerdict, className: triageVerdictBadgeClass(reviewVerdict) })
  }
  if (invPriority) {
    chips.push({ label: `Priority: ${invPriority}`, className: triagePriorityBadgeClass(invPriority) })
  }
  if (judgeVerdict) {
    chips.push({ label: `Judge: ${judgeVerdict}`, className: "border-orange-500/40 text-orange-300" })
  }
  if (judgePriority) {
    chips.push({ label: judgePriority, className: triagePriorityBadgeClass(judgePriority) })
  }
  if (hasActiveAdminOrgGap(adminGap)) {
    chips.push({ label: "Admin question", className: "border-violet-500/40 text-violet-300" })
  }

  const riskScore = pickTriageRiskScore(triage, payload)
  if (riskScore == null && chips.length === 0) return null

  return (
    <div className="space-y-3 px-6 pb-4">
      {riskScore != null ? (
        <div className="flex flex-wrap items-center gap-2" data-testid="investigation-risk-score">
          <span className="text-sm font-medium text-slate-400">Risk Score</span>
          <NeonBadge
            className={cn("font-mono tabular-nums", triageRiskScoreBadgeClass(riskScore))}
          >
            {riskScore}
          </NeonBadge>
        </div>
      ) : null}
      {chips.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {chips.map((chip) => (
            <NeonBadge key={chip.label} className={chip.className}>
              {chip.label}
            </NeonBadge>
          ))}
        </div>
      ) : null}
    </div>
  )
}

export function InvestigationContent() {
  const params = useParams()
  const recordId = typeof params.id === "string" ? params.id : ""

  const [event, setEvent] = useState<StoredEventRecord | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [timelineRefresh, setTimelineRefresh] = useState(0)

  const load = useCallback(async () => {
    if (!recordId) {
      setError("Missing record id")
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    const t0 = performance.now()
    try {
      investigationLog("load.start", { recordId })
      const data = await backendFetch<StoredEventRecord>(`/storage/events/${recordId}`)
      const payload = asRecord(data.payload)
      const summary = summarizeStoredEventPayload(payload)
      investigationLog("load.record_ok", {
        recordId,
        elapsedMs: Math.round(performance.now() - t0),
        tsoc_record_type: data.tsoc_record_type,
        sid: data.sid,
        ...summary,
      })

      const tEnrich = performance.now()
      const enriched = await enrichEventWithAdminOrgGap(data)
      investigationLog("load.enrich_done", {
        recordId,
        enrichMs: Math.round(performance.now() - tEnrich),
        totalMs: Math.round(performance.now() - t0),
        ...summarizeStoredEventPayload(asRecord(enriched.payload)),
      })
      setEvent(enriched)
    } catch (e) {
      setEvent(null)
      const message = e instanceof ApiError ? e.message : "Failed to load investigation"
      investigationLog(
        "load.failed",
        {
          recordId,
          elapsedMs: Math.round(performance.now() - t0),
          status: e instanceof ApiError ? e.status : undefined,
          message,
          body: e instanceof ApiError ? e.body : undefined,
        },
        "error"
      )
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [recordId])

  useEffect(() => {
    void load()
  }, [load])

  const description = useMemo(() => {
    if (event) {
      return [event.search_name, event.sid].filter(Boolean).join(" · ") || `Record ${recordId}`
    }
    return `Record ${recordId}`
  }, [event, recordId])

  return (
    <div className="grid gap-4">
      <NeonGlassCard accent="orange">
        <NeonCardHeader
          accent="orange"
          icon={<FileSearchIcon className="size-5 text-orange-400" />}
          title="Investigation"
          description={description}
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <InvestigationExportButton
                event={event}
                track="security"
                accent="orange"
                disabled={loading || !!error}
              />
              <Link
                href="/analysis"
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-md border border-orange-500/30 px-3 py-2 text-sm font-medium text-orange-300 transition-colors hover:bg-orange-500/10"
                )}
              >
                <ArrowLeftIcon className="size-4" />
                Back to Analysis
              </Link>
            </div>
          }
        />
        {event && !loading && !error ? <InvestigationHeaderChips event={event} /> : null}
      </NeonGlassCard>

      {loading ? (
        <InvestigationLoadingSkeleton />
      ) : error ? (
        <NeonAlert variant="destructive">
          <NeonAlertTitle>Error</NeonAlertTitle>
          <NeonAlertDescription>{error}</NeonAlertDescription>
        </NeonAlert>
      ) : event ? (
        <StorageEventDetail
          event={event}
          variant="investigation"
          investigationRecordId={recordId}
          timelineRefreshKey={timelineRefresh}
          onAnalystActionRecorded={() => setTimelineRefresh((n) => n + 1)}
        />
      ) : (
        <p className="text-sm text-slate-500">Record not found</p>
      )}
    </div>
  )
}
