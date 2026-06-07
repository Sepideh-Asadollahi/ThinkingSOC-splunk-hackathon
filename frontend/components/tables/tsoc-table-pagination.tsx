"use client"

import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react"

import { getNeonSelectContentClassName } from "@/components/neon-glass"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { showingRange } from "@/lib/tsoc-table"
import { cn } from "@/lib/utils"

import type { NeonAccent } from "@/components/neon-glass/accent"

const DEFAULT_PAGE_SIZES = [10, 25, 50, 100]

type TsocTablePaginationProps = {
  accent?: NeonAccent
  totalRows: number
  pageIndex: number
  pageSize: number
  pageSizeOptions?: number[]
  onPageIndexChange: (index: number) => void
  onPageSizeChange: (size: number) => void
  className?: string
}

export function TsocTablePagination({
  accent = "teal",
  totalRows,
  pageIndex,
  pageSize,
  pageSizeOptions = DEFAULT_PAGE_SIZES,
  onPageIndexChange,
  onPageSizeChange,
  className,
}: TsocTablePaginationProps) {
  const { start, end } = showingRange(totalRows, pageIndex, pageSize)
  const totalPages = Math.max(1, Math.ceil(totalRows / pageSize) || 1)
  const selectContentClass = getNeonSelectContentClassName(accent)

  return (
    <div
      className={cn(
        "flex flex-wrap items-center justify-between gap-4 border-t border-white/5 px-4 py-3 sm:px-6",
        className
      )}
    >
      <p className="text-xs text-slate-400">
        {totalRows === 0
          ? "Showing 0 of 0"
          : `Showing ${start}–${end} of ${totalRows}`}
      </p>
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">Rows per page</span>
          <Select value={String(pageSize)} onValueChange={(v) => onPageSizeChange(Number(v))}>
            <SelectTrigger
              size="sm"
              className="h-8 min-w-[72px] border-white/10 bg-black/40 text-white"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent className={selectContentClass}>
              {pageSizeOptions.map((size) => (
                <SelectItem key={size} value={String(size)}>
                  {size}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="inline-flex h-8 items-center gap-1 rounded-md border border-white/10 bg-black/20 px-2 text-xs text-slate-300 transition-colors hover:bg-white/5 disabled:opacity-40"
            onClick={() => onPageIndexChange(pageIndex - 1)}
            disabled={pageIndex <= 0}
            aria-label="Previous page"
          >
            <ChevronLeftIcon className="size-4" />
            Prev
          </button>
          <span className="min-w-[88px] text-center text-xs text-slate-400">
            Page {pageIndex + 1} of {totalPages}
          </span>
          <button
            type="button"
            className="inline-flex h-8 items-center gap-1 rounded-md border border-white/10 bg-black/20 px-2 text-xs text-slate-300 transition-colors hover:bg-white/5 disabled:opacity-40"
            onClick={() => onPageIndexChange(pageIndex + 1)}
            disabled={pageIndex >= totalPages - 1}
            aria-label="Next page"
          >
            Next
            <ChevronRightIcon className="size-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
