/** Client-side diagnostics for investigation / storage event loads (browser DevTools). */

const PREFIX = "[tsoc/investigation]"

export type InvestigationLogMeta = Record<string, unknown>

function formatMeta(meta?: InvestigationLogMeta): string {
  if (!meta || Object.keys(meta).length === 0) return ""
  try {
    return ` ${JSON.stringify(meta)}`
  } catch {
    return " [meta unserializable]"
  }
}

export function investigationLog(
  step: string,
  meta?: InvestigationLogMeta,
  level: "log" | "warn" | "error" = "log"
): void {
  if (typeof window === "undefined") return
  const msg = `${PREFIX} ${step}${formatMeta(meta)}`
  if (level === "error") console.error(msg)
  else if (level === "warn") console.warn(msg)
  else console.info(msg)
}

/** Log only storage/events API traffic from the shared fetch client. */
export function storageApiLog(
  step: string,
  meta?: InvestigationLogMeta,
  level: "log" | "warn" | "error" = "log"
): void {
  if (typeof window === "undefined") return
  const msg = `[tsoc/api] ${step}${formatMeta(meta)}`
  if (level === "error") console.error(msg)
  else if (level === "warn") console.warn(msg)
  else console.info(msg)
}

export function summarizeStoredEventPayload(payload: Record<string, unknown> | null | undefined) {
  if (!payload) return { hasPayload: false }
  const analysis =
    payload.analysis && typeof payload.analysis === "object"
      ? (payload.analysis as Record<string, unknown>)
      : payload.security_result && typeof payload.security_result === "object"
        ? (payload.security_result as Record<string, unknown>)
        : null
  const iq = analysis?.investigation_questions
  const iqList = Array.isArray(iq) ? iq : []
  let splRows = 0
  for (const item of iqList) {
    if (!item || typeof item !== "object") continue
    const sr = (item as Record<string, unknown>).spl_results
    if (sr && typeof sr === "object" && Array.isArray((sr as Record<string, unknown>).rows)) {
      splRows += (sr as { rows: unknown[] }).rows.length
    }
  }
  return {
    hasPayload: true,
    payloadKeys: Object.keys(payload),
    hasAnalysis: !!analysis,
    investigationQuestions: iqList.length,
    splResultRowsTotal: splRows,
    hasTriage: payload.triage != null || analysis?.triage != null,
    hasRawAlert: payload.raw_alert != null,
    hasAdminOrgGap:
      analysis != null &&
      Boolean(
        (analysis.admin_org_gap as Record<string, unknown> | undefined)?.should_suggest_question &&
          String((analysis.admin_org_gap as Record<string, unknown>).question_for_admin ?? "").trim()
      ),
  }
}
