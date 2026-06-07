import { mergeAdminOrgGapIntoAnalysis } from "@/lib/admin-org-gap"
import {
  pickObservabilityAnalysis,
  pickSecurityAnalysis,
  type SourceTrack,
} from "@/lib/analysis-payload"
import type {
  InvestigationWorkflowExport,
} from "@/lib/api/investigation-workflow"
import { fetchInvestigationWorkflowForExport } from "@/lib/api/investigation-workflow"
import type { StoredEventRecord } from "@/lib/api/types"
import { parseOpsInvestigationAnalysis } from "@/components/structured-data/observability-analysis-view"
import {
  collectInvestigationRecommendedActions,
  parseInvestigationAnalysis,
} from "@/components/structured-data/soc-analysis-view"
import { pickThreatIntel } from "@/components/structured-data/threat-intel-panel"

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return isRecord(value) ? value : null
}

function pickTriageFromPayload(payload: Record<string, unknown>): Record<string, unknown> | null {
  const triage = asRecord(payload.triage)
  if (triage) return triage
  const analysis = asRecord(payload.analysis)
  return analysis ? asRecord(analysis.triage) : null
}

export type InvestigationExportTrack = Extract<SourceTrack, "security" | "observability">

/** Tab keys aligned with Security investigation UI (`investigation-tabbed-layout`). */
export const SECURITY_INVESTIGATION_SECTION_KEYS = [
  "overview",
  "recommended-action",
  "triage",
  "agents",
  "enrichment",
  "questions",
  "threat-intel",
  "framework",
  "admin-question",
  "technical",
] as const

/** Tab keys aligned with Observability investigation UI (`ops-investigation-tabbed-layout`). */
export const OPS_INVESTIGATION_SECTION_KEYS = [
  "overview",
  "entity",
  "impact",
  "diagnoser",
  "responder",
  "evidence",
  "technical",
] as const

export type SecurityInvestigationSectionKey = (typeof SECURITY_INVESTIGATION_SECTION_KEYS)[number]
export type OpsInvestigationSectionKey = (typeof OPS_INVESTIGATION_SECTION_KEYS)[number]

export type InvestigationExportBundle = {
  exported_at: string
  track: InvestigationExportTrack
  /** Tab keys present in `sections` (same rules as the Investigation UI). */
  sections_included: string[]
  /** Per-tab snapshots shown in the Investigation UI. */
  sections: Record<string, unknown>
  record: {
    id: number
    sid?: string | null
    search_name?: string | null
    created_at?: string | null
    tsoc_record_type?: string | null
    row_index?: number | null
  }
  triage: Record<string, unknown> | null
  classification: Record<string, unknown> | null
  analysis: Record<string, unknown> | null
  raw_alert: Record<string, unknown> | null
  analysis_input: Record<string, unknown> | null
  analysis_output: Record<string, unknown> | null
  phase: string | null
  content: unknown
  payload: Record<string, unknown>
  /** Security only: Analyst gate + Event timeline (same as Overview tab). */
  investigation_workflow: InvestigationWorkflowExport | null
}

function normalizeAnalysisForExport(
  event: StoredEventRecord,
  track: InvestigationExportTrack
): Record<string, unknown> | null {
  const payload = asRecord(event.payload) ?? {}
  const phase = typeof payload.phase === "string" ? payload.phase : null
  const content = payload.content
  const phaseThreatIntel =
    phase === "threat_intel" && isRecord(content) ? content : null

  if (track === "observability") {
    const raw = pickObservabilityAnalysis(payload)
    return raw ? { ...raw, triage: raw.triage ?? payload.triage } : null
  }

  const raw = pickSecurityAnalysis(payload)
  if (!raw) {
    return phaseThreatIntel ? { threat_intel: phaseThreatIntel } : null
  }

  const merged = mergeAdminOrgGapIntoAnalysis(
    {
      ...raw,
      triage: raw.triage ?? payload.triage,
      threat_intel: raw.threat_intel ?? payload.threat_intel ?? phaseThreatIntel,
    },
    payload
  )
  return merged
}

function buildTechnicalSection(bundle: {
  raw_alert: Record<string, unknown> | null
  analysis_input: Record<string, unknown> | null
  analysis_output: Record<string, unknown> | null
  phase: string | null
  content: unknown
}): Record<string, unknown> | null {
  const hasPhase = bundle.phase != null && bundle.content !== undefined
  const hasTechnical = Boolean(
    bundle.raw_alert || bundle.analysis_input || bundle.analysis_output || hasPhase
  )
  if (!hasTechnical) return null
  return {
    raw_alert: bundle.raw_alert,
    analysis_input: bundle.analysis_input,
    analysis_output: bundle.analysis_output,
    phase: bundle.phase,
    content: bundle.content,
  }
}

function appendOverviewWorkflow(
  overview: Record<string, unknown>,
  workflow: InvestigationWorkflowExport | null | undefined
): void {
  if (!workflow) return

  overview.analyst_gate = {
    count: workflow.analyst_actions?.count ?? 0,
    latest: workflow.analyst_actions?.results?.[0] ?? null,
    history: workflow.analyst_actions?.results ?? [],
  }

  if (workflow.event_timeline) {
    overview.event_timeline = {
      record_id: workflow.event_timeline.record_id,
      sid: workflow.event_timeline.sid,
      search_name: workflow.event_timeline.search_name,
      row_index: workflow.event_timeline.row_index ?? null,
      step_count: workflow.event_timeline.steps?.length ?? 0,
      steps: workflow.event_timeline.steps ?? [],
    }
  } else {
    overview.event_timeline = null
  }

  if (workflow.fetch_errors.length > 0) {
    overview.workflow_fetch_errors = workflow.fetch_errors
  }
}

export function buildSecurityInvestigationSections(
  bundle: Pick<
    InvestigationExportBundle,
    | "record"
    | "classification"
    | "triage"
    | "analysis"
    | "raw_alert"
    | "analysis_input"
    | "analysis_output"
    | "phase"
    | "content"
    | "investigation_workflow"
  >
): { sections: Record<string, unknown>; sections_included: string[] } {
  const sections: Record<string, unknown> = {}
  const included: string[] = []

  const overview: Record<string, unknown> = {}
  appendOverviewWorkflow(overview, bundle.investigation_workflow)
  overview.record = bundle.record
  overview.classification = bundle.classification
  if (bundle.analysis) {
    const parsed = parseInvestigationAnalysis(bundle.analysis)
    if (parsed.summary) overview.summary = parsed.summary
    if (parsed.hasAdminGap && parsed.adminOrgGap) overview.admin_org_gap = parsed.adminOrgGap
  } else if (bundle.triage) {
    overview.triage_only = bundle.triage
  }
  sections.overview = overview
  included.push("overview")

  const analysis = bundle.analysis
  if (analysis) {
    const parsed = parseInvestigationAnalysis(analysis)

    if (parsed.hasRecommendedActions) {
      sections["recommended-action"] = collectInvestigationRecommendedActions(analysis)
      included.push("recommended-action")
    }
    if (parsed.hasTriage && parsed.triage) {
      sections.triage = parsed.triage
      included.push("triage")
    }
    if (parsed.hasCourt) {
      sections.agents = {
        hunter: analysis.hunter ?? null,
        defender: analysis.defender ?? null,
        judge: parsed.judge,
      }
      included.push("agents")
    }
    if (parsed.hasEnrichment) {
      sections.enrichment = {
        enrichment: analysis.enrichment ?? null,
        inventory_user: analysis.inventory_user ?? null,
        inventory_asset: analysis.inventory_asset ?? null,
        risk_context: analysis.risk_context ?? null,
      }
      included.push("enrichment")
    }
    if (parsed.hasQuestions) {
      sections.questions = {
        investigation_questions: analysis.investigation_questions ?? null,
        root_cause_spl: analysis.root_cause_spl ?? null,
      }
      included.push("questions")
    }
    if (parsed.hasThreatIntel) {
      sections["threat-intel"] = pickThreatIntel(analysis) ?? analysis.threat_intel ?? null
      included.push("threat-intel")
    }
    if (parsed.hasFramework) {
      sections.framework = analysis.framework_mapping ?? null
      included.push("framework")
    }
    if (parsed.hasAdminGap && parsed.adminOrgGap) {
      sections["admin-question"] = parsed.adminOrgGap
      included.push("admin-question")
    }
  } else if (bundle.triage) {
    sections.triage = bundle.triage
    if (!included.includes("triage")) included.push("triage")
  }

  const technical = buildTechnicalSection(bundle)
  if (technical) {
    sections.technical = technical
    included.push("technical")
  }

  return { sections, sections_included: included }
}

export function buildOpsInvestigationSections(
  bundle: Pick<
    InvestigationExportBundle,
    | "record"
    | "classification"
    | "triage"
    | "analysis"
    | "raw_alert"
    | "analysis_input"
    | "analysis_output"
    | "phase"
    | "content"
  >
): { sections: Record<string, unknown>; sections_included: string[] } {
  const sections: Record<string, unknown> = {}
  const included: string[] = []

  const overview: Record<string, unknown> = {
    record: bundle.record,
    classification: bundle.classification,
  }
  if (bundle.analysis) {
    const parsed = parseOpsInvestigationAnalysis(bundle.analysis)
    if (parsed.summary) overview.summary = parsed.summary
    if (parsed.hasOpsJudge && parsed.opsJudge) overview.ops_judge = parsed.opsJudge
    if (parsed.triage) overview.triage = parsed.triage
  } else if (bundle.triage) {
    overview.triage_only = bundle.triage
  }
  sections.overview = overview
  included.push("overview")

  const analysis = bundle.analysis
  if (analysis) {
    const parsed = parseOpsInvestigationAnalysis(analysis)
    if (parsed.hasEntity) {
      sections.entity = analysis.entity_resolution ?? null
      included.push("entity")
    }
    if (parsed.hasImpact) {
      sections.impact = analysis.impact_context ?? null
      included.push("impact")
    }
    if (parsed.hasDiagnoser) {
      sections.diagnoser = analysis.diagnoser ?? null
      included.push("diagnoser")
    }
    if (parsed.hasResponder) {
      sections.responder = analysis.responder ?? null
      included.push("responder")
    }
    if (parsed.hasEvidence) {
      sections.evidence = analysis.evidence_refs ?? null
      included.push("evidence")
    }
  } else if (bundle.triage) {
    sections.triage = bundle.triage
    included.push("triage")
  }

  const technical = buildTechnicalSection(bundle)
  if (technical) {
    sections.technical = technical
    included.push("technical")
  }

  return { sections, sections_included: included }
}

export function buildInvestigationExport(
  event: StoredEventRecord,
  track: InvestigationExportTrack,
  investigationWorkflow?: InvestigationWorkflowExport | null
): InvestigationExportBundle {
  const payload = asRecord(event.payload) ?? {}
  const analysis = normalizeAnalysisForExport(event, track)

  const base = {
    exported_at: new Date().toISOString(),
    track,
    record: {
      id: event.id,
      sid: event.sid ?? (typeof payload.sid === "string" ? payload.sid : null),
      search_name:
        event.search_name ??
        (typeof payload.search_name === "string" ? payload.search_name : null),
      created_at: event.created_at ?? null,
      tsoc_record_type:
        event.tsoc_record_type ??
        (typeof payload.tsoc_record_type === "string" ? payload.tsoc_record_type : null),
      row_index: event.row_index ?? null,
    },
    triage: pickTriageFromPayload(payload),
    classification: asRecord(payload.classification),
    analysis,
    raw_alert: asRecord(payload.raw_alert) ?? asRecord((event as Record<string, unknown>).raw_alert),
    analysis_input: asRecord(payload.analysis_input),
    analysis_output: asRecord(payload.analysis_output),
    phase: typeof payload.phase === "string" ? payload.phase : null,
    content: payload.content,
    payload,
  }

  const workflow =
    track === "security" ? (investigationWorkflow ?? null) : null

  const baseWithWorkflow = { ...base, investigation_workflow: workflow }

  const sectionBundle =
    track === "observability"
      ? buildOpsInvestigationSections(baseWithWorkflow)
      : buildSecurityInvestigationSections(baseWithWorkflow)

  return {
    ...baseWithWorkflow,
    sections: sectionBundle.sections,
    sections_included: sectionBundle.sections_included,
  }
}

function slugPart(value: string | number | null | undefined, fallback: string): string {
  const raw = value == null || value === "" ? fallback : String(value)
  return raw.replace(/[^a-zA-Z0-9._-]+/g, "_").slice(0, 80)
}

export function investigationExportFilename(
  event: StoredEventRecord,
  track: InvestigationExportTrack
): string {
  const prefix = track === "observability" ? "ops-investigation" : "investigation"
  const sid = slugPart(event.sid, "no-sid")
  const id = slugPart(event.id, "record")
  const stamp = new Date().toISOString().slice(0, 10)
  return `${prefix}-${sid}-${id}-${stamp}.json`
}

function triggerJsonDownload(event: StoredEventRecord, track: InvestigationExportTrack, bundle: InvestigationExportBundle): void {
  const json = JSON.stringify(bundle, null, 2)
  const blob = new Blob([json], { type: "application/json;charset=utf-8" })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = investigationExportFilename(event, track)
  anchor.rel = "noopener"
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

export async function downloadInvestigationExport(
  event: StoredEventRecord,
  track: InvestigationExportTrack
): Promise<void> {
  let workflow: InvestigationWorkflowExport | null = null
  if (track === "security" && event.id != null) {
    workflow = await fetchInvestigationWorkflowForExport(event.id)
  }
  const bundle = buildInvestigationExport(event, track, workflow)
  triggerJsonDownload(event, track, bundle)
}
