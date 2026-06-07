import { act, renderHook } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import type { TsocColumn } from "./tsoc-data-table"
import { useTsocTable } from "./use-tsoc-table"

type Row = { id: string; name: string; kind: string; score: number }

const columns: TsocColumn<Row>[] = [
  {
    id: "name",
    header: "Name",
    cell: (r) => r.name,
    sortable: true,
    sortValue: (r) => r.name,
    searchValue: (r) => r.name,
  },
  {
    id: "kind",
    header: "Kind",
    cell: (r) => r.kind,
    filterable: true,
    filterOptions: [
      { label: "A", value: "a" },
      { label: "B", value: "b" },
    ],
    filterValue: (r) => r.kind,
  },
  {
    id: "score",
    header: "Score",
    cell: (r) => r.score,
    sortable: true,
    sortValue: (r) => r.score,
  },
]

const rows: Row[] = [
  { id: "1", name: "Zebra", kind: "a", score: 30 },
  { id: "2", name: "Alpha", kind: "b", score: 10 },
  { id: "3", name: "Beta", kind: "a", score: 20 },
  { id: "4", name: "Gamma", kind: "b", score: 5 },
]

describe("useTsocTable", () => {
  it("sorts ascending, descending, then clears sort", () => {
    const { result } = renderHook(() => useTsocTable({ rows, columns, defaultPageSize: 10 }))

    act(() => result.current.toggleSort("score"))
    expect(result.current.sortColumnId).toBe("score")
    expect(result.current.sortDirection).toBe("asc")
    expect(result.current.pageRows.map((r) => r.score)).toEqual([5, 10, 20, 30])

    act(() => result.current.toggleSort("score"))
    expect(result.current.sortDirection).toBe("desc")
    expect(result.current.pageRows.map((r) => r.score)).toEqual([30, 20, 10, 5])

    act(() => result.current.toggleSort("score"))
    expect(result.current.sortColumnId).toBeNull()
    expect(result.current.pageRows.map((r) => r.id)).toEqual(rows.map((r) => r.id))
  })

  it("switches sort column and resets to ascending", () => {
    const { result } = renderHook(() => useTsocTable({ rows, columns, defaultPageSize: 10 }))

    act(() => result.current.toggleSort("score"))
    act(() => result.current.toggleSort("name"))
    expect(result.current.sortColumnId).toBe("name")
    expect(result.current.sortDirection).toBe("asc")
    expect(result.current.pageRows[0]?.name).toBe("Alpha")
  })

  it("ignores toggleSort for non-sortable columns", () => {
    const { result } = renderHook(() => useTsocTable({ rows, columns, defaultPageSize: 10 }))

    act(() => result.current.toggleSort("kind"))
    expect(result.current.sortColumnId).toBeNull()
  })

  it("filters by global search across searchable columns", () => {
    const { result } = renderHook(() => useTsocTable({ rows, columns, defaultPageSize: 10 }))

    act(() => result.current.setSearch("zeb"))
    expect(result.current.totalRows).toBe(1)
    expect(result.current.pageRows[0]?.name).toBe("Zebra")
    expect(result.current.pageIndex).toBe(0)
  })

  it("filters by column filter value", () => {
    const { result } = renderHook(() => useTsocTable({ rows, columns, defaultPageSize: 10 }))

    act(() => result.current.setColumnFilter("kind", "b"))
    expect(result.current.totalRows).toBe(2)
    expect(result.current.pageRows.every((r) => r.kind === "b")).toBe(true)

    act(() => result.current.setColumnFilter("kind", "__all__"))
    expect(result.current.totalRows).toBe(4)
    expect(result.current.getColumnFilterValue("kind")).toBe("__all__")
  })

  it("uses custom globalSearchFn when provided", () => {
    const { result } = renderHook(() =>
      useTsocTable({
        rows,
        columns,
        defaultPageSize: 10,
        globalSearchFn: (row, q) => row.id === q,
      })
    )

    act(() => result.current.setSearch("3"))
    expect(result.current.totalRows).toBe(1)
    expect(result.current.pageRows[0]?.id).toBe("3")
  })

  it("paginates and navigates pages", () => {
    const { result } = renderHook(() =>
      useTsocTable({ rows, columns, defaultPageSize: 2 })
    )

    expect(result.current.pageRows).toHaveLength(2)
    expect(result.current.totalPages).toBe(2)

    act(() => result.current.setPageIndex(1))
    expect(result.current.pageIndex).toBe(1)
    expect(result.current.pageRows).toHaveLength(2)

    act(() => result.current.setPageIndex(99))
    expect(result.current.pageIndex).toBe(1)
  })

  it("resets page index when page size changes", () => {
    const { result } = renderHook(() =>
      useTsocTable({ rows, columns, defaultPageSize: 2 })
    )

    act(() => result.current.setPageIndex(1))
    act(() => result.current.setPageSize(10))
    expect(result.current.pageIndex).toBe(0)
    expect(result.current.pageSize).toBe(10)
    expect(result.current.pageRows).toHaveLength(4)
  })

  it("clamps page index when filters reduce total pages", () => {
    const { result } = renderHook(() =>
      useTsocTable({ rows, columns, defaultPageSize: 2 })
    )

    act(() => result.current.setPageIndex(1))
    act(() => result.current.setSearch("alpha"))
    expect(result.current.totalRows).toBe(1)
    expect(result.current.pageIndex).toBe(0)
  })

  it("combines search and column filter", () => {
    const { result } = renderHook(() => useTsocTable({ rows, columns, defaultPageSize: 10 }))

    act(() => result.current.setColumnFilter("kind", "a"))
    act(() => result.current.setSearch("beta"))
    expect(result.current.totalRows).toBe(1)
    expect(result.current.pageRows[0]?.name).toBe("Beta")
  })

  it("applies default sort on mount", () => {
    const { result } = renderHook(() =>
      useTsocTable({
        rows,
        columns,
        defaultPageSize: 10,
        defaultSortColumnId: "score",
        defaultSortDirection: "desc",
      })
    )

    expect(result.current.sortColumnId).toBe("score")
    expect(result.current.sortDirection).toBe("desc")
    expect(result.current.pageRows.map((r) => r.score)).toEqual([30, 20, 10, 5])
  })

  it("exposes sortedRows separate from filteredRows", () => {
    const { result } = renderHook(() => useTsocTable({ rows, columns, defaultPageSize: 10 }))

    act(() => result.current.toggleSort("name"))
    expect(result.current.sortedRows[0]?.name).toBe("Alpha")
    expect(result.current.filteredRows[0]?.name).toBe("Zebra")
  })
})
