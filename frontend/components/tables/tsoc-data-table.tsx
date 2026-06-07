"use client"

import * as React from "react"
import { ArrowDownIcon, ArrowUpDownIcon, ArrowUpIcon } from "lucide-react"

import {
  NeonTable,
  NeonTableBody,
  NeonTableCell,
  NeonTableHead,
  NeonTableHeader,
  NeonTableRow,
  type NeonAccent,
} from "@/components/neon-glass"
import { TsocHorizontalScroll } from "@/components/ui/tsoc-scroll"
import { tsocNativeScrollbarClasses } from "@/lib/ui-scroll"
import { cn } from "@/lib/utils"

import { TsocTablePagination } from "./tsoc-table-pagination"
import { TsocTableToolbar } from "./tsoc-table-toolbar"
import { useTsocTable } from "./use-tsoc-table"

export type TsocFilterOption = { label: string; value: string }

export type TsocColumn<T> = {
  id: string
  header: React.ReactNode
  cell: (row: T) => React.ReactNode
  headClassName?: string
  cellClassName?: string
  sortable?: boolean
  sortValue?: (row: T) => string | number | null | undefined
  searchValue?: (row: T) => string | number | null | undefined
  filterable?: boolean
  filterLabel?: string
  filterOptions?: TsocFilterOption[]
  filterValue?: (row: T) => string | null | undefined
}

export type TsocDataTableProps<T> = {
  columns: TsocColumn<T>[]
  rows: T[]
  getRowKey: (row: T) => string
  accent?: NeonAccent
  emptyMessage?: string
  loading?: boolean
  loadingMessage?: string
  maxHeight?: string
  onRowClick?: (row: T) => void
  selectedRowKey?: string | null
  className?: string
  enableSearch?: boolean
  enablePagination?: boolean
  enableFilters?: boolean
  searchPlaceholder?: string
  defaultPageSize?: number
  pageSizeOptions?: number[]
  globalSearchFn?: (row: T, query: string) => boolean
  tableContainerClassName?: string
  enableTimeFilter?: boolean
  getRowTime?: (row: T) => unknown
  timeFilterStorageKey?: string
  defaultSortColumnId?: string | null
  defaultSortDirection?: "asc" | "desc"
}

const tableWrapperClasses = [
  "[&_tbody_tr]:border-white/5",
  "[&_tbody_tr:hover]:bg-white/5",
  "[&_tbody_tr[data-state=selected]]:bg-teal-500/10",
  "[&_tbody_tr[data-state=selected]]:border-teal-500/20",
  "[&_input]:bg-black/40",
  "[&_input]:border-white/10",
  "[&_[data-slot=select-trigger]]:bg-black/40",
  "[&_[data-slot=select-trigger]]:border-white/10",
  "[&_button:not(.header-sort-btn)]:bg-black/20",
  "[&_button:not(.header-sort-btn)]:border-white/10",
].join(" ")

export function TsocDataTable<T>({
  columns,
  rows,
  getRowKey,
  accent = "teal",
  emptyMessage = "No records",
  loading = false,
  loadingMessage = "Loading…",
  maxHeight = "420px",
  onRowClick,
  selectedRowKey,
  className,
  enableSearch = true,
  enablePagination = true,
  enableFilters = true,
  searchPlaceholder,
  defaultPageSize = 10,
  pageSizeOptions,
  globalSearchFn,
  tableContainerClassName,
  enableTimeFilter = false,
  getRowTime,
  timeFilterStorageKey,
  defaultSortColumnId = null,
  defaultSortDirection = "desc",
}: TsocDataTableProps<T>) {
  const table = useTsocTable({
    rows,
    columns,
    defaultPageSize,
    defaultSortColumnId,
    defaultSortDirection,
    globalSearchFn,
    getRowTime: enableTimeFilter ? getRowTime : undefined,
    timeFilterStorageKey: enableTimeFilter ? timeFilterStorageKey : undefined,
  })

  const displayRows = enablePagination ? table.pageRows : table.sortedRows
  const showInitialLoading = loading && rows.length === 0

  function sortIcon(columnId: string) {
    if (table.sortColumnId !== columnId) {
      return <ArrowUpDownIcon className="size-3.5 opacity-50" />
    }
    return table.sortDirection === "asc" ? (
      <ArrowUpIcon className="size-3.5" />
    ) : (
      <ArrowDownIcon className="size-3.5" />
    )
  }

  return (
    <div
      className={cn(
        "min-w-0 overflow-hidden rounded-xl border border-white/10 bg-black/10 backdrop-blur-sm",
        tableContainerClassName,
        className
      )}
    >
      {enableSearch || enableFilters || (enableTimeFilter && table.timeFilterEnabled) ? (
        <TsocTableToolbar
          accent={accent}
          search={table.search}
          onSearchChange={table.setSearch}
          searchPlaceholder={searchPlaceholder}
          columns={enableFilters ? columns : columns.map((c) => ({ ...c, filterable: false }))}
          getColumnFilterValue={table.getColumnFilterValue}
          onColumnFilterChange={table.setColumnFilter}
          showTimeFilter={enableTimeFilter && table.timeFilterEnabled}
          timeFilter={table.timeFilter}
          onTimeFilterChange={table.setTimeFilter}
        />
      ) : null}

      {showInitialLoading ? (
        <p className="p-6 text-center font-mono text-slate-400">{loadingMessage}</p>
      ) : (
      <TsocHorizontalScroll className="p-6 pt-4">
        <div className={cn("min-w-[800px]", tableWrapperClasses)}>
          <div style={{ maxHeight }} className={cn("overflow-auto", tsocNativeScrollbarClasses)}>
            <NeonTable>
              <NeonTableHeader>
                <NeonTableRow>
                  {columns.map((col) => {
                    const canSort = Boolean(col.sortable && col.sortValue)
                    return (
                      <NeonTableHead
                        key={col.id}
                        className={cn(canSort && "border-0", col.headClassName)}
                      >
                        {canSort ? (
                          <button
                            type="button"
                            className="header-sort-btn inline-flex items-center gap-1 border-0 bg-transparent p-0 text-left font-medium text-slate-400 shadow-none ring-0 hover:bg-white/5 focus-visible:ring-0"
                            onClick={() => table.toggleSort(col.id)}
                          >
                            {col.header}
                            {sortIcon(col.id)}
                          </button>
                        ) : (
                          col.header
                        )}
                      </NeonTableHead>
                    )
                  })}
                </NeonTableRow>
              </NeonTableHeader>
              <NeonTableBody>
                {loading ? (
                  <NeonTableRow>
                    <NeonTableCell colSpan={columns.length} className="text-slate-500">
                      {loadingMessage}
                    </NeonTableCell>
                  </NeonTableRow>
                ) : displayRows.length === 0 ? (
                  <NeonTableRow>
                    <NeonTableCell colSpan={columns.length} className="text-slate-500">
                      {emptyMessage}
                    </NeonTableCell>
                  </NeonTableRow>
                ) : (
                  displayRows.map((row) => {
                    const key = getRowKey(row)
                    return (
                      <NeonTableRow
                        key={key}
                        className={onRowClick ? "cursor-pointer" : undefined}
                        onClick={onRowClick ? () => onRowClick(row) : undefined}
                        data-state={selectedRowKey === key ? "selected" : undefined}
                      >
                        {columns.map((col) => (
                          <NeonTableCell key={col.id} className={col.cellClassName}>
                            {col.cell(row)}
                          </NeonTableCell>
                        ))}
                      </NeonTableRow>
                    )
                  })
                )}
              </NeonTableBody>
            </NeonTable>
          </div>
        </div>
      </TsocHorizontalScroll>
      )}

      {enablePagination && !loading ? (
        <TsocTablePagination
          accent={accent}
          totalRows={table.totalRows}
          pageIndex={table.pageIndex}
          pageSize={table.pageSize}
          pageSizeOptions={pageSizeOptions}
          onPageIndexChange={table.setPageIndex}
          onPageSizeChange={table.setPageSize}
        />
      ) : null}
    </div>
  )
}
