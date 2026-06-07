export function triageVerdictBadgeClass(verdict: string): string {
  if (verdict === "TRUE_POSITIVE") return "border-red-500/40 text-red-300"
  if (verdict === "FALSE_POSITIVE") return "border-emerald-500/30 text-emerald-300"
  return "border-amber-500/40 text-amber-300"
}

export function triagePriorityBadgeClass(priority: string): string {
  if (priority === "critical") return "border-red-500/50 text-red-200"
  if (priority === "high") return "border-orange-500/40 text-orange-300"
  if (priority === "medium") return "border-yellow-500/30 text-yellow-200"
  return "border-white/15 text-slate-400"
}

export function formatReviewVerdictLabel(verdict: string): string {
  return verdict.replace(/_/g, " ").trim()
}

export function formatInvestigationPriorityLabel(priority: string): string | null {
  const normalized = priority.trim().toLowerCase()
  if (!normalized || normalized === "—") return null
  if (normalized === "critical" || normalized === "high") {
    return `${normalized.toUpperCase()} priority`
  }
  return null
}

/** Round triage score from nested triage object or payload root. */
export function pickTriageRiskScore(
  triage: Record<string, unknown> | null | undefined,
  payload?: Record<string, unknown> | null
): number | null {
  const fromTriage = triage?.triage_score
  if (typeof fromTriage === "number" && Number.isFinite(fromTriage)) {
    return Math.round(fromTriage)
  }
  const fromPayload = payload?.triage_score
  if (typeof fromPayload === "number" && Number.isFinite(fromPayload)) {
    return Math.round(fromPayload)
  }
  return null
}

/** Badge classes for triage_score — aligned with investigation_priority bands (docs/08). */
export function triageRiskScoreBadgeClass(score: number): string {
  if (score >= 80) return "border-red-500/50 bg-red-500/10 text-red-200"
  if (score >= 60) return "border-orange-500/40 bg-orange-500/10 text-orange-300"
  if (score >= 40) return "border-yellow-500/30 bg-yellow-500/10 text-yellow-200"
  return "border-white/15 bg-white/5 text-slate-400"
}

/** Analyst headline: ``CRITICAL priority — NEEDS HUMAN REVIEW — score 82`` (matches backend triage report). */
export function formatTriageHeadline(triage: Record<string, unknown> | null | undefined): string | null {
  if (!triage) return null

  const report =
    triage.report && typeof triage.report === "object"
      ? (triage.report as Record<string, unknown>)
      : null
  const reportHeadline = typeof report?.headline === "string" ? report.headline.trim() : ""
  if (reportHeadline) {
    return reportHeadline.replace(/\.$/, "")
  }

  const parts: string[] = []
  const priorityLabel = formatInvestigationPriorityLabel(String(triage.investigation_priority ?? ""))
  if (priorityLabel) parts.push(priorityLabel)

  const review = String(triage.review_verdict ?? "").trim()
  if (review) parts.push(formatReviewVerdictLabel(review))

  const score = triage.triage_score
  if (typeof score === "number" && Number.isFinite(score)) {
    parts.push(`score ${Math.round(score)}`)
  }

  return parts.length > 0 ? parts.join(" — ") : null
}
