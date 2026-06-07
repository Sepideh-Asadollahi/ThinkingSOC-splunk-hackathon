"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useParams } from "next/navigation"
import { ActivityIcon, ArrowLeftIcon } from "lucide-react"

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
import { pickTriageFromPayload } from "@/components/structured-data/triage-section"
import { asRecord } from "@/components/structured-data/utils"
import { pickObservabilityAnalysis } from "@/lib/analysis-payload"
import { ApiError, backendFetch } from "@/lib/api/client"
import type { StoredEventRecord } from "@/lib/api/types"
import { triagePriorityBadgeClass, triageVerdictBadgeClass } from "@/lib/triage-display"
import { cn } from "@/lib/utils"

function OpsInvestigationLoadingSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading ops investigation">
      <div className="h-24 animate-pulse rounded-xl border border-white/10 bg-white/[0.03]" />
      <div className="grid gap-4 md:grid-cols-2">
        <div className="h-40 animate-pulse rounded-xl border border-white/10 bg-white/[0.03]" />
        <div className="h-40 animate-pulse rounded-xl border border-white/10 bg-white/[0.03]" />
      </div>
      <div className="h-56 animate-pulse rounded-xl border border-white/10 bg-white/[0.03]" />
    </div>
  )
}

function OpsInvestigationHeaderChips({ event }: { event: StoredEventRecord }) {
  const payload = asRecord(event.payload) ?? {}
  const triage = pickTriageFromPayload(payload)
  const analysis = pickObservabilityAnalysis(payload)
  const opsJudge = analysis ? asRecord(analysis.ops_judge) : null

  const reviewVerdict = triage ? String(triage.review_verdict ?? "") : ""
  const invPriority = triage ? String(triage.investigation_priority ?? "") : ""
  const opsVerdict = opsJudge ? String(opsJudge.verdict ?? "") : ""
  const opsPriority = opsJudge ? String(opsJudge.priority ?? "") : ""

  const chips: { label: string; className: string }[] = []
  if (reviewVerdict) {
    chips.push({ label: reviewVerdict, className: triageVerdictBadgeClass(reviewVerdict) })
  }
  if (invPriority) {
    chips.push({ label: `Priority: ${invPriority}`, className: triagePriorityBadgeClass(invPriority) })
  }
  if (opsVerdict) {
    chips.push({ label: `Ops: ${opsVerdict}`, className: "border-teal-500/40 text-teal-300" })
  }
  if (opsPriority) {
    chips.push({ label: opsPriority, className: triagePriorityBadgeClass(opsPriority) })
  }

  if (chips.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2 px-6 pb-2">
      {chips.map((chip) => (
        <NeonBadge key={chip.label} className={chip.className}>
          {chip.label}
        </NeonBadge>
      ))}
    </div>
  )
}

export function OpsInvestigationContent() {
  const params = useParams()
  const recordId = typeof params.id === "string" ? params.id : ""

  const [event, setEvent] = useState<StoredEventRecord | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!recordId) {
      setError("Missing record id")
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const data = await backendFetch<StoredEventRecord>(`/storage/events/${recordId}`)
      setEvent(data)
    } catch (e) {
      setEvent(null)
      setError(e instanceof ApiError ? e.message : "Failed to load ops investigation")
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
      <NeonGlassCard accent="teal">
        <NeonCardHeader
          accent="teal"
          icon={<ActivityIcon className="size-5 text-teal-400" />}
          title="Ops investigation"
          description={description}
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <InvestigationExportButton
                event={event}
                track="observability"
                accent="teal"
                disabled={loading || !!error}
              />
              <Link
                href="/analysis"
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-md border border-teal-500/30 px-3 py-2 text-sm font-medium text-teal-300 transition-colors hover:bg-teal-500/10"
                )}
              >
                <ArrowLeftIcon className="size-4" />
                Back to Analysis
              </Link>
            </div>
          }
        />
        {event && !loading && !error ? <OpsInvestigationHeaderChips event={event} /> : null}
      </NeonGlassCard>

      {loading ? (
        <OpsInvestigationLoadingSkeleton />
      ) : error ? (
        <NeonAlert variant="destructive">
          <NeonAlertTitle>Error</NeonAlertTitle>
          <NeonAlertDescription>{error}</NeonAlertDescription>
        </NeonAlert>
      ) : event ? (
        <StorageEventDetail event={event} variant="ops-investigation" />
      ) : (
        <p className="text-sm text-slate-500">Record not found</p>
      )}
    </div>
  )
}
