"use client"

import { ActivityIcon, FileTextIcon } from "lucide-react"

import { NeonBadge, NeonCardHeader, NeonGlassCard } from "@/components/neon-glass"
import { tsocNativeScrollbarClasses } from "@/lib/ui-scroll"
import { cn } from "@/lib/utils"

import { FieldGrid } from "./field-grid"
import { pickTriageFromAnalysis, TriagePanelContent } from "./triage-section"
import { asRecord, isRecord } from "./utils"

function TextBlock({ text, className }: { text: string; className?: string }) {
  if (!text) return <p className="text-sm text-slate-500">—</p>
  return (
    <p className={cn("whitespace-pre-wrap text-sm leading-relaxed text-slate-300", className)}>
      {text}
    </p>
  )
}

function OpsJudgeCard({ opsJudge }: { opsJudge: Record<string, unknown> }) {
  return (
    <NeonGlassCard accent="teal" className="h-full">
      <NeonCardHeader
        accent="teal"
        icon={<ActivityIcon className="size-5 text-teal-400" />}
        title="Ops judge verdict"
        description="Operational priority and next action"
        className="px-4 py-3"
      />
      <div className="space-y-3 px-4 pb-4">
        <FieldGrid
          fields={[
            { label: "Verdict", value: opsJudge.verdict },
            { label: "Priority", value: opsJudge.priority },
            { label: "Confidence", value: opsJudge.confidence },
            { label: "Next step", value: opsJudge.recommended_next_step },
            { label: "Escalation", value: opsJudge.escalation_target },
          ]}
        />
        <TextBlock text={String(opsJudge.rationale ?? "")} className="border-t border-white/10 pt-3" />
      </div>
    </NeonGlassCard>
  )
}

function TriageCardTeal({ triage }: { triage: Record<string, unknown> }) {
  return (
    <NeonGlassCard accent="teal" className="h-full">
      <NeonCardHeader
        accent="teal"
        icon={<FileTextIcon className="size-5 text-teal-400" />}
        title="Triage report"
        description="Post-analysis priority and reasoning"
        className="px-4 py-3"
      />
      <div className="px-4 pb-4">
        <TriagePanelContent triage={triage} />
      </div>
    </NeonGlassCard>
  )
}

function FollowupSearchesList({ searches }: { searches: string[] }) {
  if (!searches.length) {
    return <p className="text-sm text-slate-500">No follow-up searches suggested.</p>
  }
  return (
    <ul className="space-y-3">
      {searches.map((spl, i) => (
        <li key={i} className="rounded-xl border border-teal-500/20 bg-black/30 p-3">
          <pre
            className={cn(
              "overflow-x-auto font-mono text-xs leading-relaxed text-teal-100",
              tsocNativeScrollbarClasses
            )}
          >
            {spl}
          </pre>
        </li>
      ))}
    </ul>
  )
}

function HypothesesList({ hypotheses }: { hypotheses: Record<string, unknown>[] }) {
  if (!hypotheses.length) {
    return <p className="text-sm text-slate-500">No root-cause hypotheses.</p>
  }
  return (
    <ul className="space-y-3">
      {hypotheses.map((row, i) => (
        <li key={i} className="rounded-md border border-white/10 bg-black/30 p-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <NeonBadge className="border-teal-500/30 text-teal-300">
              {String(row.confidence ?? "—")}
            </NeonBadge>
            {Array.isArray(row.evidence_refs) && row.evidence_refs.length > 0 ? (
              <NeonBadge className="border-white/15 text-slate-400">
                {row.evidence_refs.length} evidence ref(s)
              </NeonBadge>
            ) : null}
          </div>
          <p className="mt-2 text-slate-200">{String(row.hypothesis ?? "")}</p>
          {row.what_would_confirm ? (
            <p className="mt-1 text-xs text-slate-400">
              Confirm: {String(row.what_would_confirm)}
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  )
}

function StringList({ items, emptyLabel }: { items: string[]; emptyLabel: string }) {
  if (!items.length) return <p className="text-sm text-slate-500">{emptyLabel}</p>
  return (
    <ul className="list-inside list-disc space-y-1 text-sm text-slate-300">
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  )
}

export function parseOpsInvestigationAnalysis(data: Record<string, unknown>) {
  const entity = asRecord(data.entity_resolution)
  const impact = asRecord(data.impact_context)
  const diagnoser = asRecord(data.diagnoser)
  const responder = asRecord(data.responder)
  const opsJudge = asRecord(data.ops_judge)

  const hypotheses = Array.isArray(diagnoser?.root_cause_hypotheses)
    ? diagnoser.root_cause_hypotheses
        .map((item) => (isRecord(item) ? item : null))
        .filter((row): row is Record<string, unknown> => row !== null)
    : []

  const followupSearches = Array.isArray(diagnoser?.followup_searches)
    ? diagnoser.followup_searches.map(String).filter((s) => s.trim().length > 0)
    : []

  const recommendedActions = Array.isArray(responder?.recommended_actions)
    ? responder.recommended_actions.map(String).filter((s) => s.trim().length > 0)
    : []

  const safetyNotes = Array.isArray(responder?.safety_notes)
    ? responder.safety_notes.map(String).filter((s) => s.trim().length > 0)
    : []

  const evidenceRefs = Array.isArray(data.evidence_refs)
    ? data.evidence_refs.map(String).filter((s) => s.trim().length > 0)
    : []

  return {
    triage: pickTriageFromAnalysis(data),
    opsJudge,
    summary: typeof data.summary === "string" ? data.summary : "",
    hasEntity: entity != null,
    hasImpact: impact != null,
    hasDiagnoser: hypotheses.length > 0 || followupSearches.length > 0,
    hasResponder: recommendedActions.length > 0 || safetyNotes.length > 0,
    hasEvidence: evidenceRefs.length > 0,
    hasOpsJudge: opsJudge != null,
    hypotheses,
    followupSearches,
    recommendedActions,
    safetyNotes,
    evidenceRefs,
    entity,
    impact,
    diagnoser,
    responder,
  }
}

export function OpsAnalysisInvestigationOverview({ data }: { data: Record<string, unknown> }) {
  const sections = parseOpsInvestigationAnalysis(data)

  return (
    <div className="space-y-6">
      {sections.summary ? (
        <NeonGlassCard accent="teal">
          <NeonCardHeader
            accent="teal"
            title="Summary"
            description="Operational overview"
            className="px-4 py-3"
          />
          <div className="px-4 pb-4">
            <TextBlock text={sections.summary} />
          </div>
        </NeonGlassCard>
      ) : null}

      {sections.hasOpsJudge && sections.opsJudge ? (
        <OpsJudgeCard opsJudge={sections.opsJudge} />
      ) : null}

      {sections.triage ? <TriageCardTeal triage={sections.triage} /> : null}
    </div>
  )
}

export function OpsAnalysisEntityPanel({ data }: { data: Record<string, unknown> }) {
  const entity = asRecord(data.entity_resolution)
  if (!entity) return <p className="text-sm text-slate-500">No entity resolution data.</p>
  return (
    <FieldGrid
      fields={[
        { label: "Host", value: entity.resolved_host, mono: true },
        { label: "Service", value: entity.resolved_service },
        { label: "Asset ID", value: entity.resolved_asset_id, mono: true },
        { label: "Confidence", value: entity.confidence },
        { label: "Notes", value: entity.notes },
      ]}
    />
  )
}

export function OpsAnalysisImpactPanel({ data }: { data: Record<string, unknown> }) {
  const impact = asRecord(data.impact_context)
  if (!impact) return <p className="text-sm text-slate-500">No impact context.</p>
  return (
    <div className="space-y-4">
      <FieldGrid
        fields={[
          { label: "Impact level", value: impact.impact_level },
          { label: "Customer impact", value: impact.customer_impact },
          { label: "Business criticality", value: impact.business_criticality },
          { label: "Time window", value: impact.time_window },
        ]}
      />
      {Array.isArray(impact.affected_entities) && impact.affected_entities.length > 0 ? (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-teal-300">
            Affected entities
          </h4>
          <StringList
            items={impact.affected_entities.map(String)}
            emptyLabel="No affected entities listed."
          />
        </div>
      ) : null}
    </div>
  )
}

export function OpsAnalysisDiagnoserPanel({ data }: { data: Record<string, unknown> }) {
  const sections = parseOpsInvestigationAnalysis(data)
  if (!sections.hasDiagnoser) {
    return <p className="text-sm text-slate-500">No diagnoser output for this record.</p>
  }
  return (
    <div className="space-y-6">
      <div>
        <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-teal-300">
          Root-cause hypotheses
        </h4>
        <HypothesesList hypotheses={sections.hypotheses} />
      </div>
      <div>
        <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-teal-300">
          Follow-up searches
        </h4>
        <FollowupSearchesList searches={sections.followupSearches} />
      </div>
    </div>
  )
}

export function OpsAnalysisResponderPanel({ data }: { data: Record<string, unknown> }) {
  const sections = parseOpsInvestigationAnalysis(data)
  if (!sections.hasResponder) {
    return <p className="text-sm text-slate-500">No responder recommendations.</p>
  }
  return (
    <div className="space-y-6">
      <div>
        <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-teal-300">
          Recommended actions
        </h4>
        <StringList items={sections.recommendedActions} emptyLabel="No actions listed." />
      </div>
      <div>
        <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-teal-300">Safety notes</h4>
        <StringList items={sections.safetyNotes} emptyLabel="No safety notes." />
      </div>
    </div>
  )
}

export function OpsAnalysisEvidencePanel({ data }: { data: Record<string, unknown> }) {
  const sections = parseOpsInvestigationAnalysis(data)
  if (!sections.hasEvidence) {
    return <p className="text-sm text-slate-500">No evidence references.</p>
  }
  return <StringList items={sections.evidenceRefs} emptyLabel="No evidence references." />
}
