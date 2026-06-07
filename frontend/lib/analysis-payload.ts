import { getStorageEventId } from "@/lib/storage-events"

export type SourceTrack = "security" | "observability"

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return isRecord(value) ? value : null
}

function recordTypeFromEvent(event: Record<string, unknown>): string {
  const payload = asRecord(event.payload) ?? {}
  return String(event.tsoc_record_type ?? payload.tsoc_record_type ?? "")
}

export function getRecordSourceTrack(event: Record<string, unknown>): SourceTrack {
  const explicit = event.source_track ?? (asRecord(event.payload) ?? {}).source_track
  if (explicit === "observability" || explicit === "security") {
    return explicit
  }

  const recordType = recordTypeFromEvent(event)
  if (recordType === "observability_analysis") return "observability"

  const payload = asRecord(event.payload) ?? {}
  const analysis = asRecord(payload.analysis)
  if (analysis?.ops_judge != null) return "observability"
  if (analysis?.judge != null) return "security"

  return "security"
}

export function pickSecurityAnalysis(payload: Record<string, unknown>): Record<string, unknown> | null {
  const analysis = asRecord(payload.analysis)
  if (analysis && analysis.ops_judge == null) return analysis

  const security = asRecord(payload.security_result)
  if (security) return security

  const out = asRecord(payload.analysis_output)
  const nested = out ? asRecord(out.security_result) : null
  return nested
}

export function pickObservabilityAnalysis(payload: Record<string, unknown>): Record<string, unknown> | null {
  const observability = asRecord(payload.observability_result)
  if (observability) return observability

  const analysis = asRecord(payload.analysis)
  if (analysis && (analysis.ops_judge != null || analysis.track === "observability")) {
    return analysis
  }

  const out = asRecord(payload.analysis_output)
  const nested = out ? asRecord(out.observability_result) : null
  if (nested) return nested

  if (payload.tsoc_record_type === "observability_analysis" && analysis) {
    return analysis
  }

  return null
}

export function investigationHrefForRow(row: Record<string, unknown>): string | null {
  const id = getStorageEventId(row)
  if (!id) return null

  const track =
    row.source_track === "observability" || row.source_track === "security"
      ? row.source_track
      : row.tsoc_record_type === "observability_analysis"
        ? "observability"
        : "security"

  if (track === "observability") {
    return `/analysis/ops-investigation/${id}`
  }
  return `/analysis/investigation/${id}`
}
