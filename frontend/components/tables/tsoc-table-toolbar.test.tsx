import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import type { TsocColumn } from "./tsoc-data-table"
import { TsocTableToolbar } from "./tsoc-table-toolbar"

type Row = { id: string; name: string; kind: string }

const columns: TsocColumn<Row>[] = [
  {
    id: "name",
    header: "Name",
    cell: (r) => r.name,
    filterable: true,
    filterLabel: "Kind filter",
    filterOptions: [{ label: "A", value: "a" }],
    filterValue: (r) => r.kind,
  },
]

describe("TsocTableToolbar", () => {
  it("renders search input and calls onSearchChange", () => {
    const onSearchChange = vi.fn()
    render(
      <TsocTableToolbar
        search=""
        onSearchChange={onSearchChange}
        searchPlaceholder="Find rows…"
        columns={[]}
        getColumnFilterValue={() => "__all__"}
        onColumnFilterChange={vi.fn()}
      />
    )

    const input = screen.getByLabelText("Search table")
    expect(input).toHaveAttribute("placeholder", "Find rows…")
    fireEvent.change(input, { target: { value: "hello" } })
    expect(onSearchChange).toHaveBeenCalledWith("hello")
  })

  it("renders filter controls for filterable columns", () => {
    render(
      <TsocTableToolbar
        search=""
        onSearchChange={vi.fn()}
        columns={columns}
        getColumnFilterValue={() => "__all__"}
        onColumnFilterChange={vi.fn()}
      />
    )
    expect(screen.getByText("Kind filter")).toBeInTheDocument()
  })

  it("uses ui-standard toolbar border and padding classes", () => {
    const { container } = render(
      <TsocTableToolbar
        search=""
        onSearchChange={vi.fn()}
        columns={[]}
        getColumnFilterValue={() => "__all__"}
        onColumnFilterChange={vi.fn()}
      />
    )
    const toolbar = container.firstElementChild as HTMLElement
    expect(toolbar.className).toContain("border-b")
    expect(toolbar.className).toContain("border-white/5")
    expect(toolbar.className).toContain("px-6")
    expect(toolbar.className).toContain("py-4")
  })
})
