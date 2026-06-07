"use client"

import type { AlertFrameworkContext } from "@/lib/api/graph/attack-framework"
import { cn } from "@/lib/utils"

export function FrameworkBadges({
  ctx,
  size = "sm",
  className,
}: {
  ctx: AlertFrameworkContext | undefined
  size?: "sm" | "xs"
  className?: string
}) {
  if (!ctx) return null
  const hasKill = Boolean(ctx.killChainPhase)
  const hasMitre = Boolean(
    ctx.mitreTechniqueId || ctx.mitreTechniqueName || ctx.mitreTactic,
  )
  if (!hasKill && !hasMitre) return null

  const text = size === "xs" ? "text-[9px]" : "text-[10px]"
  const pad = size === "xs" ? "px-1 py-0" : "px-1.5 py-0.5"

  return (
    <div className={cn("flex flex-wrap gap-1", className)}>
      {hasKill ? (
        <span
          className={cn(
            "rounded border border-amber-500/35 bg-amber-500/10 font-medium text-amber-200/95",
            text,
            pad,
          )}
        >
          KC: {ctx.killChainPhase}
        </span>
      ) : null}
      {ctx.mitreTechniqueId ? (
        <span
          className={cn(
            "rounded border border-violet-500/35 bg-violet-500/10 font-mono text-violet-200/95",
            text,
            pad,
          )}
          title={ctx.mitreTechniqueName ?? ctx.mitreTactic}
        >
          {ctx.mitreTechniqueId}
        </span>
      ) : null}
      {ctx.mitreTactic && !ctx.mitreTechniqueId ? (
        <span
          className={cn(
            "rounded border border-violet-500/25 bg-violet-500/10 text-violet-200/90",
            text,
            pad,
          )}
        >
          {ctx.mitreTactic}
        </span>
      ) : null}
      {ctx.mitreTechniqueName && ctx.mitreTechniqueId ? (
        <span className={cn("text-slate-500", text)}>{ctx.mitreTechniqueName}</span>
      ) : null}
    </div>
  )
}

export function FrameworkSummaryStrip({
  killChainPhases,
  mitreTechniques,
  className,
}: {
  killChainPhases: string[]
  mitreTechniques: string[]
  className?: string
}) {
  if (!killChainPhases.length && !mitreTechniques.length) return null

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-2 rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-xs",
        className,
      )}
    >
      {killChainPhases.length ? (
        <div className="flex flex-wrap items-center gap-1">
          <span className="font-semibold uppercase tracking-wide text-amber-400/90">
            Kill chain
          </span>
          {killChainPhases.map((p) => (
            <span
              key={p}
              className="rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-amber-100"
            >
              {p}
            </span>
          ))}
        </div>
      ) : null}
      {mitreTechniques.length ? (
        <div className="flex flex-wrap items-center gap-1">
          <span className="font-semibold uppercase tracking-wide text-violet-400/90">
            MITRE
          </span>
          {mitreTechniques.map((t) => (
            <span
              key={t}
              className="rounded border border-violet-500/30 bg-violet-500/10 px-1.5 py-0.5 font-mono text-violet-100"
            >
              {t}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  )
}
