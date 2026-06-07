import { Loader2Icon } from "lucide-react"

import { cn } from "@/lib/utils"

export function GraphExplorerLoadingState({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex min-h-[320px] flex-col items-center justify-center gap-3 rounded-xl border border-white/10 bg-black/30 text-slate-400",
        className,
      )}
    >
      <Loader2Icon className="size-8 animate-spin text-teal-400" />
      <p className="text-sm">Loading graph topology…</p>
    </div>
  )
}
