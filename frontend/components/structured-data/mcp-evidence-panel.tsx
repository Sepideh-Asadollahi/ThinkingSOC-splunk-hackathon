"use client"

import { SparklesIcon } from "lucide-react"

import { NeonBadge } from "@/components/neon-glass"
import { tsocNativeScrollbarClasses } from "@/lib/ui-scroll"
import { cn } from "@/lib/utils"

import { asRecord } from "./utils"
import { McpMarkdownContent } from "./mcp-markdown-content"

export const LITELLM_FALLBACK_ANSWER_PREFIX =
  "[LiteLLM fallback — Splunk AI Assistant unavailable]"

/** Split LiteLLM fallback banner from markdown body in SAIA answers. */
export function parseSaiaAnswerText(answer: string): {
  isFallback: boolean
  fallbackLabel: string | null
  body: string
} {
  const trimmed = answer.trim()
  const fallbackMatch = trimmed.match(/^\[(LiteLLM fallback[^\]]*)\]\s*([\s\S]*)$/i)
  if (fallbackMatch) {
    return {
      isFallback: true,
      fallbackLabel: fallbackMatch[1] ?? null,
      body: (fallbackMatch[2] ?? "").trim(),
    }
  }
  return { isFallback: false, fallbackLabel: null, body: trimmed }
}

export type McpQueryEvidence = {
  query: string
  row_count: number
  summary: string
  error?: string | null
}

export type McpSaiaAnswer = {
  question: string
  answer: string
}

export type McpHunterEvidence = {
  tools_called: string[]
  hunt_queries: McpQueryEvidence[]
  metadata_sourcetypes: string[]
  notes: string[]
}

export type McpJudgeEvidence = {
  tools_called: string[]
  saia_answers: McpSaiaAnswer[]
  verification_queries: McpQueryEvidence[]
  notes: string[]
}

function parseQueryList(raw: unknown): McpQueryEvidence[] {
  if (!Array.isArray(raw)) return []
  return raw
    .map((item): McpQueryEvidence | null => {
      const row = asRecord(item)
      if (!row || typeof row.query !== "string") return null
      return {
        query: row.query,
        row_count: typeof row.row_count === "number" ? row.row_count : Number(row.row_count ?? 0),
        summary: String(row.summary ?? ""),
        error: row.error != null ? String(row.error) : null,
      }
    })
    .filter((x): x is McpQueryEvidence => x != null)
}

function parseSaiaAnswers(raw: unknown): McpSaiaAnswer[] {
  if (!Array.isArray(raw)) return []
  return raw
    .map((item) => {
      const row = asRecord(item)
      if (!row) return null
      const question = String(row.question ?? "").trim()
      const answer = String(row.answer ?? "").trim()
      if (!question && !answer) return null
      return { question, answer }
    })
    .filter((x): x is McpSaiaAnswer => x != null)
}

function parseStringList(raw: unknown): string[] {
  if (!Array.isArray(raw)) return []
  return raw.map((x) => String(x)).filter(Boolean)
}

export function parseMcpHunterEvidence(raw: unknown): McpHunterEvidence | null {
  const row = asRecord(raw)
  if (!row) return null
  const evidence: McpHunterEvidence = {
    tools_called: parseStringList(row.tools_called),
    hunt_queries: parseQueryList(row.hunt_queries),
    metadata_sourcetypes: parseStringList(row.metadata_sourcetypes),
    notes: parseStringList(row.notes),
  }
  if (
    evidence.tools_called.length === 0 &&
    evidence.hunt_queries.length === 0 &&
    evidence.metadata_sourcetypes.length === 0
  ) {
    return null
  }
  return evidence
}

export function parseMcpJudgeEvidence(raw: unknown): McpJudgeEvidence | null {
  const row = asRecord(raw)
  if (!row) return null
  const evidence: McpJudgeEvidence = {
    tools_called: parseStringList(row.tools_called),
    saia_answers: parseSaiaAnswers(row.saia_answers),
    verification_queries: parseQueryList(row.verification_queries),
    notes: parseStringList(row.notes),
  }
  if (
    evidence.tools_called.length === 0 &&
    evidence.saia_answers.length === 0 &&
    evidence.verification_queries.length === 0
  ) {
    return null
  }
  return evidence
}

export function pickMcpHunterFromAnalysis(data: Record<string, unknown>): McpHunterEvidence | null {
  const hunter = asRecord(data.hunter)
  return hunter ? parseMcpHunterEvidence(hunter.mcp_evidence) : null
}

export function pickMcpJudgeFromAnalysis(data: Record<string, unknown>): McpJudgeEvidence | null {
  const judge = asRecord(data.judge)
  if (judge) return parseMcpJudgeEvidence(judge.mcp_evidence)
  const jo = asRecord(data.judge_output)
  const nested = jo ? asRecord(jo.judge) : null
  return nested ? parseMcpJudgeEvidence(nested.mcp_evidence) : null
}

function McpSectionHeader({ title }: { title: string }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <SparklesIcon className="size-3.5 shrink-0 text-cyan-400/90" aria-hidden />
      <p className="text-[10px] font-semibold uppercase tracking-wide text-cyan-300/90">{title}</p>
    </div>
  )
}

function McpToolBadges({ tools }: { tools: string[] }) {
  if (tools.length === 0) return null
  const unique = Array.from(new Set(tools))
  return (
    <div className="flex flex-wrap gap-1">
      {unique.map((tool) => (
        <NeonBadge key={tool} className="border-cyan-500/30 font-mono text-[10px] text-cyan-200/90">
          {tool}
        </NeonBadge>
      ))}
    </div>
  )
}

function McpQueryBlock({ item, index }: { item: McpQueryEvidence; index: number }) {
  return (
    <div
      className="rounded-lg border border-cyan-500/15 bg-cyan-950/10 p-3"
      data-testid={`mcp-query-${index}`}
    >
      <p className="font-mono text-[11px] leading-relaxed text-cyan-100/90">{item.query}</p>
      {item.error ? (
        <p className="mt-2 text-xs text-amber-400/90">Error: {item.error}</p>
      ) : (
        <p className="mt-2 text-[10px] text-slate-500">{item.row_count} row(s)</p>
      )}
      {item.summary && item.summary !== "(no rows)" ? (
        <pre
          className={cn(
            "mt-2 max-h-32 overflow-auto rounded border border-white/5 bg-black/40 p-2 font-mono text-[10px] text-slate-300",
            tsocNativeScrollbarClasses
          )}
        >
          {item.summary}
        </pre>
      ) : null}
    </div>
  )
}

function McpSaiaQaList({ answers }: { answers: McpSaiaAnswer[] }) {
  if (answers.length === 0) return null
  return (
    <div className="space-y-4" data-testid="mcp-saia-qa-list">
      {answers.map((item, index) => {
        const parsed = parseSaiaAnswerText(item.answer)
        return (
          <div
            key={index}
            className="w-full min-w-0 rounded-lg border border-violet-500/20 bg-violet-950/15 p-4"
            data-testid={`mcp-saia-qa-${index}`}
          >
            <p className="text-[10px] font-semibold uppercase tracking-wide text-violet-300/80">Question</p>
            <p className="mt-1 text-sm leading-relaxed text-slate-100">{item.question}</p>
            <p className="mt-4 text-[10px] font-semibold uppercase tracking-wide text-violet-300/80">
              {parsed.isFallback ? "LiteLLM fallback answer" : "SAIA answer"}
            </p>
            {parsed.isFallback && parsed.fallbackLabel ? (
              <NeonBadge
                className="mt-2 border-amber-500/40 text-[10px] text-amber-200"
                data-testid={`mcp-saia-fallback-badge-${index}`}
              >
                {parsed.fallbackLabel}
              </NeonBadge>
            ) : null}
            <McpMarkdownContent content={parsed.body} className="mt-2 w-full" />
          </div>
        )
      })}
    </div>
  )
}

export function McpHunterEvidencePanel({
  evidence,
  className,
  showHeader = true,
}: {
  evidence: McpHunterEvidence
  className?: string
  showHeader?: boolean
}) {
  return (
    <div className={cn("space-y-3", className)} data-testid="mcp-hunter-evidence">
      {showHeader ? (
        <>
          <McpSectionHeader title="Splunk MCP hunt evidence" />
          <p className="text-xs text-slate-500">
            Live correlation queries run before Hunter — ground truth to expand or counter Defender.
          </p>
        </>
      ) : null}
      <McpToolBadges tools={evidence.tools_called} />
      {evidence.metadata_sourcetypes.length > 0 ? (
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
            Index sourcetypes
          </p>
          <div className="flex flex-wrap gap-1">
            {evidence.metadata_sourcetypes.slice(0, 12).map((st) => (
              <NeonBadge key={st} className="border-white/10 text-[10px] text-slate-300">
                {st}
              </NeonBadge>
            ))}
          </div>
        </div>
      ) : null}
      {evidence.hunt_queries.length > 0 ? (
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
            Live hunt queries
          </p>
          {evidence.hunt_queries.map((q, i) => (
            <McpQueryBlock key={i} item={q} index={i} />
          ))}
        </div>
      ) : null}
      {evidence.notes.length > 0 ? (
        <p className="text-xs text-slate-500">{evidence.notes.join(" · ")}</p>
      ) : null}
    </div>
  )
}

export function McpJudgeEvidencePanel({
  evidence,
  className,
  showHeader = true,
}: {
  evidence: McpJudgeEvidence
  className?: string
  showHeader?: boolean
}) {
  return (
    <div className={cn("w-full min-w-0 space-y-4", className)} data-testid="mcp-judge-evidence">
      {showHeader ? (
        <>
          <McpSectionHeader title="Splunk MCP verdict evidence" />
          <p className="text-xs text-slate-500">
            Gathered after Defender and Hunter — weight SAIA guidance and verification query row counts
            in the verdict rationale.
          </p>
        </>
      ) : null}
      <McpToolBadges tools={evidence.tools_called} />
      {evidence.saia_answers.length > 0 ? (
        <div>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
            SAIA questions &amp; answers
          </p>
          <McpSaiaQaList answers={evidence.saia_answers} />
        </div>
      ) : null}
      {evidence.verification_queries.length > 0 ? (
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
            Verification queries
          </p>
          {evidence.verification_queries.map((q, i) => (
            <McpQueryBlock key={i} item={q} index={i} />
          ))}
        </div>
      ) : null}
      {evidence.notes.length > 0 ? (
        <p className="text-xs text-slate-500">{evidence.notes.join(" · ")}</p>
      ) : null}
    </div>
  )
}
