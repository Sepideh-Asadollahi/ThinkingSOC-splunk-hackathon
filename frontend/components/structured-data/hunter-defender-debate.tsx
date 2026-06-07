"use client"

import type { ReactNode } from "react"
import { CrosshairIcon, GavelIcon, MessagesSquareIcon, ShieldIcon, SparklesIcon } from "lucide-react"

import { NeonCardHeader, NeonFloatingIconBox, NeonGlassCard } from "@/components/neon-glass"
import { cn } from "@/lib/utils"

import { FieldGrid } from "./field-grid"
import { HunterSplSearchIdeasSection } from "./hunter-spl-search-ideas"
import {
  McpHunterEvidencePanel,
  McpJudgeEvidencePanel,
  parseMcpHunterEvidence,
  parseMcpJudgeEvidence,
  type McpHunterEvidence,
} from "./mcp-evidence-panel"

export type HunterDebateData = {
  narrative: string
  splunk_search_suggestions?: string[]
  mcp_evidence?: McpHunterEvidence | null
}

function SpeechBubble({
  text,
  align,
  accent,
}: {
  text: string
  align: "left" | "right"
  accent: "violet" | "orange"
}) {
  const border =
    accent === "violet"
      ? "border-violet-500/25 bg-violet-500/5"
      : "border-orange-500/25 bg-orange-500/5"
  const corner = align === "left" ? "rounded-tl-sm" : "rounded-tr-sm"

  if (!text) {
    return (
      <p className="rounded-2xl border border-dashed border-white/10 bg-black/20 px-4 py-6 text-center text-sm text-slate-500">
        No output from this agent
      </p>
    )
  }

  return (
    <div
      className={cn(
        "rounded-2xl border px-4 py-3 text-sm leading-relaxed text-slate-200",
        border,
        corner
      )}
    >
      <p className="whitespace-pre-wrap">{text}</p>
    </div>
  )
}

function AgentColumn({
  role,
  title,
  subtitle,
  accent,
  align,
  icon,
  text,
  children,
}: {
  role: string
  title: string
  subtitle: string
  accent: "violet" | "orange"
  align: "left" | "right"
  icon: ReactNode
  text: string
  children?: ReactNode
}) {
  return (
    <NeonGlassCard accent={accent} className="flex h-full flex-col">
      <div
        className={cn(
          "flex items-center gap-3 border-b border-white/[0.06] px-4 py-3",
          align === "right" && "flex-row-reverse text-right"
        )}
      >
        <NeonFloatingIconBox accent={accent} animate={false} className="size-10 shrink-0">
          {icon}
        </NeonFloatingIconBox>
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">{role}</p>
          <h3 className="text-base font-semibold text-slate-100">{title}</h3>
          <p className="text-xs text-slate-500">{subtitle}</p>
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <SpeechBubble text={text} align={align} accent={accent} />
        {children}
      </div>
    </NeonGlassCard>
  )
}

function HunterExpansionSection({
  hunterMcp,
  splSuggestions,
}: {
  hunterMcp: McpHunterEvidence | null
  splSuggestions: string[]
}) {
  if (!hunterMcp && splSuggestions.length === 0) return null

  return (
    <div className="w-full space-y-4" data-testid="hunter-expansion-section">
      {hunterMcp ? (
        <NeonGlassCard accent="teal" className="w-full min-w-0" data-testid="mcp-hunter-evidence-section">
          <NeonCardHeader
            accent="teal"
            icon={<SparklesIcon className="size-5 text-teal-300" />}
            title="Splunk MCP hunt evidence"
            description="Live correlation queries after Defender — ground truth for hunt expansion"
            className="px-4 py-3"
          />
          <div className="w-full min-w-0 px-4 pb-4">
            <McpHunterEvidencePanel evidence={hunterMcp} showHeader={false} />
          </div>
        </NeonGlassCard>
      ) : null}
      <HunterSplSearchIdeasSection suggestions={splSuggestions} />
    </div>
  )
}

function JudgeBench({
  judge,
  judgeMcp,
}: {
  judge: Record<string, unknown>
  judgeMcp: ReturnType<typeof parseMcpJudgeEvidence>
}) {
  return (
    <div className="space-y-4">
      <NeonGlassCard accent="orange" className="mx-auto w-full max-w-[60rem]">
        <NeonCardHeader
          accent="orange"
          icon={<GavelIcon className="size-5 text-orange-400" />}
          title="Judge"
          description="Final verdict and recommended action"
          className="px-4 py-3 text-center [&_h2]:mx-auto [&_p]:mx-auto"
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
          {typeof judge.rationale === "string" && judge.rationale ? (
            <p className="whitespace-pre-wrap border-t border-white/10 pt-3 text-center text-sm leading-relaxed text-slate-300">
              {judge.rationale}
            </p>
          ) : null}
        </div>
      </NeonGlassCard>

      {judgeMcp ? (
        <NeonGlassCard accent="teal" className="w-full min-w-0" data-testid="mcp-judge-evidence-section">
          <NeonCardHeader
            accent="teal"
            icon={<SparklesIcon className="size-5 text-teal-300" />}
            title="Splunk MCP verdict evidence"
            description="SAIA guidance and verification queries — read after Defender and Hunter above"
            className="px-4 py-3"
          />
          <div className="w-full min-w-0 px-4 pb-4">
            <McpJudgeEvidencePanel evidence={judgeMcp} showHeader={false} />
          </div>
        </NeonGlassCard>
      ) : null}
    </div>
  )
}

/** Hunter (left) vs Defender (right) with optional Judge centered below. */
export function AgentCourt({
  defender,
  hunter,
  judge,
  className,
}: {
  defender?: string | null
  hunter?: HunterDebateData | null
  judge?: Record<string, unknown> | null
  className?: string
}) {
  const defenderText = typeof defender === "string" ? defender.trim() : ""
  const hunterNarrative = hunter?.narrative?.trim() ?? ""
  const splSuggestions = hunter?.splunk_search_suggestions?.filter(Boolean) ?? []
  const hunterMcp = hunter?.mcp_evidence ?? null
  const hasDefender = defenderText.length > 0
  const hasHunter =
    hunterNarrative.length > 0 || splSuggestions.length > 0 || hunterMcp != null
  const hasJudge = judge != null && Object.keys(judge).length > 0
  const judgeMcp = judge ? parseMcpJudgeEvidence(judge.mcp_evidence) : null

  if (!hasDefender && !hasHunter && !hasJudge) return null

  return (
    <section className={cn("space-y-6", className)} data-testid="agent-court">
      <div className="flex items-center gap-2 px-1">
        <GavelIcon className="size-4 text-orange-400/80" aria-hidden />
        <h3 className="text-sm font-medium text-slate-200">Hunter & defender</h3>
        <div
          className="h-px flex-1 bg-gradient-to-r from-orange-500/30 via-white/10 to-violet-500/30"
          aria-hidden
        />
      </div>

      {(hasHunter || hasDefender) && (
        <div className="relative">
          <div className="relative grid gap-4 lg:grid-cols-2 lg:gap-8">
            <div
              className="pointer-events-none absolute left-1/2 top-1/2 z-10 hidden -translate-x-1/2 -translate-y-1/2 lg:flex"
              aria-hidden
            >
              <div className="flex size-10 items-center justify-center rounded-full border border-white/15 bg-[#0a0a0a] shadow-lg">
                <MessagesSquareIcon className="size-4 text-slate-400" />
              </div>
            </div>

            <div className="order-1">
              <AgentColumn
                role="Investigation view"
                title="Hunter"
                subtitle="Hypotheses & hunt paths"
                accent="orange"
                align="left"
                icon={<CrosshairIcon className="size-5 text-orange-400" />}
                text={hunterNarrative}
              />
            </div>

            <div className="order-2 flex justify-center py-1 lg:hidden" aria-hidden>
              <div className="h-8 w-px bg-gradient-to-b from-orange-500/40 via-white/20 to-violet-500/40" />
            </div>

            <div className="order-3">
              <AgentColumn
                role="Defense advocate"
                title="Defender"
                subtitle="Benign & alternate explanations"
                accent="violet"
                align="right"
                icon={<ShieldIcon className="size-5 text-violet-400" />}
                text={defenderText}
              />
            </div>
          </div>

          {hasJudge ? (
            <div className="pointer-events-none relative mx-auto mt-0 hidden h-10 w-full max-w-lg lg:block" aria-hidden>
              <div className="absolute left-[25%] top-0 h-full w-px bg-gradient-to-b from-orange-500/30 to-orange-500/10" />
              <div className="absolute right-[25%] top-0 h-full w-px bg-gradient-to-b from-violet-500/30 to-violet-500/10" />
              <div className="absolute left-1/2 top-full h-3 w-px -translate-x-1/2 bg-white/20" />
            </div>
          ) : null}
        </div>
      )}

      {hasJudge ? (
        <div className="w-full space-y-4" data-testid="judge-bench-section">
          <JudgeBench judge={judge} judgeMcp={judgeMcp} />
        </div>
      ) : null}

      {hunterMcp || splSuggestions.length > 0 ? (
        <HunterExpansionSection hunterMcp={hunterMcp} splSuggestions={splSuggestions} />
      ) : null}
    </section>
  )
}

/** @deprecated Use AgentCourt */
export function HunterDefenderDebate(props: {
  defender?: string | null
  hunter?: HunterDebateData | null
  className?: string
}) {
  return <AgentCourt {...props} />
}
