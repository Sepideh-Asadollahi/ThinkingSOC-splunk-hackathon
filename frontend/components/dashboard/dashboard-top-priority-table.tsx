"use client"

import Link from "next/link"
import { ArrowRightIcon } from "lucide-react"

import { NeonBadge, NeonCardHeader, NeonGlassCard } from "@/components/neon-glass"
import { investigationHrefForRow } from "@/lib/analysis-payload"
import type { TopPriorityItem } from "@/lib/api/types"
import { triagePriorityBadgeClass, triageVerdictBadgeClass } from "@/lib/triage-display"
import { cn } from "@/lib/utils"

export function DashboardTopPriorityTable({
  items,
}: {
  items: TopPriorityItem[]
}) {
  return (
    <NeonGlassCard accent="teal" animatePreset="page">
      <NeonCardHeader
        accent="teal"
        title="Top priority queue"
        description="Highest triage scores from stored analyses"
        actions={
          <Link
            href="/analysis"
            className="inline-flex items-center gap-1 text-sm text-teal-400 hover:text-teal-300"
          >
            View all
            <ArrowRightIcon className="size-4" />
          </Link>
        }
        className="px-4 pt-4"
      />
      {items.length === 0 ? (
        <p className="px-4 pb-4 text-sm text-slate-500">No analyzed alerts in storage yet.</p>
      ) : (
        <div className="divide-y divide-white/[0.06]">
          {items.map((item, index) => {
            const href = investigationHrefForRow(item as Record<string, unknown>)
            const searchName = item.search_name || item.sid || `Record ${item.id ?? index + 1}`
            const verdict = item.review_verdict ?? "—"
            const priority = item.investigation_priority ?? "—"

            const row = (
              <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
                <div className="min-w-0">
                  <p className="truncate font-medium text-white">{searchName}</p>
                  <p className="text-xs text-slate-500">
                    Score {item.triage_score ?? 0}
                    {item.source_track ? ` · ${item.source_track}` : ""}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <NeonBadge
                    className={cn("border", triageVerdictBadgeClass(String(verdict)))}
                  >
                    {String(verdict).replace(/_/g, " ")}
                  </NeonBadge>
                  <NeonBadge
                    className={cn("border", triagePriorityBadgeClass(String(priority)))}
                  >
                    {priority}
                  </NeonBadge>
                  {item.needs_human_review ? (
                    <NeonBadge className="border border-amber-500/40 text-amber-300">
                      Review
                    </NeonBadge>
                  ) : null}
                </div>
              </div>
            )

            if (!href) {
              return <div key={`${searchName}-${index}`}>{row}</div>
            }

            return (
              <Link
                key={href}
                href={href}
                className="block transition-colors hover:bg-white/[0.03]"
              >
                {row}
              </Link>
            )
          })}
        </div>
      )}
    </NeonGlassCard>
  )
}
