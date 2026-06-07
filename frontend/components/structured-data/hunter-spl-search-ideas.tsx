"use client"

import { SearchIcon } from "lucide-react"

import { NeonCardHeader, NeonGlassCard } from "@/components/neon-glass"
import { tsocNativeScrollbarClasses } from "@/lib/ui-scroll"
import { cn } from "@/lib/utils"

export function HunterSplSearchIdeasPanel({
  suggestions,
  className,
  showHeader = true,
}: {
  suggestions: string[]
  className?: string
  showHeader?: boolean
}) {
  const items = suggestions.map((s) => s.trim()).filter(Boolean)
  if (items.length === 0) return null

  return (
    <div className={cn("w-full min-w-0 space-y-3", className)} data-testid="hunter-spl-search-ideas">
      {showHeader ? (
        <>
          <p className="text-[10px] font-semibold uppercase tracking-wide text-teal-400/80">
            Splunk search ideas
          </p>
          <p className="text-xs text-slate-500">
            Actionable SPL from Hunter — suggested next searches after reviewing MCP hunt evidence.
          </p>
        </>
      ) : null}
      <ul className="space-y-2">
        {items.map((spl, i) => (
          <li
            key={i}
            className={cn(
              "rounded-lg border border-teal-500/20 bg-black/50 px-3 py-2 font-mono text-xs leading-relaxed text-teal-100/90",
              tsocNativeScrollbarClasses
            )}
          >
            {spl}
          </li>
        ))}
      </ul>
    </div>
  )
}

export function HunterSplSearchIdeasSection({ suggestions }: { suggestions: string[] }) {
  const items = suggestions.map((s) => s.trim()).filter(Boolean)
  if (items.length === 0) return null

  return (
    <NeonGlassCard accent="teal" className="w-full min-w-0" data-testid="hunter-spl-search-ideas-section">
      <NeonCardHeader
        accent="teal"
        icon={<SearchIcon className="size-5 text-teal-300" />}
        title="Splunk search ideas"
        description="Suggested SPL from Hunter — run after reviewing live MCP hunt evidence"
        className="px-4 py-3"
      />
      <div className="w-full min-w-0 px-4 pb-4">
        <HunterSplSearchIdeasPanel suggestions={items} showHeader={false} />
      </div>
    </NeonGlassCard>
  )
}
