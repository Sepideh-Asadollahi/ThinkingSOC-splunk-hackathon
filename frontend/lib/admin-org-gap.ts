export type AdminOrgGap = {
  should_suggest_question: boolean
  gap_summary: string
  question_for_admin: string
  notes?: string | null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

export function normalizeAdminOrgGap(raw: unknown): AdminOrgGap | null {
  if (!isRecord(raw)) return null
  return {
    should_suggest_question: Boolean(raw.should_suggest_question),
    gap_summary: String(raw.gap_summary ?? "").trim(),
    question_for_admin: String(raw.question_for_admin ?? "").trim(),
    notes: raw.notes != null && String(raw.notes).trim() ? String(raw.notes).trim() : null,
  }
}

export function hasActiveAdminOrgGap(gap: AdminOrgGap | null): boolean {
  return Boolean(gap?.should_suggest_question && gap.question_for_admin)
}

/** Collect gap objects from every known payload shape (soc_analysis, route, audit). */
export function collectAdminOrgGapCandidates(
  source: Record<string, unknown> | null | undefined
): AdminOrgGap[] {
  if (!source) return []
  const out: AdminOrgGap[] = []
  const push = (raw: unknown) => {
    const g = normalizeAdminOrgGap(raw)
    if (g) out.push(g)
  }

  push(source.admin_org_gap)
  const analysis = isRecord(source.analysis) ? source.analysis : null
  if (analysis) push(analysis.admin_org_gap)
  const security = isRecord(source.security_result) ? source.security_result : null
  if (security) push(security.admin_org_gap)
  const analysisOutput = isRecord(source.analysis_output) ? source.analysis_output : null
  if (analysisOutput) {
    const nested = isRecord(analysisOutput.security_result) ? analysisOutput.security_result : null
    if (nested) push(nested.admin_org_gap)
  }
  return out
}

/** Prefer an active gap; otherwise return the first normalized candidate. */
export function pickAdminOrgGap(
  source: Record<string, unknown> | null | undefined
): AdminOrgGap | null {
  const candidates = collectAdminOrgGapCandidates(source)
  if (!candidates.length) return null
  return candidates.find(hasActiveAdminOrgGap) ?? candidates[0]!
}

/** Gap from standalone admin_org_gap_suggest storage record. */
export function adminOrgGapFromStoragePayload(payload: Record<string, unknown>): AdminOrgGap | null {
  const response = normalizeAdminOrgGap(payload.response)
  if (response) return response
  return normalizeAdminOrgGap(payload)
}

/** Pick the best active gap from a list of storage event rows (newest first). */
export function pickActiveAdminOrgGapFromStorageRows(
  rows: Record<string, unknown>[] | undefined
): AdminOrgGap | null {
  if (!rows?.length) return null
  for (const row of rows) {
    const payload = isRecord(row.payload) ? row.payload : row
    const gap = adminOrgGapFromStoragePayload(payload)
    if (hasActiveAdminOrgGap(gap)) return gap
  }
  for (const row of rows) {
    const payload = isRecord(row.payload) ? row.payload : row
    const gap = adminOrgGapFromStoragePayload(payload)
    if (gap) return gap
  }
  return null
}

/** Merge admin_org_gap onto a SOC analysis object from payload + embedded fields. */
export function mergeAdminOrgGapIntoAnalysis(
  analysis: Record<string, unknown> | null,
  payload: Record<string, unknown>
): Record<string, unknown> | null {
  if (!analysis) return null
  const candidates = [
    ...collectAdminOrgGapCandidates(analysis),
    ...collectAdminOrgGapCandidates(payload),
  ]
  const best = candidates.find(hasActiveAdminOrgGap) ?? candidates[0]
  if (!best) return analysis
  return { ...analysis, admin_org_gap: best }
}
