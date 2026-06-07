"use client"

import { TsocOverflowScroll } from "@/components/ui/tsoc-scroll"
import type { OperationStatusResponse } from "@/lib/api/graph/types"
import { cn } from "@/lib/utils"

export function OperationStatusViewer({
  status,
  className,
}: {
  status: OperationStatusResponse | null
  className?: string
}) {
  if (!status) {
    return (
      <p className={cn("text-sm text-slate-400", className)}>
        Waiting for operation status…
      </p>
    )
  }

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-slate-400">Status:</span>
        <span
          className={cn(
            "rounded-md border px-2 py-0.5 font-medium capitalize",
            status.status === "completed" &&
              "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
            status.status === "failed" &&
              "border-red-500/30 bg-red-500/10 text-red-300",
            status.status === "running" &&
              "border-amber-500/30 bg-amber-500/10 text-amber-300",
          )}
        >
          {status.status}
        </span>
        <span className="text-slate-500">{status.message}</span>
      </div>
      <TsocOverflowScroll className="max-h-48 rounded-lg border border-white/10 bg-black/30 p-3">
        <ul className="space-y-1 font-mono text-xs text-slate-300">
          {status.detailed_logs.map((entry, i) => (
            <li key={`${entry.timestamp ?? i}-${entry.message}`}>
              {entry.timestamp ? (
                <span className="text-slate-500">
                  [{entry.timestamp.slice(11, 19)}]{" "}
                </span>
              ) : null}
              <span
                className={cn(
                  entry.level === "error" && "text-red-400",
                  entry.level === "warn" && "text-amber-400",
                )}
              >
                {entry.message}
              </span>
            </li>
          ))}
        </ul>
      </TsocOverflowScroll>
    </div>
  )
}
