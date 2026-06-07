"use client"

import * as React from "react"

import { cn } from "@/lib/utils"

import { getAccentClasses, type NeonAccent } from "./accent"

type NeonInputProps = React.ComponentProps<"input"> & {
  accent?: NeonAccent
}

export function NeonInput({ accent = "teal", className, ...props }: NeonInputProps) {
  const a = getAccentClasses(accent)
  return (
    <input
      className={cn(
        "flex h-9 w-full rounded-md border bg-black/40 border-white/10 px-3 py-1 text-sm text-white shadow-xs placeholder:text-slate-400 outline-none focus-visible:ring-[3px]",
        a.ring,
        className
      )}
      {...props}
    />
  )
}

export function getNeonSelectContentClassName(accent: NeonAccent = "teal") {
  const a = getAccentClasses(accent)
  return cn("bg-[#09090b] border-white/10 text-white", a.border)
}

export function getNeonComboboxTriggerClassName(accent: NeonAccent = "teal") {
  const a = getAccentClasses(accent)
  return cn(
    "bg-black/40 border-white/10 text-white placeholder:text-slate-400",
    a.ring
  )
}

export function getNeonComboboxContentClassName(accent: NeonAccent = "teal") {
  return getNeonSelectContentClassName(accent)
}
