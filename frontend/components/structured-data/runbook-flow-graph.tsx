"use client"

import { Fragment, useMemo, useState } from "react"
import {
  ArrowRightIcon,
  CheckCircle2Icon,
  FileSearchIcon,
  GitBranchIcon,
  PlayIcon,
  ShieldCheckIcon,
  TargetIcon,
} from "lucide-react"

import type {
  RunbookApproval,
  RunbookRun,
  RunbookSourceResult,
  VerifiedRunbookDraft,
} from "@/lib/api/investigation-workflow"
import { cn } from "@/lib/utils"
import { MarkdownContent } from "./mcp-markdown-content"

type FlowNodeTone = "teal" | "violet" | "emerald" | "slate"

type FlowNode = {
  id: string
  eyebrow: string
  title: string
  description: string
  status: string
  tone: FlowNodeTone
  icon: React.ReactNode
  details: Array<{ label: string; value: string }>
}

const TONE_CLASSES: Record<
  FlowNodeTone,
  { border: string; active: string; icon: string; status: string; line: string }
> = {
  teal: {
    border: "border-teal-500/20 hover:border-teal-400/40",
    active: "border-teal-400/45 bg-teal-500/[0.065] shadow-[0_16px_45px_-26px_rgba(45,212,191,0.34)]",
    icon: "border-teal-500/20 bg-teal-500/[0.08] text-teal-300",
    status: "text-teal-300",
    line: "from-teal-400/50",
  },
  violet: {
    border: "border-violet-500/20 hover:border-violet-400/40",
    active: "border-violet-400/45 bg-violet-500/[0.06] shadow-[0_16px_45px_-26px_rgba(167,139,250,0.30)]",
    icon: "border-violet-500/20 bg-violet-500/[0.07] text-violet-300",
    status: "text-violet-300",
    line: "from-violet-400/50",
  },
  emerald: {
    border: "border-emerald-500/20 hover:border-emerald-400/40",
    active: "border-emerald-400/45 bg-emerald-500/[0.055] shadow-[0_16px_45px_-26px_rgba(52,211,153,0.28)]",
    icon: "border-emerald-500/20 bg-emerald-500/[0.07] text-emerald-300",
    status: "text-emerald-300",
    line: "from-emerald-400/50",
  },
  slate: {
    border: "border-white/10 hover:border-slate-300/25",
    active: "border-slate-300/30 bg-white/[0.045] shadow-[0_16px_45px_-26px_rgba(203,213,225,0.22)]",
    icon: "border-white/10 bg-white/[0.045] text-slate-300",
    status: "text-slate-300",
    line: "from-slate-400/40",
  },
}

function stepStatus(result: RunbookSourceResult | undefined) {
  if (result?.spl_results?.error) return { label: "FAILED", tone: "slate" as const }
  if ((result?.spl_results?.row_count ?? 0) > 0 && result?.validation?.valid === true) {
    return { label: "EVIDENCE VERIFIED", tone: "emerald" as const }
  }
  if (result?.validation?.valid === true) return { label: "PARSER VALID", tone: "teal" as const }
  return { label: "DRAFT", tone: "slate" as const }
}

function buildNodes(
  draft: VerifiedRunbookDraft,
  approval: RunbookApproval | null,
  latestRun: RunbookRun | null
): FlowNode[] {
  const nodes: FlowNode[] = [
    {
      id: "source",
      eyebrow: "Source",
      title: `Investigation #${draft.source_record_id}`,
      description: draft.summary,
      status: draft.source_verdict.replaceAll("_", " "),
      tone: "teal",
      icon: <FileSearchIcon className="size-4" />,
      details: [
        { label: "Detection", value: draft.applicable_search_name },
        { label: "Runbook", value: draft.title },
        { label: "Source verdict", value: draft.source_verdict.replaceAll("_", " ") },
      ],
    },
  ]

  draft.steps.forEach((step, index) => {
    const result = draft.source_results[index]
    const state = stepStatus(result)
    nodes.push({
      id: step.step_id,
      eyebrow: `Step ${index + 1}`,
      title: step.title,
      description: step.intent,
      status: state.label,
      tone: state.tone,
      icon: <GitBranchIcon className="size-4" />,
      details: [
        { label: "Intent", value: step.intent },
        { label: "Expected evidence", value: step.expected_evidence },
        { label: "Stop condition", value: step.stop_condition },
        {
          label: "Source check",
          value: `${result?.spl_results?.row_count ?? 0} row(s) · ${result?.validation?.valid === true ? "parser valid" : "not verified"}`,
        },
      ],
    })
  })

  const decision = approval?.decision
  nodes.push({
    id: "decision",
    eyebrow: "Human gate",
    title: decision === "approve" ? "Runbook approved" : decision === "reject" ? "Runbook rejected" : "Awaiting review",
    description: draft.decision_rule,
    status: decision ? decision.toUpperCase() : "REVIEW REQUIRED",
    tone: decision === "approve" ? "emerald" : decision === "reject" ? "slate" : "violet",
    icon: decision === "approve" ? <CheckCircle2Icon className="size-4" /> : <ShieldCheckIcon className="size-4" />,
    details: [
      { label: "Decision rule", value: draft.decision_rule },
      { label: "Analyst decision", value: decision ? decision.toUpperCase() : "Not recorded" },
      { label: "Review note", value: approval?.note || "No review note recorded" },
    ],
  })

  nodes.push({
    id: "reuse",
    eyebrow: "Safe reuse",
    title: latestRun ? `Target #${latestRun.target_record_id}` : "Exact-match target",
    description: latestRun
      ? "The approved runbook was regenerated and executed against this stored alert."
      : `Available only for another stored alert named “${draft.applicable_search_name}”.`,
    status: latestRun?.status.replaceAll("_", " ") || (decision === "approve" ? "READY" : "LOCKED"),
    tone: latestRun?.status === "REUSED" ? "emerald" : decision === "approve" ? "teal" : "slate",
    icon: latestRun ? <PlayIcon className="size-4" /> : <TargetIcon className="size-4" />,
    details: latestRun
      ? [
          { label: "Target record", value: `#${latestRun.target_record_id}` },
          { label: "Evidence", value: `${latestRun.total_evidence_rows} row(s)` },
          { label: "Measured runtime", value: `${(latestRun.duration_ms / 1000).toFixed(1)} seconds` },
          { label: "Estimated time saved", value: `${latestRun.estimated_minutes_saved.toFixed(1)} minutes` },
        ]
      : [
          { label: "Eligibility", value: "Approved runbook and exact detection-name match" },
          { label: "Execution", value: "Fresh, validated, read-only SPL" },
          { label: "Current state", value: decision === "approve" ? "Ready for a compatible target" : "Locked until approval" },
        ],
  })

  return nodes
}

export function RunbookFlowGraph({
  draft,
  approval,
  latestRun,
}: {
  draft: VerifiedRunbookDraft
  approval: RunbookApproval | null
  latestRun: RunbookRun | null
}) {
  const nodes = useMemo(
    () => buildNodes(draft, approval, latestRun),
    [approval, draft, latestRun]
  )
  const [selectedId, setSelectedId] = useState(nodes[0]?.id ?? "source")

  const selected = nodes.find((node) => node.id === selectedId) ?? nodes[0]

  return (
    <section
      className="relative overflow-hidden rounded-xl border border-white/[0.07] bg-[radial-gradient(circle_at_top_left,rgba(20,184,166,0.055),transparent_40%),linear-gradient(145deg,rgba(15,23,42,0.72),rgba(0,0,0,0.62))] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.035)] sm:p-5"
      aria-labelledby="runbook-flow-title"
      data-testid="runbook-flow-graph"
    >
      <div className="pointer-events-none absolute -right-16 -top-20 size-56 rounded-full bg-teal-500/[0.055] blur-3xl" />
      <div className="relative flex flex-wrap items-start justify-between gap-3">
        <div>
          <h4 id="runbook-flow-title" className="text-sm font-semibold text-slate-100">
            Runbook execution graph
          </h4>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Select a rectangular node to inspect its evidence, gate, and safe-reuse contract.
          </p>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-slate-400" aria-label="Graph legend">
          <span className="size-2 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.8)]" />
          Verified
          <span className="ml-2 size-2 rounded-full bg-violet-400 shadow-[0_0_10px_rgba(167,139,250,0.8)]" />
          Human gate
        </div>
      </div>

      <div className="relative mt-5 overflow-x-auto pb-2">
        <div
          className={cn(
            "flex min-w-0 flex-col items-stretch gap-0 xl:flex-row xl:items-center",
            nodes.length > 5 && "xl:min-w-[1160px]"
          )}
          role="list"
          aria-label="Runbook execution path"
        >
          {nodes.map((node, index) => {
            const selectedNode = node.id === selected?.id
            const tone = TONE_CLASSES[node.tone]
            return (
              <Fragment key={node.id}>
                <div className="min-w-0 xl:flex-1" role="listitem">
                  <button
                    type="button"
                    aria-pressed={selectedNode}
                    aria-label={`${node.eyebrow}: ${node.title}`}
                    onClick={() => setSelectedId(node.id)}
                    className={cn(
                      "group relative flex min-h-36 w-full min-w-0 flex-col overflow-hidden rounded-xl border bg-black/35 p-4 text-left outline-none transition duration-300 ease-out",
                      "hover:-translate-y-0.5 hover:bg-white/[0.045] hover:shadow-[0_16px_38px_-28px_rgba(148,163,184,0.28)]",
                      "focus-visible:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-teal-400/35 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950",
                      "motion-reduce:transform-none motion-reduce:transition-none",
                      tone.border,
                      selectedNode && cn("-translate-y-0.5", tone.active)
                    )}
                  >
                    <span
                      className={cn(
                        "absolute inset-x-0 top-0 h-px bg-gradient-to-r via-current to-transparent opacity-30 transition-opacity group-hover:opacity-100",
                        tone.line
                      )}
                    />
                    <span className="flex items-start justify-between gap-3">
                      <span className={cn("flex size-9 shrink-0 items-center justify-center rounded-lg border", tone.icon)}>
                        {node.icon}
                      </span>
                      <span className={cn("text-[10px] font-semibold uppercase tracking-[0.16em]", tone.status)}>
                        {node.status}
                      </span>
                    </span>
                    <span className="mt-3 text-[10px] font-medium uppercase tracking-[0.18em] text-slate-500">
                      {node.eyebrow}
                    </span>
                    <MarkdownContent
                      content={node.title}
                      compact
                      className="mt-1 block text-sm font-semibold leading-5 text-slate-100"
                    />
                    <MarkdownContent
                      content={node.description}
                      compact
                      className="mt-2 line-clamp-3 text-xs leading-5 text-slate-400"
                    />
                    <span
                      className={cn(
                        "absolute bottom-0 left-0 h-0.5 bg-gradient-to-r to-transparent transition-all duration-300",
                        tone.line,
                        selectedNode ? "w-2/3 opacity-100" : "w-0 opacity-0 group-hover:w-1/2 group-hover:opacity-80"
                      )}
                    />
                  </button>
                </div>
                {index < nodes.length - 1 ? (
                  <div
                    className="relative flex h-9 shrink-0 items-center justify-center xl:h-auto xl:w-8"
                    aria-hidden="true"
                  >
                    <span className="h-full w-px bg-gradient-to-b from-teal-400/35 via-white/15 to-violet-400/30 xl:h-px xl:w-full xl:bg-gradient-to-r" />
                    <ArrowRightIcon className="absolute size-3.5 rotate-90 text-teal-300/55 xl:right-0 xl:rotate-0" />
                  </div>
                ) : null}
              </Fragment>
            )
          })}
        </div>
      </div>

      {selected ? (
        <div
          className="relative mt-3 rounded-xl border border-white/10 bg-black/35 p-4 shadow-inner shadow-black/30"
          aria-live="polite"
          data-testid="runbook-flow-details"
        >
          <div className="flex items-center gap-2">
            <span className={cn("flex size-7 items-center justify-center rounded-md border", TONE_CLASSES[selected.tone].icon)}>
              {selected.icon}
            </span>
            <div>
              <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-slate-500">Selected node</p>
              <p className="text-sm font-semibold text-slate-100"><MarkdownContent content={selected.title} compact /></p>
            </div>
          </div>
          <dl className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {selected.details.map((detail) => (
              <div key={`${selected.id}-${detail.label}`} className="min-w-0 rounded-lg border border-white/[0.07] bg-white/[0.025] p-3">
                <dt className="text-[10px] font-medium uppercase tracking-wide text-slate-500">{detail.label}</dt>
                <dd className="mt-1 break-words text-xs leading-5 text-slate-300"><MarkdownContent content={detail.value} compact /></dd>
              </div>
            ))}
          </dl>
        </div>
      ) : null}
    </section>
  )
}
