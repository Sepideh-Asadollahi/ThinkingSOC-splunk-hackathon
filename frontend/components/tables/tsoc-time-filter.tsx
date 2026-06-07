"use client"

import { getNeonSelectContentClassName } from "@/components/neon-glass"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { TIME_FILTER_OPTIONS } from "@/lib/time-utils"
import { cn } from "@/lib/utils"

import type { NeonAccent } from "@/components/neon-glass/accent"

type TsocTimeFilterProps = {
  accent?: NeonAccent
  value: string
  onValueChange: (value: string) => void
  className?: string
}

export function TsocTimeFilter({
  accent = "teal",
  value,
  onValueChange,
  className,
}: TsocTimeFilterProps) {
  const selectContentClass = getNeonSelectContentClassName(accent)

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span className="text-xs text-slate-400">Time</span>
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger
          size="sm"
          className="h-8 min-w-[140px] border-white/10 bg-black/40 text-white"
          aria-label="Time filter"
        >
          <SelectValue placeholder="All time" />
        </SelectTrigger>
        <SelectContent className={selectContentClass}>
          {TIME_FILTER_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
