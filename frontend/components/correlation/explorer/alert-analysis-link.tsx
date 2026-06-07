"use client"

import { ExternalLinkIcon } from "lucide-react"
import Link from "next/link"

import type { AlertDisplayInfo } from "@/lib/api/graph/alert-display"
import { cn } from "@/lib/utils"

export function AlertAnalysisLink({
  info,
  className,
  variant = "inline",
}: {
  info: AlertDisplayInfo | undefined
  className?: string
  variant?: "inline" | "button"
}) {
  if (!info?.analysisHref) return null

  const base =
    variant === "button"
      ? "inline-flex items-center gap-1 rounded-md border border-orange-500/35 bg-orange-500/10 px-2 py-1 text-xs font-medium text-orange-200 hover:bg-orange-500/20"
      : "inline-flex items-center gap-0.5 text-orange-300 hover:text-orange-200 underline-offset-2 hover:underline"

  return (
    <Link
      href={info.analysisHref}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(base, className)}
      title="Open SOC analysis in a new tab"
    >
      Analysis
      <ExternalLinkIcon className="size-3 shrink-0 opacity-80" aria-hidden />
    </Link>
  )
}
