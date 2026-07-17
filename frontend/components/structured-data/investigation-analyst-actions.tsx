"use client"

import { useCallback, useEffect, useState } from "react"
import { CheckCircle2Icon, Loader2Icon, ShieldAlertIcon } from "lucide-react"

import {
  NeonActionButton,
  NeonAlert,
  NeonAlertDescription,
  NeonAlertTitle,
  NeonBadge,
  NeonCardHeader,
  NeonField,
  NeonFieldLabel,
  NeonGlassCard,
  NeonInput,
} from "@/components/neon-glass"
import { ApiError } from "@/lib/api/client"
import {
  fetchAnalystActions,
  postAnalystAction,
  type AnalystActionEntry,
} from "@/lib/api/investigation-workflow"
import { formatEventCreatedAt } from "@/lib/storage-events"
import { cn } from "@/lib/utils"

function actionLabel(action: string | null | undefined): string {
  if (!action) return "—"
  return action === "acknowledge" ? "Acknowledged" : action === "escalate" ? "Escalated" : action
}

function LatestDecision({ entry }: { entry: AnalystActionEntry }) {
  const isEscalate = entry.action === "escalate"
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] px-4 py-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <NeonBadge
          className={cn(
            isEscalate ? "border-rose-500/40 text-rose-300" : "border-emerald-500/40 text-emerald-300"
          )}
        >
          {actionLabel(entry.action)}
        </NeonBadge>
        <span className="text-xs text-slate-500">{formatEventCreatedAt(entry.created_at)}</span>
      </div>
      {entry.note ? <p className="mt-2 text-slate-300">{entry.note}</p> : null}
      {entry.recommended_step ? (
        <p className="mt-2 text-xs text-slate-500">
          Recommended step at action: <span className="text-slate-400">{entry.recommended_step}</span>
        </p>
      ) : null}
    </div>
  )
}

type InvestigationAnalystActionsProps = {
  recordId: string
  disabled?: boolean
  onActionRecorded?: (action: "acknowledge" | "escalate") => void
}

export function InvestigationAnalystActions({
  recordId,
  disabled = false,
  onActionRecorded,
}: InvestigationAnalystActionsProps) {
  const [latest, setLatest] = useState<AnalystActionEntry | null>(null)
  const [note, setNote] = useState("")
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState<"acknowledge" | "escalate" | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!recordId) return
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAnalystActions(recordId)
      setLatest(data.results?.[0] ?? null)
    } catch (e) {
      const message =
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : "Failed to load analyst actions"
      setLatest(null)
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [recordId])

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timer)
  }, [load])

  const submit = async (action: "acknowledge" | "escalate") => {
    if (!recordId || disabled) return
    setSubmitting(action)
    setError(null)
    try {
      const res = await postAnalystAction(recordId, {
        action,
        note: note.trim() || undefined,
      })
      setLatest(res.latest ?? res.results?.[0] ?? null)
      setNote("")
      onActionRecorded?.(action)
    } catch (e) {
      const message =
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : "Failed to save decision"
      setError(message)
    } finally {
      setSubmitting(null)
    }
  }

  return (
    <NeonGlassCard accent="violet">
      <NeonCardHeader
        accent="violet"
        icon={<CheckCircle2Icon className="size-5 text-violet-400" />}
        title="Analyst gate"
        description="Acknowledge starts verified-runbook compilation; Escalate is recorded for human review"
      />
      <div className="space-y-4 px-6 pb-6">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Loader2Icon className="size-4 animate-spin" />
            Loading…
          </div>
        ) : null}

        {latest && !loading ? <LatestDecision entry={latest} /> : null}

        <NeonField>
          <NeonFieldLabel htmlFor="analyst-note">Optional note</NeonFieldLabel>
          <NeonInput
            id="analyst-note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Context for handoff or closure"
            disabled={disabled || !!submitting}
          />
        </NeonField>

        <div className="flex flex-wrap gap-2">
          <NeonActionButton
            type="button"
            disabled={disabled || !!submitting}
            onClick={() => void submit("acknowledge")}
          >
            {submitting === "acknowledge" ? (
              <Loader2Icon className="size-4 animate-spin" />
            ) : (
              <CheckCircle2Icon className="size-4" />
            )}
            Acknowledge
          </NeonActionButton>
          <NeonActionButton
            type="button"
            className="border-rose-500/40 text-rose-300 hover:bg-rose-500/10"
            disabled={disabled || !!submitting}
            onClick={() => void submit("escalate")}
          >
            {submitting === "escalate" ? (
              <Loader2Icon className="size-4 animate-spin" />
            ) : (
              <ShieldAlertIcon className="size-4" />
            )}
            Escalate
          </NeonActionButton>
        </div>

        {error ? (
          <NeonAlert variant="destructive">
            <NeonAlertTitle>Could not record decision</NeonAlertTitle>
            <NeonAlertDescription>{error}</NeonAlertDescription>
          </NeonAlert>
        ) : null}
      </div>
    </NeonGlassCard>
  )
}
