"use client"

import type { ReactNode } from "react"

import {
  NeonBadge,
  NeonGlassCard,
  NeonTabs,
  NeonTabsContent,
  NeonTabsContents,
  NeonTabsList,
  NeonTabsTrigger,
} from "@/components/neon-glass"

import {
  OpsAnalysisDiagnoserPanel,
  OpsAnalysisEntityPanel,
  OpsAnalysisEvidencePanel,
  OpsAnalysisImpactPanel,
  OpsAnalysisInvestigationOverview,
  OpsAnalysisResponderPanel,
  parseOpsInvestigationAnalysis,
} from "./observability-analysis-view"
import { TriageSection } from "./triage-section"
import { StructuredDataView } from "./structured-data-view"
import { FieldGrid } from "./field-grid"
import { asRecord, isRecord } from "./utils"

function OverviewMetadata({
  event,
  payload,
  classification,
}: {
  event: Record<string, unknown>
  payload: Record<string, unknown>
  classification: Record<string, unknown> | null
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-teal-500/20 bg-black/30 p-4">
        <h3 className="mb-3 text-sm font-medium text-slate-200">Record metadata</h3>
        <div className="mb-3 flex flex-wrap gap-2">
          <NeonBadge className="border-teal-500/30 text-teal-300">
            {String(event.tsoc_record_type ?? payload.tsoc_record_type ?? "record")}
          </NeonBadge>
          {event.row_index != null ? (
            <NeonBadge className="border-white/15 text-slate-400">row {String(event.row_index)}</NeonBadge>
          ) : null}
        </div>
        <FieldGrid
          fields={[
            { label: "SID", value: event.sid ?? payload.sid, mono: true },
            { label: "Search", value: event.search_name ?? payload.search_name },
            { label: "Created", value: event.created_at },
            { label: "Record ID", value: event.id, mono: true },
          ]}
        />
      </div>

      {classification ? (
        <div className="rounded-xl border border-teal-500/20 bg-black/30 p-4">
          <h3 className="mb-1 text-sm font-medium text-slate-200">Classification</h3>
          <p className="mb-3 text-xs text-slate-500">Router track and pipeline</p>
          <FieldGrid
            fields={[
              { label: "Track", value: classification.track },
              { label: "Pipeline", value: classification.recommended_pipeline },
              { label: "Confidence", value: classification.confidence },
              { label: "Signals", value: classification.signals },
            ]}
          />
          {typeof classification.reason === "string" ? (
            <p className="mt-2 text-sm text-slate-400">{classification.reason}</p>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

function TechnicalTabContent({
  rawAlert,
  analysisInput,
  analysisOutput,
  phase,
  content,
}: {
  rawAlert: Record<string, unknown> | null
  analysisInput: Record<string, unknown> | null
  analysisOutput: Record<string, unknown> | null
  phase: string | null
  content: unknown
}) {
  const hasPhase = phase != null && content !== undefined
  const parts: { key: string; title: string; node: ReactNode }[] = []

  if (rawAlert) {
    parts.push({ key: "raw", title: "Raw alert", node: <StructuredDataView data={rawAlert} compact /> })
  }
  if (analysisInput) {
    parts.push({ key: "input", title: "Analysis input", node: <StructuredDataView data={analysisInput} compact /> })
  }
  if (analysisOutput) {
    parts.push({ key: "output", title: "Analysis output", node: <StructuredDataView data={analysisOutput} compact /> })
  }
  if (hasPhase) {
    parts.push({
      key: "phase",
      title: `Phase: ${phase}`,
      node: isRecord(content) ? (
        <StructuredDataView data={content} compact />
      ) : (
        <p className="whitespace-pre-wrap text-sm text-slate-300">{String(content)}</p>
      ),
    })
  }

  if (parts.length === 0) {
    return <p className="text-sm text-slate-500">No technical payloads for this record.</p>
  }

  if (parts.length === 1) {
    return <div className="space-y-2">{parts[0]!.node}</div>
  }

  return (
    <NeonTabs defaultValue={parts[0]!.key}>
      <NeonTabsList accent="teal" className="mb-4 flex-wrap border-b border-white/10 pb-2">
        {parts.map((p) => (
          <NeonTabsTrigger key={p.key} accent="teal" value={p.key}>
            {p.title}
          </NeonTabsTrigger>
        ))}
      </NeonTabsList>
      <NeonTabsContents>
        {parts.map((p) => (
          <NeonTabsContent key={p.key} value={p.key}>
            {p.node}
          </NeonTabsContent>
        ))}
      </NeonTabsContents>
    </NeonTabs>
  )
}

export function OpsInvestigationTabbedLayout({
  event,
  payload,
  analysis,
  triage,
  classification,
  rawAlert,
  analysisInput,
  analysisOutput,
  phase,
  content,
}: {
  event: Record<string, unknown>
  payload: Record<string, unknown>
  analysis: Record<string, unknown> | null
  triage: Record<string, unknown> | null
  classification: Record<string, unknown> | null
  rawAlert: Record<string, unknown> | null
  analysisInput: Record<string, unknown> | null
  analysisOutput: Record<string, unknown> | null
  phase: string | null
  content: unknown
}) {
  const sections = analysis ? parseOpsInvestigationAnalysis(analysis) : null
  const hasPhase = phase != null && content !== undefined
  const hasTechnical = Boolean(rawAlert || analysisInput || analysisOutput || hasPhase)
  const showTriageOnly = !analysis && triage != null

  return (
    <NeonGlassCard accent="teal" data-testid="ops-investigation-tabs">
      <NeonTabs defaultValue="overview">
        <div className="border-b border-white/[0.06] px-4 pt-4">
          <NeonTabsList accent="teal" className="flex-wrap gap-1">
            <NeonTabsTrigger accent="teal" value="overview">
              Overview
            </NeonTabsTrigger>
            {sections?.hasEntity ? (
              <NeonTabsTrigger accent="teal" value="entity">
                Entity
              </NeonTabsTrigger>
            ) : null}
            {sections?.hasImpact ? (
              <NeonTabsTrigger accent="teal" value="impact">
                Impact
              </NeonTabsTrigger>
            ) : null}
            {sections?.hasDiagnoser ? (
              <NeonTabsTrigger accent="teal" value="diagnoser">
                Diagnoser
              </NeonTabsTrigger>
            ) : null}
            {sections?.hasResponder ? (
              <NeonTabsTrigger accent="teal" value="responder">
                Responder
              </NeonTabsTrigger>
            ) : null}
            {sections?.hasEvidence ? (
              <NeonTabsTrigger accent="teal" value="evidence">
                Evidence
              </NeonTabsTrigger>
            ) : null}
            {hasTechnical ? (
              <NeonTabsTrigger accent="teal" value="technical">
                Technical
              </NeonTabsTrigger>
            ) : null}
          </NeonTabsList>
        </div>

        <NeonTabsContents className="p-4 md:p-6">
          <NeonTabsContent value="overview" className="space-y-6">
            <OverviewMetadata event={event} payload={payload} classification={classification} />
            {analysis ? <OpsAnalysisInvestigationOverview data={analysis} /> : null}
            {showTriageOnly ? <TriageSection triage={triage} /> : null}
            {!analysis && !classification && !showTriageOnly ? (
              <StructuredDataView data={payload} />
            ) : null}
          </NeonTabsContent>

          {sections?.hasEntity ? (
            <NeonTabsContent value="entity">
              <OpsAnalysisEntityPanel data={analysis!} />
            </NeonTabsContent>
          ) : null}

          {sections?.hasImpact ? (
            <NeonTabsContent value="impact">
              <OpsAnalysisImpactPanel data={analysis!} />
            </NeonTabsContent>
          ) : null}

          {sections?.hasDiagnoser ? (
            <NeonTabsContent value="diagnoser">
              <OpsAnalysisDiagnoserPanel data={analysis!} />
            </NeonTabsContent>
          ) : null}

          {sections?.hasResponder ? (
            <NeonTabsContent value="responder">
              <OpsAnalysisResponderPanel data={analysis!} />
            </NeonTabsContent>
          ) : null}

          {sections?.hasEvidence ? (
            <NeonTabsContent value="evidence">
              <OpsAnalysisEvidencePanel data={analysis!} />
            </NeonTabsContent>
          ) : null}

          {hasTechnical ? (
            <NeonTabsContent value="technical">
              <TechnicalTabContent
                rawAlert={rawAlert}
                analysisInput={analysisInput}
                analysisOutput={analysisOutput}
                phase={phase}
                content={content}
              />
            </NeonTabsContent>
          ) : null}
        </NeonTabsContents>
      </NeonTabs>
    </NeonGlassCard>
  )
}
