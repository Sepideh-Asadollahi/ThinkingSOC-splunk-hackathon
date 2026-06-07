function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return isRecord(value) ? value : null
}

export function formatEventCreatedAt(createdAt: unknown): string {
  if (createdAt == null || createdAt === "") return "—"
  const text = String(createdAt)
  const date = new Date(text)
  if (Number.isNaN(date.getTime())) return text
  return date.toLocaleString()
}

export function getEventVerdict(event: Record<string, unknown>): string {
  const payload = asRecord(event.payload) ?? {}
  const analysis = asRecord(payload.analysis)
  const judge = analysis ? asRecord(analysis.judge) : null
  if (judge && judge.verdict != null) return String(judge.verdict)

  const opsJudge = analysis ? asRecord(analysis.ops_judge) : null
  if (opsJudge && opsJudge.verdict != null) return String(opsJudge.verdict)

  const output = asRecord(payload.analysis_output)
  if (output && output.verdict != null) return String(output.verdict)

  return "—"
}

export function getEventSummary(event: Record<string, unknown>): string | null {
  const payload = asRecord(event.payload) ?? {}
  const analysis = asRecord(payload.analysis)
  if (analysis && typeof analysis.summary === "string" && analysis.summary) {
    return analysis.summary
  }
  if (typeof payload.phase === "string") return payload.phase
  return null
}

export function getStorageEventId(event: Record<string, unknown>): string | null {
  if (event.id != null) return String(event.id)
  return null
}
