"use client"

import { SearchIcon } from "lucide-react"

import { getNeonSelectContentClassName, NeonInput } from "@/components/neon-glass"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"

import { TsocTimeFilter } from "./tsoc-time-filter"

import type { NeonAccent } from "@/components/neon-glass/accent"
import type { TsocColumn } from "./tsoc-data-table"

type TsocTableToolbarProps<T> = {
  accent?: NeonAccent
  search: string
  onSearchChange: (value: string) => void
  searchPlaceholder?: string
  columns: TsocColumn<T>[]
  getColumnFilterValue: (columnId: string) => string
  onColumnFilterChange: (columnId: string, value: string) => void
  timeFilter?: string
  onTimeFilterChange?: (value: string) => void
  showTimeFilter?: boolean
  className?: string
}

export function TsocTableToolbar<T>({
  accent = "teal",
  search,
  onSearchChange,
  searchPlaceholder = "Search table…",
  columns,
  getColumnFilterValue,
  onColumnFilterChange,
  timeFilter = "all",
  onTimeFilterChange,
  showTimeFilter = false,
  className,
}: TsocTableToolbarProps<T>) {
  const filterableColumns = columns.filter((c) => c.filterable && c.filterOptions?.length)
  const selectContentClass = getNeonSelectContentClassName(accent)
  const hasFilters = filterableColumns.length > 0 || showTimeFilter

  return (
    <div className={cn("space-y-3 border-b border-white/5 px-6 py-4", className)}>
      <div className="flex flex-wrap items-center gap-2">
        <SearchIcon className="size-4 shrink-0 text-slate-400" aria-hidden />
        <NeonInput
          accent={accent}
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={searchPlaceholder}
          className="max-w-md flex-1 font-mono text-xs"
          aria-label="Search table"
        />
        <span className="text-xs font-mono text-slate-400">
          Type to filter rows across searchable columns
        </span>
      </div>
      {hasFilters ? (
        <div className="flex flex-wrap items-center gap-3">
          {showTimeFilter && onTimeFilterChange ? (
            <TsocTimeFilter
              accent={accent}
              value={timeFilter}
              onValueChange={onTimeFilterChange}
            />
          ) : null}
          {filterableColumns.map((col) => (
            <div key={col.id} className="flex items-center gap-2">
              <span className="text-xs text-slate-400">{col.filterLabel ?? col.id}</span>
              <Select
                value={getColumnFilterValue(col.id)}
                onValueChange={(v) => onColumnFilterChange(col.id, v)}
              >
                <SelectTrigger
                  size="sm"
                  className="h-8 min-w-[120px] border-white/10 bg-black/40 text-white"
                >
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent className={selectContentClass}>
                  <SelectItem value="__all__">All</SelectItem>
                  {(col.filterOptions ?? []).map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}
