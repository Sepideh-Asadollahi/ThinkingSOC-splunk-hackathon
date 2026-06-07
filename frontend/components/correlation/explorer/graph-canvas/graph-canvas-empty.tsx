import { cn } from "@/lib/utils"

export function GraphCanvasEmpty({
  statusMessage,
  className,
}: {
  statusMessage: string | null
  className?: string
}) {
  return (
    <div
      className={cn(
        "flex h-full min-h-[320px] items-center justify-center rounded-xl border border-white/10 bg-black/30 text-sm text-slate-400",
        className,
      )}
    >
      {statusMessage && statusMessage !== "Success."
        ? statusMessage
        : "No nodes match the current filters"}
    </div>
  )
}
