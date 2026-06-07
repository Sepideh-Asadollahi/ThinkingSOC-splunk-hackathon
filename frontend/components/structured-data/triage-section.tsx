"use client"

import { NeonBadge } from "@/components/neon-glass"
import { triagePriorityBadgeClass, triageVerdictBadgeClass } from "@/lib/triage-display"

import { DataSection } from "./section"
import { asRecord, isRecord } from "./utils"

export function pickTriageFromPayload(payload: Record<string, unknown>): Record<string, unknown> | null {
  const top = asRecord(payload.triage)
  if (top) return top
  return pickTriageFromAnalysis(payload)
}

export function pickTriageFromAnalysis(data: Record<string, unknown>): Record<string, unknown> | null {
  const direct = asRecord(data.triage)
  if (direct) return direct

  const analysis = asRecord(data.analysis)
  if (analysis) {
    const nested = asRecord(analysis.triage)
    if (nested) return nested
  }

  const security = asRecord(data.security_result)
  if (security) {
    const nested = asRecord(security.triage)
    if (nested) return nested
  }

  const out = asRecord(data.analysis_output)
  if (out) {
    const nested = asRecord(out.triage)
    if (nested) return nested
  }
  return null
}

function TriageReportBlock({ report }: { report: Record<string, unknown> }) {
  const factors = Array.isArray(report.factors) ? report.factors : []
  const signalNotes = Array.isArray(report.signal_notes) ? report.signal_notes : []

  return (
    <div className="mt-4 space-y-4 border-t border-white/10 pt-4">
      {typeof report.headline === "string" && report.headline ? (
        <p className="text-base font-medium leading-snug text-slate-100">{report.headline}</p>
      ) : null}

      {typeof report.why_verdict === "string" && report.why_verdict ? (
        <div>
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-orange-400/90">
            Why this verdict
          </h4>
          <p className="text-sm leading-relaxed text-slate-300">{report.why_verdict}</p>
        </div>
      ) : null}

      {typeof report.why_priority === "string" && report.why_priority ? (
        <div>
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-violet-400/90">
            Why this priority
          </h4>
          <p className="text-sm leading-relaxed text-slate-300">{report.why_priority}</p>
        </div>
      ) : null}

      {typeof report.recommended_action === "string" && report.recommended_action ? (
        <div className="rounded-md border border-teal-500/25 bg-teal-500/5 p-3">
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-teal-400/90">
            Recommended action
          </h4>
          <p className="text-sm leading-relaxed text-slate-200">{report.recommended_action}</p>
        </div>
      ) : null}

      {factors.length > 0 ? (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Score breakdown
          </h4>
          <ul className="space-y-2">
            {factors.map((item, i) => {
              const row = isRecord(item) ? item : {}
              const impact = row.score_impact
              return (
                <li
                  key={i}
                  className="rounded-md border border-white/10 bg-black/30 px-3 py-2 text-sm"
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="font-medium text-slate-200">{String(row.title ?? "—")}</span>
                    {impact != null && impact !== "" ? (
                      <span
                        className={
                          Number(impact) < 0
                            ? "font-mono text-xs text-red-300/90"
                            : "font-mono text-xs text-emerald-300/90"
                        }
                      >
                        {Number(impact) > 0 ? "+" : ""}
                        {String(impact)} pts
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-slate-400">
                    {String(row.explanation ?? "")}
                  </p>
                </li>
              )
            })}
          </ul>
        </div>
      ) : null}

      {signalNotes.length > 0 ? (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-400/80">
            Escalation notes
          </h4>
          <ul className="list-disc space-y-1 pl-4 text-sm text-slate-300">
            {signalNotes.map((note, i) => (
              <li key={i}>{String(note)}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}

export function TriagePanelContent({ triage }: { triage: Record<string, unknown> }) {
  const reviewVerdict = String(triage.review_verdict ?? "—")
  const invPriority = String(triage.investigation_priority ?? "—")
  const score = triage.triage_score
  const signals = Array.isArray(triage.signals) ? triage.signals : []
  const report = asRecord(triage.report)

  return (
    <>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <NeonBadge className={triageVerdictBadgeClass(reviewVerdict)}>{reviewVerdict}</NeonBadge>
        <NeonBadge className={triagePriorityBadgeClass(invPriority)}>
          Priority: {invPriority}
        </NeonBadge>
        {score != null ? (
          <NeonBadge className="border-violet-500/30 text-violet-300">Score {String(score)}</NeonBadge>
        ) : null}
        {triage.needs_human_review === true ? (
          <NeonBadge className="border-amber-500/40 text-amber-200">Human review required</NeonBadge>
        ) : null}
      </div>

      {report ? (
        <TriageReportBlock report={report} />
      ) : (
        <>
          {typeof triage.priority_rationale === "string" && triage.priority_rationale ? (
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300">
              {triage.priority_rationale}
            </p>
          ) : null}
          {signals.length > 0 ? (
            <ul className="mt-2 flex flex-wrap gap-1">
              {signals.map((s, i) => (
                <li key={i}>
                  <NeonBadge className="border-white/10 text-xs text-slate-400">{String(s)}</NeonBadge>
                </li>
              ))}
            </ul>
          ) : null}
        </>
      )}
    </>
  )
}

export function TriageSection({ triage }: { triage: Record<string, unknown> }) {
  return (
    <DataSection
      title="Triage report"
      description="Post-analysis priority and reasoning for this alert"
      accent="orange"
      defaultOpen
    >
      <TriagePanelContent triage={triage} />
    </DataSection>
  )
}
