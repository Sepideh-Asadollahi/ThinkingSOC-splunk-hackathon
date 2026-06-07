"use client"

import { useState, type ReactNode } from "react"
import { ChevronDownIcon } from "lucide-react"

import { cn } from "@/lib/utils"

export function DataSection({
  title,
  description,
  defaultOpen = true,
  accent = "slate",
  children,
}: {
  title: string
  description?: string
  defaultOpen?: boolean
  accent?: "slate" | "orange" | "teal" | "violet"
  children: ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  const border =
    accent === "orange"
      ? "border-orange-500/25"
      : accent === "teal"
        ? "border-teal-500/25"
        : accent === "violet"
          ? "border-violet-500/25"
          : "border-white/10"

  return (
    <section className={cn("rounded-lg border bg-black/25", border)}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full cursor-pointer items-center justify-between gap-2 px-3 py-2 text-left"
      >
        <div>
          <h3 className="text-sm font-medium text-slate-100">{title}</h3>
          {description ? <p className="text-xs text-slate-500">{description}</p> : null}
        </div>
        <ChevronDownIcon className={cn("size-4 shrink-0 text-slate-400 transition-transform", open && "rotate-180")} />
      </button>
      {open ? <div className="space-y-3 border-t border-white/10 px-3 py-3">{children}</div> : null}
    </section>
  )
}
