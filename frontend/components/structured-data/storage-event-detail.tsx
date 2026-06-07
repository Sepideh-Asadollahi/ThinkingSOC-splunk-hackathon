"use client"

import { useEffect, useRef } from "react"

import { NeonBadge } from "@/components/neon-glass"
import { investigationLog, summarizeStoredEventPayload } from "@/lib/api/investigation-log"
import { TsocOverflowScroll } from "@/components/ui/tsoc-scroll"

import {
  adminOrgGapFromStoragePayload,
  hasActiveAdminOrgGap,
  mergeAdminOrgGapIntoAnalysis,
  pickAdminOrgGap,
} from "@/lib/admin-org-gap"
import { pickObservabilityAnalysis, pickSecurityAnalysis } from "@/lib/analysis-payload"

import { FieldGrid } from "./field-grid"
import { InvestigationTabbedLayout } from "./investigation-tabbed-layout"
import { OpsInvestigationTabbedLayout } from "./ops-investigation-tabbed-layout"
import { DataSection } from "./section"
import { AdminOrgGapPanel, SocAnalysisView } from "./soc-analysis-view"
import { OpsAnalysisInvestigationOverview } from "./observability-analysis-view"
import { pickTriageFromPayload, TriageSection } from "./triage-section"
import { StructuredDataView } from "./structured-data-view"
import { asRecord, isRecord } from "./utils"

export function StorageEventDetail({
  event,
  variant = "default",
  investigationRecordId,
  timelineRefreshKey = 0,
  onAnalystActionRecorded,
}: {
  event: Record<string, unknown> | null
  variant?: "default" | "investigation" | "ops-investigation"
  /** Security investigation page: record id for timeline + analyst gate in Overview. */
  investigationRecordId?: string
  timelineRefreshKey?: number
  onAnalystActionRecorded?: () => void
}) {
  const renderLogRef = useRef<string | null>(null)
  useEffect(() => {
    if (!event || variant !== "investigation") return
    const key = String(event.id ?? "unknown")
    if (renderLogRef.current === key) return
    renderLogRef.current = key

    const payload = asRecord(event.payload) ?? {}
    const recordType = String(event.tsoc_record_type ?? payload.tsoc_record_type ?? "")
    const triage = pickTriageFromPayload(payload)
    const analysis = pickSecurityAnalysis(payload)
    const rawAlert = asRecord(payload.raw_alert) ?? asRecord(event.raw_alert)

    const adminGap = analysis ? pickAdminOrgGap(analysis) : pickAdminOrgGap(payload)
    investigationLog("render.investigation", {
      recordId: event.id,
      recordType,
      hasAnalysis: !!analysis,
      hasTriage: !!triage,
      hasRawAlert: !!rawAlert,
      hasAdminOrgGap: hasActiveAdminOrgGap(adminGap),
      ...summarizeStoredEventPayload(payload),
    })
    if (!analysis && !triage && !rawAlert) {
      investigationLog(
        "render.empty_panels",
        {
          recordId: event.id,
          recordType,
          payloadKeys: Object.keys(payload),
          hint: "API returned data but pickSecurityAnalysis found no analysis block",
        },
        "warn"
      )
    }
  }, [event, variant])

  if (!event) {
    return <p className="text-sm text-slate-500">Select a row from the table</p>
  }

  const payload = asRecord(event.payload) ?? {}
  const recordType = String(event.tsoc_record_type ?? payload.tsoc_record_type ?? "")

  if (recordType === "admin_org_gap_suggest") {
    const gap = adminOrgGapFromStoragePayload(payload)
    return (
      <TsocOverflowScroll className="max-h-[min(70vh,720px)] space-y-3 px-6 pb-6" axis="both">
        <div className="flex flex-wrap gap-2">
          <NeonBadge className="border-violet-500/30 text-violet-300">admin_org_gap_suggest</NeonBadge>
        </div>
        <FieldGrid
          fields={[
            { label: "SID", value: event.sid ?? payload.sid, mono: true },
            { label: "Search", value: event.search_name ?? payload.search_name },
            { label: "Created", value: event.created_at },
            { label: "Record ID", value: event.id, mono: true },
          ]}
        />
        <AdminOrgGapPanel gap={gap} />
        <DataSection title="Request / response" defaultOpen={false}>
          <StructuredDataView data={payload} compact />
        </DataSection>
      </TsocOverflowScroll>
    )
  }

  const triage = pickTriageFromPayload(payload)
  const rawSecurity = pickSecurityAnalysis(payload)
  const rawObservability = pickObservabilityAnalysis(payload)
  const rawAnalysis = variant === "ops-investigation" ? rawObservability : rawSecurity
  const phase = typeof payload.phase === "string" ? payload.phase : null
  const content = payload.content
  const phaseThreatIntel =
    phase === "threat_intel" && isRecord(content) ? (content as Record<string, unknown>) : null
  const analysis = rawAnalysis
    ? mergeAdminOrgGapIntoAnalysis(
        {
          ...rawAnalysis,
          triage: rawAnalysis.triage ?? payload.triage,
          threat_intel:
            rawAnalysis.threat_intel ?? payload.threat_intel ?? phaseThreatIntel,
        },
        payload
      )
    : phaseThreatIntel
      ? { threat_intel: phaseThreatIntel }
      : null
  const classification = asRecord(payload.classification)
  const rawAlert = asRecord(payload.raw_alert) ?? asRecord(event.raw_alert)
  const analysisInput = asRecord(payload.analysis_input)
  const analysisOutput = asRecord(payload.analysis_output)

  if (variant === "investigation") {
    return (
      <InvestigationTabbedLayout
        event={event}
        payload={payload}
        analysis={analysis}
        triage={triage}
        classification={classification}
        rawAlert={rawAlert}
        analysisInput={analysisInput}
        analysisOutput={analysisOutput}
        phase={phase}
        content={content}
        recordId={investigationRecordId}
        timelineRefreshKey={timelineRefreshKey}
        onAnalystActionRecorded={onAnalystActionRecorded}
      />
    )
  }

  if (variant === "ops-investigation") {
    const opsAnalysis = rawObservability
      ? { ...rawObservability, triage: rawObservability.triage ?? payload.triage }
      : null
    return (
      <OpsInvestigationTabbedLayout
        event={event}
        payload={payload}
        analysis={opsAnalysis}
        triage={triage}
        classification={classification}
        rawAlert={rawAlert}
        analysisInput={analysisInput}
        analysisOutput={analysisOutput}
        phase={phase}
        content={content}
      />
    )
  }

  return (
    <TsocOverflowScroll className="max-h-[min(70vh,720px)] space-y-3 px-6 pb-6" axis="both">
      <div className="flex flex-wrap gap-2">
        <NeonBadge className="border-orange-500/30 text-orange-300">
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

      {triage ? <TriageSection triage={triage} /> : null}

      {classification ? (
        <DataSection title="Classification" accent="orange">
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
        </DataSection>
      ) : null}

      {rawObservability ? <OpsAnalysisInvestigationOverview data={rawObservability} /> : null}
      {analysis ? <SocAnalysisView data={analysis} /> : null}

      {phase && content !== undefined ? (
        <DataSection title={`Investigation: ${phase}`} defaultOpen>
          {isRecord(content) ? <StructuredDataView data={content} compact /> : (
            <p className="whitespace-pre-wrap text-sm text-slate-300">{String(content)}</p>
          )}
        </DataSection>
      ) : null}

      {rawAlert ? (
        <DataSection title="Raw alert" defaultOpen={!analysis}>
          <StructuredDataView data={rawAlert} compact />
        </DataSection>
      ) : null}

      {analysisInput ? (
        <DataSection title="Analysis input" defaultOpen={false}>
          <StructuredDataView data={analysisInput} compact />
        </DataSection>
      ) : null}

      {analysisOutput ? (
        <DataSection title="Analysis output" defaultOpen={false}>
          <StructuredDataView data={analysisOutput} compact />
        </DataSection>
      ) : null}

      {!analysis && !classification && !rawAlert && !phase ? (
        <DataSection title="Payload" defaultOpen>
          <StructuredDataView data={payload} />
        </DataSection>
      ) : null}
    </TsocOverflowScroll>
  )
}
