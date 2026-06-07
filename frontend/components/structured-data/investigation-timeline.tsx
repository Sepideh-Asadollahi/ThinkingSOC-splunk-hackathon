"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { ClockIcon, Loader2Icon } from "lucide-react"

import {
  NeonActionButton,
  NeonAlert,
  NeonAlertDescription,
  NeonAlertTitle,
  NeonBadge,
  NeonCardHeader,
  NeonGlassCard,
} from "@/components/neon-glass"
import { ApiError } from "@/lib/api/client"
import {
  fetchInvestigationTimeline,
  type InvestigationTimelineStep,
} from "@/lib/api/investigation-workflow"
import { formatEventCreatedAt } from "@/lib/storage-events"
import { cn } from "@/lib/utils"

const DEFAULT_VISIBLE_STEPS = 4

function TimelineStepRow({ step, isLast }: { step: InvestigationTimelineStep; isLast: boolean }) {
  return (
    <li className="relative flex gap-3 pb-6 last:pb-0">
      {!isLast ? (
        <span
          className="absolute left-[7px] top-4 h-[calc(100%-0.5rem)] w-px bg-white/15"
          aria-hidden
        />
      ) : null}
      <span
        className={cn(
          "relative z-10 mt-1 size-3.5 shrink-0 rounded-full border-2",
          step.is_analyst_action
            ? "border-emerald-400/80 bg-emerald-500/30"
            : step.is_current_record
              ? "border-orange-400/80 bg-orange-500/40"
              : "border-white/30 bg-white/10"
        )}
        aria-hidden
      />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <p className="text-sm font-medium text-slate-100">{step.title}</p>
          <time className="shrink-0 text-xs text-slate-500" dateTime={String(step.created_at ?? "")}>
            {formatEventCreatedAt(step.created_at)}
          </time>
        </div>
        <p className="mt-0.5 text-xs text-slate-400">{step.description}</p>
        {step.detail ? (
          <p className="mt-1 text-xs text-slate-300">{step.detail}</p>
        ) : null}
        {step.is_current_record ? (
          <p className="mt-1 text-[10px] uppercase tracking-wide text-orange-400/90">This record</p>
        ) : null}
      </div>
    </li>
  )
}

function TimelineStepControls({
  total,
  expanded,
  onToggle,
}: {
  total: number
  expanded: boolean
  onToggle: () => void
}) {
  const hidden = Math.max(0, total - DEFAULT_VISIBLE_STEPS)
  const canCollapse = hidden > 0

  return (
    <div
      className="mb-4 flex flex-wrap items-center gap-2"
      data-testid="investigation-timeline-controls"
    >
      <NeonBadge className="border-teal-500/30 text-teal-300">
        {total} {total === 1 ? "step" : "steps"}
      </NeonBadge>
      {canCollapse ? (
        <NeonActionButton
          type="button"
          size="sm"
          accent="teal"
          onClick={onToggle}
          aria-expanded={expanded}
        >
          {expanded ? "Show less" : `Show ${hidden} more`}
        </NeonActionButton>
      ) : null}
    </div>
  )
}

type InvestigationTimelineProps = {
  recordId: string
  refreshKey?: number
}

export function InvestigationTimeline({ recordId, refreshKey = 0 }: InvestigationTimelineProps) {
  const [steps, setSteps] = useState<InvestigationTimelineStep[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [scopeLabel, setScopeLabel] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!recordId) return
    setLoading(true)
    setError(null)
    try {
      const data = await fetchInvestigationTimeline(recordId)
      setSteps(data.steps ?? [])
      const parts = [
        data.search_name,
        data.sid ? `SID ${data.sid}` : null,
        data.row_index != null ? `row ${data.row_index}` : null,
      ].filter(Boolean)
      setScopeLabel(parts.length > 0 ? parts.join(" · ") : null)
    } catch (e) {
      const message =
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : "Failed to load timeline"
      setSteps([])
      setScopeLabel(null)
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [recordId])

  useEffect(() => {
    void load()
  }, [load, refreshKey])

  useEffect(() => {
    setExpanded(false)
  }, [steps.length, recordId])

  const visibleSteps = useMemo(() => {
    if (expanded || steps.length <= DEFAULT_VISIBLE_STEPS) return steps
    return steps.slice(0, DEFAULT_VISIBLE_STEPS)
  }, [expanded, steps])

  return (
    <NeonGlassCard accent="teal">
      <NeonCardHeader
        accent="teal"
        icon={<ClockIcon className="size-5 text-teal-400" />}
        title="Event timeline"
        description={
          scopeLabel
            ? `Pipeline for this alert only — ${scopeLabel}`
            : "Pipeline for this alert (ingest → classify → analysis → your decisions)"
        }
      />
      <div className="px-6 pb-6">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-slate-400" aria-busy="true">
            <Loader2Icon className="size-4 animate-spin" />
            Loading timeline…
          </div>
        ) : error ? (
          <NeonAlert variant="destructive" className="mt-0">
            <NeonAlertTitle>Timeline unavailable</NeonAlertTitle>
            <NeonAlertDescription>{error}</NeonAlertDescription>
          </NeonAlert>
        ) : steps.length === 0 ? (
          <p className="text-sm text-slate-500">No pipeline steps found for this alert.</p>
        ) : (
          <>
            <TimelineStepControls
              total={steps.length}
              expanded={expanded}
              onToggle={() => setExpanded((v) => !v)}
            />
            <ol className="list-none pl-0" data-testid="investigation-timeline-steps">
              {visibleSteps.map((step, i) => (
                <TimelineStepRow
                  key={`${step.record_id}-${i}`}
                  step={step}
                  isLast={i === visibleSteps.length - 1}
                />
              ))}
            </ol>
          </>
        )}
      </div>
    </NeonGlassCard>
  )
}
