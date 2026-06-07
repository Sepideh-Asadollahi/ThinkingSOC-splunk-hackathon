"use client"

import { FileTextIcon, GavelIcon, HelpCircleIcon, ListChecksIcon, ShieldIcon } from "lucide-react"

import { NeonCardHeader, NeonGlassCard, NeonBadge } from "@/components/neon-glass"
import { tsocNativeScrollbarClasses } from "@/lib/ui-scroll"
import { cn } from "@/lib/utils"

import {
  groupFrameworkMapping,
  type FrameworkMappingRow,
} from "@/lib/framework-mapping"
import {
  hasActiveAdminOrgGap,
  normalizeAdminOrgGap,
  type AdminOrgGap,
} from "@/lib/admin-org-gap"
import {
  normalizeInvestigationQuestions,
  pickInvestigationQuestionsRaw,
  pickSplResultsAnalysisBody,
  type InvestigationQuestionItem,
  type SplResultsAnalysis,
  type SplSaiaAnalysis,
} from "@/lib/investigation-questions"

import { FieldGrid, type FieldGridItem } from "./field-grid"
import { AgentCourt, type HunterDebateData } from "./hunter-defender-debate"
import { HunterSplSearchIdeasPanel } from "./hunter-spl-search-ideas"
import {
  McpHunterEvidencePanel,
  McpJudgeEvidencePanel,
  parseMcpHunterEvidence,
  parseMcpJudgeEvidence,
  parseSaiaAnswerText,
} from "./mcp-evidence-panel"
import { McpMarkdownContent } from "./mcp-markdown-content"
import { DataSection } from "./section"
import { pickTriageFromAnalysis, TriagePanelContent } from "./triage-section"
import { ThreatIntelPanel, ThreatIntelSection, pickThreatIntel } from "./threat-intel-panel"
import { asRecord, isRecord, labelize } from "./utils"

/** Supports stored payloads before/after identity → enrichment rename. */
function enrichmentFromData(data: Record<string, unknown>): Record<string, unknown> | null {
  const raw = asRecord(data.enrichment) ?? asRecord(data.identity_resolution)
  if (!raw) return null
  return {
    ...raw,
    confidence: raw.confidence ?? raw.identity_confidence,
    notes: raw.notes ?? raw.identity_notes,
  }
}

const ENRICHMENT_GRID_KEYS = new Set([
  "confidence",
  "identity_confidence",
  "resolved_user_id",
  "resolved_asset_id",
  "matched_relationship_ids",
  "notes",
  "identity_notes",
])

function enrichmentResolutionFields(enrichment: Record<string, unknown>): FieldGridItem[] {
  const fields: FieldGridItem[] = [
    { label: "Confidence", value: enrichment.confidence },
    { label: "User ID", value: enrichment.resolved_user_id, mono: true },
    { label: "Asset ID", value: enrichment.resolved_asset_id, mono: true },
    {
      label: "Matched relationships",
      value: enrichment.matched_relationship_ids,
      fieldKey: "matched_relationship_ids",
    },
  ]
  for (const [key, value] of Object.entries(enrichment)) {
    if (ENRICHMENT_GRID_KEYS.has(key)) continue
    if (value === null || value === undefined || value === "") continue
    fields.push({ label: labelize(key), value, fieldKey: key })
  }
  return fields
}

function inventoryUserFields(row: Record<string, unknown>): FieldGridItem[] {
  const ordered = ["user_id", "display_name", "email", "department", "risk_score", "description"] as const
  const fields: FieldGridItem[] = ordered.map((key) => ({
    label: labelize(key),
    value: row[key],
    fieldKey: `user-${key}`,
    mono: key === "user_id",
  }))
  for (const [key, value] of Object.entries(row)) {
    if (ordered.includes(key as (typeof ordered)[number])) continue
    if (value === null || value === undefined || value === "") continue
    fields.push({ label: labelize(key), value, fieldKey: `user-${key}` })
  }
  return fields
}

function inventoryAssetFields(row: Record<string, unknown>): FieldGridItem[] {
  const ordered = [
    "asset_id",
    "asset_type",
    "hostname",
    "fqdn",
    "ip",
    "owner",
    "criticality",
    "risk_score",
    "description",
  ] as const
  const fields: FieldGridItem[] = ordered.map((key) => ({
    label: labelize(key),
    value: row[key],
    fieldKey: `asset-${key}`,
    mono: key === "asset_id" || key === "ip",
  }))
  for (const [key, value] of Object.entries(row)) {
    if (ordered.includes(key as (typeof ordered)[number])) continue
    if (value === null || value === undefined || value === "") continue
    fields.push({ label: labelize(key), value, fieldKey: `asset-${key}` })
  }
  return fields
}

function EnrichmentSectionTitle({ children }: { children: string }) {
  return (
    <h4 className="text-xs font-semibold uppercase tracking-wide text-orange-300/90">{children}</h4>
  )
}

export function EnrichmentPanelContent({ data }: { data: Record<string, unknown> }) {
  const enrichment = enrichmentFromData(data)
  const risk = typeof data.risk_context === "string" ? data.risk_context.trim() : ""
  const user = asRecord(data.inventory_user)
  const asset = asRecord(data.inventory_asset)
  const notes =
    enrichment && typeof enrichment.notes === "string" ? enrichment.notes.trim() : ""

  if (!enrichment && !risk && !user && !asset) {
    return <p className="text-sm text-slate-500">No inventory enrichment data.</p>
  }

  return (
    <div className="space-y-6">
      {enrichment ? (
        <section className="space-y-3">
          <EnrichmentSectionTitle>Inventory resolution</EnrichmentSectionTitle>
          <FieldGrid fields={enrichmentResolutionFields(enrichment)} />
          {notes ? (
            <div className="rounded-md border border-white/10 bg-black/30 px-3 py-2">
              <p className="text-[10px] font-medium uppercase tracking-wide text-slate-500">Notes</p>
              <TextBlock text={notes} className="mt-1 text-sm" />
            </div>
          ) : null}
        </section>
      ) : null}

      {risk ? (
        <section className="space-y-2">
          <EnrichmentSectionTitle>Risk context</EnrichmentSectionTitle>
          <TextBlock text={risk} />
        </section>
      ) : null}

      {user ? (
        <section className="space-y-2">
          <EnrichmentSectionTitle>Matched user (inventory)</EnrichmentSectionTitle>
          <FieldGrid fields={inventoryUserFields(user)} />
        </section>
      ) : null}

      {asset ? (
        <section className="space-y-2">
          <EnrichmentSectionTitle>Matched asset (inventory)</EnrichmentSectionTitle>
          <FieldGrid fields={inventoryAssetFields(asset)} />
        </section>
      ) : null}
    </div>
  )
}

export function hasEnrichmentContent(data: Record<string, unknown>): boolean {
  if (enrichmentFromData(data) != null) return true
  if (typeof data.risk_context === "string" && data.risk_context.trim().length > 0) return true
  if (asRecord(data.inventory_user) != null) return true
  if (asRecord(data.inventory_asset) != null) return true
  return false
}

function TextBlock({ text, className }: { text: string; className?: string }) {
  if (!text) return <p className="text-sm text-slate-500">—</p>
  return (
    <p className={cn("whitespace-pre-wrap text-sm leading-relaxed text-slate-300", className)}>
      {text}
    </p>
  )
}

function FrameworkMappingSection({
  title,
  accent,
  items,
}: {
  title: string
  accent: "violet" | "teal"
  items: FrameworkMappingRow[]
}) {
  if (!items.length) return null
  const idBadge =
    accent === "violet"
      ? "border-violet-500/30 text-violet-300"
      : "border-teal-500/30 text-teal-300"
  return (
    <section className="space-y-2">
      <h4
        className={cn(
          "text-xs font-semibold uppercase tracking-wide",
          accent === "violet" ? "text-violet-300" : "text-teal-300"
        )}
      >
        {title}
      </h4>
      <ul className="space-y-2">
        {items.map((row, i) => (
          <li key={`${title}-${i}`} className="rounded-md border border-white/10 bg-black/30 p-2 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <NeonBadge className={idBadge}>{String(row.id ?? "—")}</NeonBadge>
              <span className="text-slate-200">{String(row.name ?? "")}</span>
              {row.confidence ? (
                <NeonBadge className="border-white/15 text-slate-400">{String(row.confidence)}</NeonBadge>
              ) : null}
            </div>
            <p className="mt-1 text-xs text-slate-400">{String(row.rationale ?? "")}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}

function FrameworkList({ framework }: { framework: unknown[] }) {
  const rows = framework
    .map((item) => (isRecord(item) ? (item as FrameworkMappingRow) : null))
    .filter((row): row is FrameworkMappingRow => row !== null)
  const { mitre, killChain, other } = groupFrameworkMapping(rows)

  if (!mitre.length && !killChain.length && !other.length) {
    return <p className="text-sm text-slate-500">—</p>
  }

  return (
    <div className="space-y-4">
      <FrameworkMappingSection title="MITRE ATT&CK" accent="violet" items={mitre} />
      <FrameworkMappingSection title="Cyber Kill Chain" accent="teal" items={killChain} />
      {other.length ? (
        <FrameworkMappingSection title="Other frameworks" accent="violet" items={other} />
      ) : null}
    </div>
  )
}

function RootSplBlock({ rootSpl }: { rootSpl: Record<string, unknown> }) {
  return (
    <>
      <FieldGrid
        fields={[
          { label: "Time window", value: rootSpl.time_window, mono: true },
          { label: "Pivots", value: rootSpl.pivots },
        ]}
      />
      {typeof rootSpl.spl === "string" ? (
        <pre
          className={cn(
            "mt-2 overflow-x-auto rounded border border-teal-500/20 bg-black/50 p-2 font-mono text-xs text-teal-100",
            tsocNativeScrollbarClasses
          )}
        >
          {rootSpl.spl}
        </pre>
      ) : null}
      <TextBlock text={String(rootSpl.explanation ?? "")} className="mt-2" />
    </>
  )
}

/** Judge next-step string (API may use ``recommended_next_step`` or ``next_step``). */
export function pickJudgeRecommendedStep(judge: Record<string, unknown> | null): string {
  if (!judge) return ""
  const step =
    typeof judge.recommended_next_step === "string"
      ? judge.recommended_next_step
      : typeof judge.next_step === "string"
        ? judge.next_step
        : ""
  return step.trim()
}

/** Flat ``judge`` on SOC result, or nested ``judge_output.judge`` from graph LLM step. */
export function pickJudgeFromData(data: Record<string, unknown>): Record<string, unknown> | null {
  const flat = asRecord(data.judge)
  if (
    flat &&
    (flat.verdict != null ||
      flat.priority != null ||
      flat.recommended_next_step != null ||
      flat.rationale != null)
  ) {
    return flat
  }
  const jo = asRecord(data.judge_output)
  const nested = jo ? asRecord(jo.judge) : null
  if (nested) return nested
  return flat
}

export function pickSummaryFromData(data: Record<string, unknown>): string {
  if (typeof data.summary === "string" && data.summary.trim()) return data.summary.trim()
  const jo = asRecord(data.judge_output)
  if (jo && typeof jo.summary === "string" && jo.summary.trim()) return jo.summary.trim()
  return ""
}

export function JudgeCard({ judge }: { judge: Record<string, unknown> }) {
  const judgeMcp = parseMcpJudgeEvidence(judge.mcp_evidence)
  return (
    <div className="space-y-4">
      <NeonGlassCard accent="orange" className="h-full">
        <NeonCardHeader
          accent="orange"
          icon={<GavelIcon className="size-5 text-orange-400" />}
          title="Judge verdict"
          description="Priority and recommended action"
          className="px-4 py-3"
        />
        <div className="space-y-3 px-4 pb-4">
          <FieldGrid
            fields={[
              { label: "Verdict", value: judge.verdict },
              { label: "Priority", value: judge.priority },
              { label: "Confidence", value: judge.confidence },
              { label: "Next step", value: judge.recommended_next_step },
            ]}
          />
          <TextBlock text={String(judge.rationale ?? "")} className="border-t border-white/10 pt-3" />
        </div>
      </NeonGlassCard>
      {judgeMcp ? (
        <DataSection
          title="Splunk MCP verdict evidence"
          description="SAIA guidance and verification queries — after Defender and Hunter"
          accent="teal"
          defaultOpen={false}
        >
          <McpJudgeEvidencePanel evidence={judgeMcp} showHeader={false} />
        </DataSection>
      ) : null}
    </div>
  )
}

export function TriageCard({ triage }: { triage: Record<string, unknown> }) {
  return (
    <NeonGlassCard accent="orange" className="h-full">
      <NeonCardHeader
        accent="orange"
        icon={<FileTextIcon className="size-5 text-orange-400" />}
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

function SplResultsTable({ results }: { results: NonNullable<InvestigationQuestionItem["spl_results"]> }) {
  if (results.error) {
    return <p className="mt-2 text-xs text-amber-400/90">Splunk: {results.error}</p>
  }
  const rows = results.rows ?? []
  if (rows.length === 0) {
    return <p className="mt-2 text-xs text-slate-500">Splunk returned 0 rows.</p>
  }
  const columns = Array.from(
    rows.reduce((set, row) => {
      Object.keys(row).forEach((k) => set.add(k))
      return set
    }, new Set<string>())
  )
  return (
    <div
      className={cn(
        "mt-3 max-w-full overflow-x-auto rounded-lg border border-white/10",
        tsocNativeScrollbarClasses
      )}
    >
      <table className="min-w-full text-left text-xs text-slate-300">
        <thead className="bg-white/5 text-[10px] uppercase tracking-wide text-slate-500">
          <tr>
            {columns.map((col) => (
              <th key={col} className="whitespace-nowrap px-2 py-1.5 font-medium">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri} className="border-t border-white/5">
              {columns.map((col) => (
                <td key={col} className="whitespace-nowrap px-2 py-1 font-mono text-[11px]">
                  {String(row[col] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="px-2 py-1 text-[10px] text-slate-500">
        {results.row_count ?? rows.length} row(s)
        {results.truncated ? " (truncated)" : ""}
      </p>
    </div>
  )
}

function SplSaiaAnalysisContent({ analysis }: { analysis: SplSaiaAnalysis }) {
  if (analysis.unavailable_reason) {
    return (
      <p className="text-xs text-amber-200/90" data-testid="spl-saia-unavailable">
        {analysis.unavailable_reason}
      </p>
    )
  }
  const parsed = parseSaiaAnswerText((analysis.explanation ?? "").trim())
  return (
    <>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        {analysis.optimized ? (
          <NeonBadge className="border-violet-500/40 text-violet-200">optimized</NeonBadge>
        ) : null}
        {(analysis.steps ?? []).map((step) => (
          <NeonBadge key={step} className="border-white/15 text-slate-400">
            {step}
          </NeonBadge>
        ))}
        {parsed.isFallback && parsed.fallbackLabel ? (
          <NeonBadge className="border-amber-500/40 text-[10px] text-amber-200">
            {parsed.fallbackLabel}
          </NeonBadge>
        ) : null}
      </div>
      {parsed.body ? (
        <div className="w-full min-w-0" data-testid="spl-saia-analysis">
          <McpMarkdownContent content={parsed.body} className="text-xs" />
        </div>
      ) : (
        <p className="text-xs text-slate-500">SAIA returned no explanation text.</p>
      )}
      {analysis.optimized && analysis.spl_before_optimize ? (
        <details className="mt-2 text-[10px] text-slate-500">
          <summary className="cursor-pointer text-violet-300/80">SPL before SAIA optimize</summary>
          <pre
            className={cn(
              "mt-1 overflow-x-auto rounded border border-white/10 bg-black/40 p-2 font-mono text-[10px] text-slate-400",
              tsocNativeScrollbarClasses
            )}
          >
            {analysis.spl_before_optimize}
          </pre>
        </details>
      ) : null}
    </>
  )
}

function SplResultsAnalysisContent({ analysis }: { analysis: SplResultsAnalysis }) {
  const { text, findings, confidence, usefulness, recommendedNextStep } =
    pickSplResultsAnalysisBody(analysis)
  if (!text && findings.length === 0 && !recommendedNextStep) {
    return <p className="text-xs text-slate-500">No execution-result narrative yet.</p>
  }
  return (
    <>
      {text ? (
        <div className="w-full min-w-0" data-testid="spl-results-analysis">
          <McpMarkdownContent content={text} className="text-xs" />
        </div>
      ) : null}
      {findings.length > 0 ? (
        <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-slate-400">
          {findings.map((f, idx) => (
            <li key={idx}>{f}</li>
          ))}
        </ul>
      ) : null}
      {recommendedNextStep ? (
        <p className="mt-2 text-xs leading-relaxed text-orange-200/90">
          <span className="font-semibold text-orange-200">Next step:</span> {recommendedNextStep}
        </p>
      ) : null}
      <div className="mt-2 flex flex-wrap gap-3 text-[10px] text-slate-500">
        {usefulness ? <span>Usefulness: {usefulness}</span> : null}
        {confidence ? <span>Confidence: {confidence}</span> : null}
      </div>
    </>
  )
}

/** Per-SPL analysis: SAIA (MCP) + optional execution-result LLM summary — always shown. */
function SplQuestionAnalysisSection({ item }: { item: InvestigationQuestionItem }) {
  const saia = item.spl_saia_analysis
  const legacyExpl = (item.explanation ?? "").trim()
  const hasResultsAnalysis = item.spl_results_analysis != null

  return (
    <div
      className="mt-4 space-y-3 rounded-lg border border-white/10 bg-white/[0.02] p-3"
      data-testid="spl-question-analysis"
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-300">SPL analysis</p>

      <div className="rounded-lg border border-violet-500/20 bg-violet-950/15 p-3">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-violet-200/90">
          Splunk AI Assistant (SAIA)
        </p>
        <div className="mt-2">
          {saia ? (
            <SplSaiaAnalysisContent analysis={saia} />
          ) : legacyExpl ? (
            <>
              <NeonBadge className="mb-2 border-white/15 text-slate-400">from generator</NeonBadge>
              <McpMarkdownContent content={legacyExpl} className="text-xs" />
            </>
          ) : (
            <p className="text-xs text-slate-500">
              SAIA review runs by default during analysis when Splunk MCP is configured.
            </p>
          )}
        </div>
      </div>

      {item.spl_results ? (
        <div>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
            Splunk execution results
          </p>
          <SplResultsTable results={item.spl_results} />
        </div>
      ) : null}

      <div className="rounded-lg border border-orange-500/20 bg-orange-950/10 p-3">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-orange-200/90">
          Execution result analysis
        </p>
        <div className="mt-2">
          {hasResultsAnalysis ? (
            <SplResultsAnalysisContent analysis={item.spl_results_analysis!} />
          ) : (
            <p className="text-xs text-slate-500">
              Shown after SPL runs on Splunk when LLM result-batch analysis is enabled.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

function InvestigationQuestionsSplList({ items }: { items: InvestigationQuestionItem[] }) {
  return (
    <ul className="space-y-4">
      {items.map((item, i) => (
        <li key={i} className="w-full min-w-0 rounded-xl border border-white/10 bg-black/30 p-4">
          <p className="mb-3 text-sm font-medium leading-relaxed text-slate-200">{item.question}</p>
          <pre
            className={cn(
              "overflow-x-auto rounded-lg border border-teal-500/20 bg-black/50 p-3 font-mono text-xs text-teal-100",
              tsocNativeScrollbarClasses
            )}
          >
            {item.spl}
          </pre>
          {item.time_window ? (
            <p className="mt-1 font-mono text-[10px] text-slate-500">{item.time_window}</p>
          ) : null}
          <SplQuestionAnalysisSection item={item} />
        </li>
      ))}
    </ul>
  )
}

export function AdminOrgGapPanel({ gap }: { gap: AdminOrgGap | null }) {
  if (!gap) {
    return (
      <p className="text-sm text-slate-500" data-testid="admin-org-gap-panel-empty">
        No admin organizational GAP data on this record. Re-run Security analysis after backend update to
        generate a suggested question.
      </p>
    )
  }
  if (!hasActiveAdminOrgGap(gap)) {
    return (
      <NeonGlassCard accent="violet" data-testid="admin-org-gap-panel-inactive">
        <NeonCardHeader
          accent="violet"
          icon={<HelpCircleIcon className="size-5 text-violet-300" />}
          title="Admin question"
          description="No question suggested for this alert"
          className="px-4 py-3"
        />
        <div className="space-y-2 px-4 pb-4 text-sm text-slate-400">
          <p>
            Analysis ran, but the system did not flag an organizational knowledge gap (often because
            inventory already links the host and no ambiguous process policy was detected).
          </p>
          {gap.notes ? <TextBlock text={gap.notes} className="text-xs" /> : null}
        </div>
      </NeonGlassCard>
    )
  }
  return (
    <NeonGlassCard accent="violet" data-testid="admin-org-gap-panel">
      <NeonCardHeader
        accent="violet"
        icon={<HelpCircleIcon className="size-5 text-violet-300" />}
        title="Question for administrator"
        description="Organizational context needed to interpret this alert"
        className="px-4 py-3"
      />
      <div className="space-y-3 px-4 pb-4">
        {gap.gap_summary ? (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-violet-300/90">Knowledge gap</p>
            <TextBlock text={gap.gap_summary} className="mt-1 text-slate-300" />
          </div>
        ) : null}
        <div className="rounded-lg border border-violet-500/25 bg-violet-950/20 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-violet-200">Ask the admin</p>
          <p className="mt-2 text-sm font-medium leading-relaxed text-slate-100">{gap.question_for_admin}</p>
        </div>
        {gap.notes ? <TextBlock text={gap.notes} className="text-xs text-slate-500" /> : null}
        <p className="text-xs text-slate-500">
          Hackathon demo: answers are not collected or stored. Full ThinkingSOC supports admin Q&amp;A workflows.
        </p>
      </div>
    </NeonGlassCard>
  )
}

function SocAnalysisStack({ data }: { data: Record<string, unknown> }) {
  const judge = pickJudgeFromData(data)
  const summary = pickSummaryFromData(data)
  const hunter = asRecord(data.hunter)
  const framework = Array.isArray(data.framework_mapping) ? data.framework_mapping : []
  const questionItems = normalizeInvestigationQuestions(
    pickInvestigationQuestionsRaw(data),
    asRecord(data.root_cause_spl)
  )
  const evidenceChain = asRecord(data.evidence_chain)
  const adminOrgGap = normalizeAdminOrgGap(data.admin_org_gap)
  const judgeMcp = judge ? parseMcpJudgeEvidence(judge.mcp_evidence) : null
  const hunterMcp = hunter ? parseMcpHunterEvidence(hunter.mcp_evidence) : null

  return (
    <div className="space-y-3">
      {hasActiveAdminOrgGap(adminOrgGap) && adminOrgGap ? (
        <AdminOrgGapPanel gap={adminOrgGap} />
      ) : null}

      {summary ? (
        <DataSection title="Summary" accent="orange" defaultOpen>
          <TextBlock text={summary} />
        </DataSection>
      ) : null}

      {typeof data.defender === "string" && data.defender ? (
        <DataSection title="Defender" defaultOpen={false}>
          <TextBlock text={data.defender} />
        </DataSection>
      ) : null}

      {hunter ? (
        <DataSection title="Hunter" defaultOpen={false}>
          <TextBlock text={String(hunter.narrative ?? "")} />
        </DataSection>
      ) : null}

      {judge ? (
        <DataSection title="Judge verdict" description="Priority and recommended action" accent="orange">
          <FieldGrid
            fields={[
              { label: "Verdict", value: judge.verdict },
              { label: "Priority", value: judge.priority },
              { label: "Confidence", value: judge.confidence },
              { label: "Next step", value: judge.recommended_next_step },
            ]}
          />
          <TextBlock text={String(judge.rationale ?? "")} className="mt-2 border-t border-white/10 pt-2" />
        </DataSection>
      ) : null}

      {judgeMcp ? (
        <DataSection
          title="Splunk MCP verdict evidence"
          description="SAIA guidance and verification queries — after Defender and Hunter"
          accent="teal"
          defaultOpen={false}
        >
          <McpJudgeEvidencePanel evidence={judgeMcp} showHeader={false} />
        </DataSection>
      ) : null}

      {hunterMcp ? (
        <DataSection
          title="Splunk MCP hunt evidence"
          description="Live correlation queries after Defender"
          accent="teal"
          defaultOpen={false}
        >
          <McpHunterEvidencePanel evidence={hunterMcp} showHeader={false} />
        </DataSection>
      ) : null}

      {hunter &&
      Array.isArray(hunter.splunk_search_suggestions) &&
      hunter.splunk_search_suggestions.length > 0 ? (
        <DataSection
          title="Splunk search ideas"
          description="Suggested SPL from Hunter"
          accent="teal"
          defaultOpen={false}
        >
          <HunterSplSearchIdeasPanel
            suggestions={hunter.splunk_search_suggestions as string[]}
            showHeader={false}
          />
        </DataSection>
      ) : null}

      {hasEnrichmentContent(data) ? (
        <DataSection title="Inventory enrichment" defaultOpen={false}>
          <EnrichmentPanelContent data={data} />
        </DataSection>
      ) : null}

      <ThreatIntelSection data={data} />

      {framework.length > 0 ? (
        <DataSection title="Framework mapping" defaultOpen={false}>
          <FrameworkList framework={framework} />
        </DataSection>
      ) : null}

      {questionItems.length > 0 ? (
        <DataSection title="Questions & SPL" defaultOpen={false}>
          <InvestigationQuestionsSplList items={questionItems} />
        </DataSection>
      ) : null}

      {asRecord(data.evidence_chain) ? (
        <DataSection title="Evidence chain" defaultOpen={false}>
          <SocAnalysisEvidenceChainPanel data={data} />
        </DataSection>
      ) : null}
    </div>
  )
}

export function parseInvestigationAnalysis(data: Record<string, unknown>) {
  const judge = pickJudgeFromData(data)
  const summary = pickSummaryFromData(data)
  const hunterRaw = asRecord(data.hunter)
  const hunter: HunterDebateData | null = hunterRaw
    ? {
        narrative: String(hunterRaw.narrative ?? ""),
        splunk_search_suggestions: Array.isArray(hunterRaw.splunk_search_suggestions)
          ? (hunterRaw.splunk_search_suggestions as string[])
          : [],
        mcp_evidence: parseMcpHunterEvidence(hunterRaw.mcp_evidence),
      }
    : null
  const framework = Array.isArray(data.framework_mapping) ? data.framework_mapping : []
  const questionItems = normalizeInvestigationQuestions(
    pickInvestigationQuestionsRaw(data),
    asRecord(data.root_cause_spl)
  )
  const evidenceChain = asRecord(data.evidence_chain)

  const threatIntel = pickThreatIntel(data)
  const adminOrgGap = normalizeAdminOrgGap(data.admin_org_gap)

  const defender =
    typeof data.defender === "string" && data.defender.trim().length > 0 ? data.defender.trim() : ""
  const triage = pickTriageFromAnalysis(data)
  const triageReport = triage ? asRecord(triage.report) : null
  const triageRecommended =
    typeof triageReport?.recommended_action === "string" &&
    triageReport.recommended_action.trim().length > 0
  const judgeNextStep = pickJudgeRecommendedStep(judge)
  const judgeRationale =
    judge != null && typeof judge.rationale === "string" ? judge.rationale.trim() : ""

  return {
    triage,
    threatIntel,
    hasThreatIntel: threatIntel != null,
    adminOrgGap,
    hasAdminGap: hasActiveAdminOrgGap(adminOrgGap),
    judge,
    hunter,
    defender,
    summary,
    questionItems,
    evidenceChain,
    hasEnrichment: hasEnrichmentContent(data),
    hasFramework: framework.length > 0,
    hasQuestions: questionItems.length > 0,
    hasEvidenceChain: evidenceChain != null,
    hasTriage: triage != null,
    hasRecommendedActions:
      judgeNextStep.length > 0 || judgeRationale.length > 0 || triageRecommended,
    hasCourt:
      judge != null ||
      defender.length > 0 ||
      (hunter != null &&
        (hunter.narrative.trim().length > 0 ||
          (hunter.splunk_search_suggestions?.length ?? 0) > 0 ||
          hunter.mcp_evidence != null)),
  }
}

export function SocAnalysisEvidenceChainPanel({ data }: { data: Record<string, unknown> }) {
  const evidenceChain = asRecord(data.evidence_chain)
  if (!evidenceChain) {
    return <p className="text-sm text-slate-500">No evidence chain on this record.</p>
  }
  return (
    <div className="space-y-3" data-testid="security-evidence-chain-panel">
      <p className="text-xs text-slate-500">
        Traceable lineage from request inputs to final judge decision.
      </p>
      <pre
        className={cn(
          "overflow-x-auto rounded-lg border border-teal-500/20 bg-black/50 p-3 font-mono text-xs text-teal-100",
          tsocNativeScrollbarClasses
        )}
      >
        {JSON.stringify(evidenceChain, null, 2)}
      </pre>
    </div>
  )
}

export function SocAnalysisAdminGapPanel({ data }: { data: Record<string, unknown> }) {
  const gap = normalizeAdminOrgGap(data.admin_org_gap)
  return (
    <div className="space-y-4" data-testid="security-admin-gap-panel">
      <p className="text-xs text-slate-500">
        Ask your IT / security administrator to confirm policy and ownership. Answers are not stored in
        this hackathon demo.
      </p>
      <AdminOrgGapPanel gap={gap} />
    </div>
  )
}

export function SocAnalysisSummaryCard({ data }: { data: Record<string, unknown> }) {
  const summary = pickSummaryFromData(data)
  if (!summary) return null

  return (
    <NeonGlassCard accent="orange" data-testid="security-summary-card">
      <NeonCardHeader
        accent="orange"
        title="Summary"
        description="Executive overview"
        className="px-4 py-3"
      />
      <div className="px-4 pb-4">
        <TextBlock text={summary} />
      </div>
    </NeonGlassCard>
  )
}

export function SocAnalysisInvestigationOverview({ data }: { data: Record<string, unknown> }) {
  const sections = parseInvestigationAnalysis(data)

  return (
    <div className="space-y-6">
      {sections.hasAdminGap && sections.adminOrgGap ? (
        <AdminOrgGapPanel gap={sections.adminOrgGap} />
      ) : null}

      {sections.hasThreatIntel ? <ThreatIntelSection data={data} /> : null}
    </div>
  )
}

export type InvestigationRecommendedAction = {
  source: string
  text: string
  /** Card subtitle under the source name. */
  description?: string
  /** Supporting context (e.g. Judge rationale under the next step). */
  detail?: string
  primary?: boolean
}

/**
 * All analyst-facing recommendation text for the Recommended action tab.
 * Verdict labels and score breakdown stay on Triage / Hunter & defender tabs.
 */
export function collectInvestigationRecommendedActions(
  data: Record<string, unknown>
): InvestigationRecommendedAction[] {
  const sections = parseInvestigationAnalysis(data)
  const steps: InvestigationRecommendedAction[] = []

  const judge = sections.judge
  const judgeStep = pickJudgeRecommendedStep(judge)
  const judgeRationale =
    judge != null && typeof judge.rationale === "string" ? judge.rationale.trim() : ""

  if (judgeStep) {
    steps.push({
      source: "Judge",
      text: judgeStep,
      detail: judgeRationale || undefined,
      primary: true,
    })
  } else if (judgeRationale) {
    steps.push({ source: "Judge", text: judgeRationale, primary: true })
  }

  const triageReport = sections.triage ? asRecord(sections.triage.report) : null
  const triageStep =
    typeof triageReport?.recommended_action === "string"
      ? triageReport.recommended_action.trim()
      : ""
  if (triageStep) {
    steps.push({ source: "Triage", text: triageStep })
  }

  return steps
}

export function SocAnalysisRecommendedActionPanel({ data }: { data: Record<string, unknown> }) {
  const steps = collectInvestigationRecommendedActions(data)
  if (steps.length === 0) {
    return (
      <p className="text-sm text-slate-500" data-testid="security-recommended-action-panel">
        No actionable next steps on this record. See{" "}
        <span className="text-slate-400">Hunter & defender</span> for agent rationale or{" "}
        <span className="text-slate-400">Triage</span> for priority scoring.
      </p>
    )
  }

  return (
    <div className="space-y-4" data-testid="security-recommended-action-panel">
      <p className="text-xs text-slate-500">
        Recommended steps from Judge and post-analysis triage. Defender skepticism and Hunter hypotheses
        are on the Hunter & defender tab.
      </p>
      {steps.map((step, index) => (
        <NeonGlassCard key={`${step.source}-${index}`} accent={step.source === "Defender" ? "violet" : "orange"}>
          <NeonCardHeader
            accent={step.source === "Defender" ? "violet" : "orange"}
            icon={
              step.source === "Defender" ? (
                <ShieldIcon className="size-5 text-violet-400" />
              ) : (
                <ListChecksIcon className="size-5 text-orange-400" />
              )
            }
            title={step.primary ? "Primary next step" : step.source}
            description={
              step.description ??
              (step.primary ? `From ${step.source}` : "Recommended action")
            }
            className="px-4 py-3"
          />
          <div className="space-y-3 px-4 pb-4">
            <p className="text-sm font-medium leading-relaxed text-slate-100">{step.text}</p>
            {step.detail ? (
              <TextBlock text={step.detail} className="border-t border-white/10 pt-3 text-slate-300" />
            ) : null}
          </div>
        </NeonGlassCard>
      ))}
    </div>
  )
}

export function SocAnalysisTriagePanel({ data }: { data: Record<string, unknown> }) {
  const sections = parseInvestigationAnalysis(data)
  if (!sections.triage) {
    return <p className="text-sm text-slate-500">No triage outcome for this record.</p>
  }
  return (
    <div data-testid="security-triage-panel">
      <TriageCard triage={sections.triage} />
    </div>
  )
}

export function SocAnalysisCourtPanel({ data }: { data: Record<string, unknown> }) {
  const sections = parseInvestigationAnalysis(data)
  if (!sections.hasCourt) {
    return <p className="text-sm text-slate-500">No hunter or defender analysis for this record.</p>
  }
  return (
    <AgentCourt
      defender={sections.defender}
      hunter={sections.hunter}
      judge={sections.judge}
    />
  )
}

export function SocAnalysisEnrichmentPanel({ data }: { data: Record<string, unknown> }) {
  return <EnrichmentPanelContent data={data} />
}

/** @deprecated Use SocAnalysisEnrichmentPanel */
export const SocAnalysisIdentityPanel = SocAnalysisEnrichmentPanel

/** @deprecated Risk is shown inside the Enrichment tab via {@link EnrichmentPanelContent}. */
export function SocAnalysisRiskPanel({ data }: { data: Record<string, unknown> }) {
  const risk = typeof data.risk_context === "string" ? data.risk_context.trim() : ""
  if (!risk) return <p className="text-sm text-slate-500">No risk context.</p>
  return <TextBlock text={risk} />
}

export function SocAnalysisThreatIntelPanel({ data }: { data: Record<string, unknown> }) {
  return <ThreatIntelPanel data={data} />
}

export function SocAnalysisFrameworkPanel({ data }: { data: Record<string, unknown> }) {
  const framework = Array.isArray(data.framework_mapping) ? data.framework_mapping : []
  if (framework.length === 0) return <p className="text-sm text-slate-500">No framework mapping.</p>
  return <FrameworkList framework={framework} />
}

export function SocAnalysisQuestionsPanel({ data }: { data: Record<string, unknown> }) {
  const items = normalizeInvestigationQuestions(
    pickInvestigationQuestionsRaw(data),
    asRecord(data.root_cause_spl)
  )
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">No investigation questions with SPL.</p>
  }
  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500">
        Each SPL includes SAIA analysis (Splunk AI Assistant via MCP) by default, plus execution
        results and LLM interpretation when available.
      </p>
      <InvestigationQuestionsSplList items={items} />
    </div>
  )
}

/** @deprecated Merged into SocAnalysisQuestionsPanel */
export function SocAnalysisRootSplPanel({ data }: { data: Record<string, unknown> }) {
  return <SocAnalysisQuestionsPanel data={data} />
}

export function SocAnalysisView({
  data,
  layout = "stack",
}: {
  data: Record<string, unknown>
  layout?: "stack" | "investigation"
}) {
  if (layout === "investigation") {
    return (
      <div className="space-y-6">
        <SocAnalysisSummaryCard data={data} />
        <SocAnalysisInvestigationOverview data={data} />
      </div>
    )
  }
  return <SocAnalysisStack data={data} />
}
