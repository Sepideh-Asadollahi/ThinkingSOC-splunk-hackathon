"use client"

import { isValidElement, type ReactNode } from "react"

import { NeonBadge } from "@/components/neon-glass"
import { tsocOverflowYAutoClasses } from "@/lib/ui-scroll"
import { cn } from "@/lib/utils"

import { formatPrimitive } from "./utils"

export type FieldGridItem = {
  label: string
  value: unknown
  mono?: boolean
  /** Stable React key; use when multiple fields share the same label. */
  fieldKey?: string
}

export function FieldGrid({
  fields,
  className,
}: {
  fields: FieldGridItem[]
  className?: string
}) {
  return (
    <dl className={cn("grid gap-2 sm:grid-cols-2", className)}>
      {fields.map(({ label, value, mono, fieldKey }, index) => (
        <div
          key={fieldKey ?? `${label}-${index}`}
          className="rounded-md border border-white/10 bg-black/30 px-3 py-2"
        >
          <dt className="text-[10px] font-medium uppercase tracking-wide text-slate-500">{label}</dt>
          <dd className="mt-0.5 text-sm text-slate-200">
            <FieldValue value={value} mono={mono} />
          </dd>
        </div>
      ))}
    </dl>
  )
}

function FieldValue({ value, mono }: { value: unknown; mono?: boolean }) {
  if (isValidElement(value)) return value
  if (typeof value === "boolean") {
    return (
      <NeonBadge className={value ? "border-emerald-500/40 text-emerald-300" : "border-slate-500/40 text-slate-400"}>
        {value ? "Yes" : "No"}
      </NeonBadge>
    )
  }
  if (Array.isArray(value) && value.every((v) => typeof v === "string" || typeof v === "number")) {
    return (
      <ul className="flex flex-wrap gap-1">
        {value.map((item, i) => (
          <NeonBadge key={i} className="border-white/15 text-slate-300">
            {String(item)}
          </NeonBadge>
        ))}
      </ul>
    )
  }
  const text = formatPrimitive(value)
  const long = text.length > 120
  return (
    <span
      className={cn(
        mono && "font-mono text-xs",
        long && cn("block max-h-24 whitespace-pre-wrap", tsocOverflowYAutoClasses)
      )}
    >
      {text}
    </span>
  )
}
