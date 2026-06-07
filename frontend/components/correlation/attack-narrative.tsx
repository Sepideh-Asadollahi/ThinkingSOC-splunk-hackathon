"use client"

import {
  buildAttackNarrativeSteps,
  type AttackNarrativeStep,
} from "@/lib/api/graph/attack-narrative"
import type { AttackAnalysisStep } from "@/lib/api/graph/types"
import { cn } from "@/lib/utils"

export function AttackNarrative({
  executiveSummary,
  steps,
  className,
  compact = false,
}: {
  executiveSummary?: string | null
  steps?: AttackAnalysisStep[] | null
  className?: string
  compact?: boolean
}) {
  const narrative = buildAttackNarrativeSteps(steps)
  const summary = executiveSummary?.trim()

  if (!summary && narrative.length === 0) {
    return (
      <p className={cn("text-xs text-slate-500", className)}>
        No attack narrative yet — run Attack Discovery or enrich this finding.
      </p>
    )
  }

  return (
    <div className={cn("space-y-3", className)}>
      {summary ? (
        <p
          className={cn(
            "text-slate-300",
            compact ? "text-xs leading-relaxed" : "text-sm leading-relaxed",
          )}
        >
          {summary}
        </p>
      ) : null}
      {narrative.length > 0 ? (
        <AttackNarrativeStepsList steps={narrative} compact={compact} />
      ) : null}
    </div>
  )
}

function AttackNarrativeStepsList({
  steps,
  compact,
}: {
  steps: AttackNarrativeStep[]
  compact?: boolean
}) {
  return (
    <ol className="space-y-2">
      {steps.map((item) => (
        <li
          key={item.step}
          className={cn(
            "flex gap-3 rounded-lg border border-white/10 bg-black/25",
            compact ? "px-2.5 py-2" : "px-3 py-2.5",
          )}
        >
          <span
            className={cn(
              "flex shrink-0 items-center justify-center rounded-full border border-teal-500/40 bg-teal-500/15 font-semibold text-teal-200",
              compact ? "size-6 text-[10px]" : "size-7 text-xs",
            )}
            aria-hidden
          >
            {item.step}
          </span>
          <div className="min-w-0 flex-1">
            <p
              className={cn(
                "font-medium uppercase tracking-wide text-teal-400/90",
                compact ? "text-[10px]" : "text-[11px]",
              )}
            >
              {item.phaseLabel}
            </p>
            <p
              className={cn(
                "mt-0.5 text-slate-200",
                compact ? "text-xs leading-snug" : "text-sm leading-snug",
              )}
            >
              {item.description}
            </p>
            {item.mitreLabel ? (
              <p className="mt-1 font-mono text-[10px] text-slate-500">
                {item.mitreLabel}
              </p>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  )
}
