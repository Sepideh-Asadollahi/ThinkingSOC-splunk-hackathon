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
  parseInvestigationAnalysis,
  SocAnalysisAdminGapPanel,
  SocAnalysisEvidenceChainPanel,
  SocAnalysisFrameworkPanel,
  SocAnalysisCourtPanel,
  SocAnalysisInvestigationOverview,
  SocAnalysisSummaryCard,
  SocAnalysisQuestionsPanel,
  SocAnalysisRecommendedActionPanel,
  SocAnalysisTriagePanel,
  SocAnalysisThreatIntelPanel,
  SocAnalysisEnrichmentPanel,
} from "./soc-analysis-view"
import { InvestigationAnalystActions } from "./investigation-analyst-actions"
import { InvestigationTimeline } from "./investigation-timeline"
import { TriageSection } from "./triage-section"
import { StructuredDataView } from "./structured-data-view"
import { FieldGrid } from "./field-grid"
import { asRecord, isRecord } from "./utils"

/** Security investigation tab labels (order matches analyst workflow). */
export const INVESTIGATION_TAB = {
  overview: "Overview",
  recommendedAction: "Recommended action",
  triage: "Triage",
  agents: "Hunter & defender",
  enrichment: "Enrichment",
  questions: "Questions & SPL",
  threatIntel: "Threat intel",
  framework: "Framework",
  evidenceChain: "Evidence chain",
  adminQuestion: "Admin question",
  technical: "Technical",
} as const

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
      <div className="rounded-xl border border-orange-500/20 bg-black/30 p-4">
        <h3 className="mb-3 text-sm font-medium text-slate-200">Record metadata</h3>
        <div className="mb-3 flex flex-wrap gap-2">
          <NeonBadge className="border-orange-500/30 text-orange-300">
            {String(event.tsoc_record_type ?? payload.tsoc_record_type ?? "record")}
          </NeonBadge>
          {event.row_index != null && Number.isFinite(Number(event.row_index)) ? (
            <NeonBadge className="border-white/15 text-slate-400">
              row {String(Number(event.row_index) + 1)}
            </NeonBadge>
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
        <div className="rounded-xl border border-orange-500/20 bg-black/30 p-4">
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

export function InvestigationTabbedLayout({
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
  recordId,
  timelineRefreshKey = 0,
  onAnalystActionRecorded,
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
  recordId?: string
  timelineRefreshKey?: number
  onAnalystActionRecorded?: () => void
}) {
  const analysisForPanels =
    analysis && triage && !asRecord(analysis.triage) ? { ...analysis, triage } : analysis
  const sections = analysisForPanels ? parseInvestigationAnalysis(analysisForPanels) : null
  const hasPhase = phase != null && content !== undefined
  const hasTechnical = Boolean(rawAlert || analysisInput || analysisOutput || hasPhase)
  const showTriageOnly = !analysis && triage != null
  /** Admin question tab only when analysis suggests an org knowledge gap (see docs/07-lld). */
  const showAdminQuestionTab = Boolean(sections?.hasAdminGap)

  type TabDef = { value: string; label: string }
  const tabDefs: TabDef[] = [
    { value: "overview", label: INVESTIGATION_TAB.overview },
  ]
  if (sections?.hasRecommendedActions) {
    tabDefs.push({ value: "recommended-action", label: INVESTIGATION_TAB.recommendedAction })
  }
  if (sections?.hasTriage) {
    tabDefs.push({ value: "triage", label: INVESTIGATION_TAB.triage })
  }
  if (sections?.hasCourt) {
    tabDefs.push({ value: "agents", label: INVESTIGATION_TAB.agents })
  }
  if (sections?.hasEnrichment) {
    tabDefs.push({ value: "enrichment", label: INVESTIGATION_TAB.enrichment })
  }
  if (sections?.hasQuestions) {
    tabDefs.push({ value: "questions", label: INVESTIGATION_TAB.questions })
  }
  if (sections?.hasThreatIntel) {
    tabDefs.push({ value: "threat-intel", label: INVESTIGATION_TAB.threatIntel })
  }
  if (sections?.hasFramework) {
    tabDefs.push({ value: "framework", label: INVESTIGATION_TAB.framework })
  }
  if (sections?.hasEvidenceChain) {
    tabDefs.push({ value: "evidence-chain", label: INVESTIGATION_TAB.evidenceChain })
  }
  if (showAdminQuestionTab) {
    tabDefs.push({ value: "admin-question", label: INVESTIGATION_TAB.adminQuestion })
  }
  if (hasTechnical) {
    tabDefs.push({ value: "technical", label: INVESTIGATION_TAB.technical })
  }

  const showWorkflowPanels = Boolean(recordId)

  return (
    <NeonGlassCard accent="orange" data-testid="investigation-tabs">
      <NeonTabs defaultValue="overview">
        <div
          className="border-b border-white/[0.06] px-4 pt-4"
          data-testid="investigation-tabs-bar"
        >
          <NeonTabsList accent="orange" className="flex-wrap gap-1">
            {tabDefs.map((tab) => (
              <NeonTabsTrigger key={tab.value} accent="orange" value={tab.value}>
                {tab.label}
              </NeonTabsTrigger>
            ))}
          </NeonTabsList>
        </div>

        <NeonTabsContents className="p-4 md:p-6">
          <NeonTabsContent value="overview" className="space-y-6">
            {analysisForPanels ? <SocAnalysisSummaryCard data={analysisForPanels} /> : null}
            {showWorkflowPanels ? (
              <div className="grid gap-4 lg:grid-cols-2">
                <InvestigationAnalystActions
                  recordId={recordId!}
                  onActionRecorded={onAnalystActionRecorded}
                />
                <InvestigationTimeline recordId={recordId!} refreshKey={timelineRefreshKey} />
              </div>
            ) : null}
            <OverviewMetadata event={event} payload={payload} classification={classification} />
            {analysisForPanels ? <SocAnalysisInvestigationOverview data={analysisForPanels} /> : null}
            {showTriageOnly ? <TriageSection triage={triage} /> : null}
            {!analysis && !classification && !showTriageOnly ? (
              <StructuredDataView data={payload} />
            ) : null}
          </NeonTabsContent>

          {sections?.hasRecommendedActions ? (
            <NeonTabsContent value="recommended-action">
              <SocAnalysisRecommendedActionPanel data={analysisForPanels!} />
            </NeonTabsContent>
          ) : null}

          {sections?.hasTriage ? (
            <NeonTabsContent value="triage">
              <SocAnalysisTriagePanel data={analysisForPanels!} />
            </NeonTabsContent>
          ) : null}

          {sections?.hasCourt ? (
            <NeonTabsContent value="agents">
              <SocAnalysisCourtPanel data={analysisForPanels!} />
            </NeonTabsContent>
          ) : null}

          {sections?.hasEnrichment ? (
            <NeonTabsContent value="enrichment">
              <SocAnalysisEnrichmentPanel data={analysisForPanels!} />
            </NeonTabsContent>
          ) : null}

          {sections?.hasQuestions ? (
            <NeonTabsContent value="questions">
              <SocAnalysisQuestionsPanel data={analysisForPanels!} />
            </NeonTabsContent>
          ) : null}

          {sections?.hasThreatIntel ? (
            <NeonTabsContent value="threat-intel">
              <SocAnalysisThreatIntelPanel data={analysis!} />
            </NeonTabsContent>
          ) : null}

          {sections?.hasFramework ? (
            <NeonTabsContent value="framework">
              <SocAnalysisFrameworkPanel data={analysis!} />
            </NeonTabsContent>
          ) : null}

          {sections?.hasEvidenceChain ? (
            <NeonTabsContent value="evidence-chain">
              <SocAnalysisEvidenceChainPanel data={analysisForPanels!} />
            </NeonTabsContent>
          ) : null}

          {showAdminQuestionTab ? (
            <NeonTabsContent value="admin-question">
              <SocAnalysisAdminGapPanel data={analysis!} />
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
