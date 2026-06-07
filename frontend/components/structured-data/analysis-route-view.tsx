"use client"

import { NeonBadge } from "@/components/neon-glass"
import { TsocOverflowScroll } from "@/components/ui/tsoc-scroll"

import { FieldGrid } from "./field-grid"
import { DataSection } from "./section"
import { SocAnalysisView } from "./soc-analysis-view"
import { StructuredDataView } from "./structured-data-view"
import { asRecord } from "./utils"

export function AnalysisRouteView({ data }: { data: Record<string, unknown> }) {
  const classification = asRecord(data.classification)
  const security = asRecord(data.security_result)
  const observability = asRecord(data.observability_result)
  const rawAlert = asRecord(data.raw_alert)
  const analysisInput = asRecord(data.analysis_input)
  const analysisOutput = asRecord(data.analysis_output)

  return (
    <TsocOverflowScroll className="max-h-96 space-y-3" axis="both">
      <div className="flex flex-wrap items-center gap-2">
        <NeonBadge className="border-orange-500/30 text-orange-300">track: {String(data.track ?? "—")}</NeonBadge>
        {data.mcp_used ? <NeonBadge className="border-teal-500/30 text-teal-300">MCP used</NeonBadge> : null}
        <NeonBadge className="border-white/15 text-slate-400">row {String(data.row_index ?? 0)}</NeonBadge>
      </div>

      {classification ? (
        <DataSection title="Classification" accent="orange" defaultOpen>
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

      {security ? <SocAnalysisView data={security} /> : null}

      {observability ? (
        <DataSection title="Observability result" defaultOpen={false}>
          <StructuredDataView data={observability} />
        </DataSection>
      ) : null}

      {analysisOutput && !security ? (
        <DataSection title="Analysis output">
          <StructuredDataView data={analysisOutput} />
        </DataSection>
      ) : null}

      {rawAlert ? (
        <DataSection title="Raw alert" defaultOpen={false}>
          <StructuredDataView data={rawAlert} compact />
        </DataSection>
      ) : null}

      {analysisInput ? (
        <DataSection title="Analysis input" defaultOpen={false}>
          <StructuredDataView data={analysisInput} compact />
        </DataSection>
      ) : null}
    </TsocOverflowScroll>
  )
}
