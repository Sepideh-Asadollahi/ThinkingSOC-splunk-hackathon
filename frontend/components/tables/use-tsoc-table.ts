"use client"

import { useMemo, useState } from "react"

import {
  readStoredTimeFilter,
  rowMatchesTimeFilter,
  writeStoredTimeFilter,
} from "@/lib/time-utils"
import { compareValues, pageCount, paginateSlice, type SortDirection } from "@/lib/tsoc-table"

import type { TsocColumn } from "./tsoc-data-table"

export type TsocColumnFilter = {
  columnId: string
  value: string
}

export type UseTsocTableOptions<T> = {
  rows: T[]
  columns: TsocColumn<T>[]
  defaultPageSize?: number
  defaultSortColumnId?: string | null
  defaultSortDirection?: SortDirection
  globalSearchFn?: (row: T, query: string) => boolean
  getRowTime?: (row: T) => unknown
  timeFilterStorageKey?: string
}

function initialSortState<T>(
  columns: TsocColumn<T>[],
  defaultSortColumnId?: string | null,
  defaultSortDirection: SortDirection = "desc",
): { columnId: string | null; direction: SortDirection } {
  if (!defaultSortColumnId) {
    return { columnId: null, direction: "asc" }
  }
  const col = columns.find((c) => c.id === defaultSortColumnId)
  if (!col?.sortable || !col.sortValue) {
    return { columnId: null, direction: "asc" }
  }
  return { columnId: defaultSortColumnId, direction: defaultSortDirection }
}

export function useTsocTable<T>({
  rows,
  columns,
  defaultPageSize = 10,
  defaultSortColumnId = null,
  defaultSortDirection = "desc",
  globalSearchFn,
  getRowTime,
  timeFilterStorageKey,
}: UseTsocTableOptions<T>) {
  const [search, setSearch] = useState("")
  const [timeFilter, setTimeFilterState] = useState(() => {
    if (timeFilterStorageKey) {
      return readStoredTimeFilter(timeFilterStorageKey) ?? "all"
    }
    return "all"
  })
  const [columnFilters, setColumnFilters] = useState<TsocColumnFilter[]>([])
  const [sortColumnId, setSortColumnId] = useState<string | null>(
    () => initialSortState(columns, defaultSortColumnId, defaultSortDirection).columnId
  )
  const [sortDirection, setSortDirection] = useState<SortDirection>(
    () => initialSortState(columns, defaultSortColumnId, defaultSortDirection).direction
  )
  const [pageIndex, setPageIndex] = useState(0)
  const [pageSize, setPageSize] = useState(defaultPageSize)

  const timeFilterEnabled = Boolean(getRowTime)

  const filteredRows = useMemo(() => {
    let result = rows

    if (getRowTime && timeFilter !== "all") {
      result = result.filter((row) => rowMatchesTimeFilter(getRowTime(row), timeFilter))
    }

    const q = search.trim().toLowerCase()
    if (q) {
      result = result.filter((row) => {
        if (globalSearchFn) return globalSearchFn(row, q)
        return columns.some((col) => {
          const text = col.searchValue?.(row) ?? col.sortValue?.(row)
          return text != null && String(text).toLowerCase().includes(q)
        })
      })
    }

    for (const filter of columnFilters) {
      if (!filter.value || filter.value === "__all__") continue
      const col = columns.find((c) => c.id === filter.columnId)
      if (!col?.filterValue) continue
      result = result.filter((row) => col.filterValue!(row) === filter.value)
    }

    return result
  }, [rows, search, timeFilter, columnFilters, columns, globalSearchFn, getRowTime])

  const sortedRows = useMemo(() => {
    if (!sortColumnId) return filteredRows
    const col = columns.find((c) => c.id === sortColumnId)
    if (!col?.sortValue) return filteredRows
    const sorted = [...filteredRows]
    sorted.sort((a, b) => {
      const cmp = compareValues(col.sortValue!(a), col.sortValue!(b))
      return sortDirection === "asc" ? cmp : -cmp
    })
    return sorted
  }, [filteredRows, sortColumnId, sortDirection, columns])

  const totalRows = sortedRows.length
  const totalPages = pageCount(totalRows, pageSize)
  const safePageIndex = Math.min(pageIndex, totalPages - 1)
  const pageRows = useMemo(
    () => paginateSlice(sortedRows, safePageIndex, pageSize),
    [sortedRows, safePageIndex, pageSize]
  )

  function toggleSort(columnId: string) {
    const col = columns.find((c) => c.id === columnId)
    if (!col?.sortable || !col.sortValue) return
    if (sortColumnId !== columnId) {
      setSortColumnId(columnId)
      setSortDirection("asc")
      setPageIndex(0)
      return
    }
    if (sortDirection === "asc") {
      setSortDirection("desc")
      return
    }
    setSortColumnId(null)
    setSortDirection("asc")
  }

  function setColumnFilter(columnId: string, value: string) {
    setColumnFilters((prev) => {
      const rest = prev.filter((f) => f.columnId !== columnId)
      if (!value || value === "__all__") return rest
      return [...rest, { columnId, value }]
    })
    setPageIndex(0)
  }

  function getColumnFilterValue(columnId: string): string {
    return columnFilters.find((f) => f.columnId === columnId)?.value ?? "__all__"
  }

  function setSearchQuery(value: string) {
    setSearch(value)
    setPageIndex(0)
  }

  function setTimeFilter(value: string) {
    setTimeFilterState(value)
    if (timeFilterStorageKey) {
      writeStoredTimeFilter(timeFilterStorageKey, value)
    }
    setPageIndex(0)
  }

  function setPageSizeAndReset(size: number) {
    setPageSize(size)
    setPageIndex(0)
  }

  return {
    search,
    setSearch: setSearchQuery,
    timeFilter,
    setTimeFilter,
    timeFilterEnabled,
    sortColumnId,
    sortDirection,
    toggleSort,
    setColumnFilter,
    getColumnFilterValue,
    pageIndex: safePageIndex,
    setPageIndex,
    pageSize,
    setPageSize: setPageSizeAndReset,
    totalRows,
    totalPages,
    pageRows,
    filteredRows,
    sortedRows,
  }
}
