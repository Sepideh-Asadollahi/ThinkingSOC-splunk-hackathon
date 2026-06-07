import { fireEvent, render, screen, within } from "@testing-library/react"
import { act } from "react"
import { describe, expect, it, vi } from "vitest"

import { TsocDataTable } from "./tsoc-data-table"

type Row = { id: string; name: string; kind: string; createdAt?: string }

const columns = [
  {
    id: "name",
    header: "Name",
    cell: (row: Row) => row.name,
    sortable: true,
    sortValue: (row: Row) => row.name,
    searchValue: (row: Row) => row.name,
  },
  {
    id: "kind",
    header: "Kind",
    cell: (row: Row) => row.kind,
    sortable: true,
    sortValue: (row: Row) => row.kind,
    filterable: true,
    filterLabel: "Kind",
    filterOptions: [
      { label: "A", value: "a" },
      { label: "B", value: "b" },
    ],
    filterValue: (row: Row) => row.kind,
  },
]

const sampleRows: Row[] = [
  { id: "1", name: "Zebra", kind: "a" },
  { id: "2", name: "Alpha", kind: "b" },
  { id: "3", name: "Beta", kind: "a" },
  { id: "4", name: "Gamma", kind: "b" },
]

describe("TsocDataTable", () => {
  it("renders column headers and row cells", () => {
    render(
      <TsocDataTable
        columns={columns}
        rows={sampleRows}
        getRowKey={(row) => row.id}
        enablePagination={false}
      />
    )
    expect(screen.getByText("Name")).toBeInTheDocument()
    expect(screen.getByText("Zebra")).toBeInTheDocument()
    expect(screen.getByText("Gamma")).toBeInTheDocument()
  })

  it("shows empty message when there are no rows", () => {
    render(
      <TsocDataTable
        columns={columns}
        rows={[]}
        getRowKey={(row) => row.id}
        emptyMessage="Nothing here"
        enablePagination={false}
      />
    )
    expect(screen.getByText("Nothing here")).toBeInTheDocument()
  })

  it("shows initial loading block when loading with no rows (ui-standard)", () => {
    render(
      <TsocDataTable
        columns={columns}
        rows={[]}
        getRowKey={(row) => row.id}
        loading
        loadingMessage="Loading items…"
        enablePagination={false}
      />
    )
    const msg = screen.getByText("Loading items…")
    expect(msg).toBeInTheDocument()
    expect(msg.className).toContain("font-mono")
    expect(msg.className).toContain("text-slate-400")
  })

  it("shows loading row inside table when refreshing existing data", () => {
    render(
      <TsocDataTable
        columns={columns}
        rows={sampleRows}
        getRowKey={(row) => row.id}
        loading
        loadingMessage="Refreshing…"
        enablePagination={false}
      />
    )
    expect(screen.getByText("Refreshing…")).toBeInTheDocument()
    expect(screen.queryByText("Zebra")).not.toBeInTheDocument()
  })

  it("filters rows via search input", () => {
    const { container } = render(
      <TsocDataTable
        columns={columns}
        rows={sampleRows}
        getRowKey={(row) => row.id}
        enablePagination={false}
      />
    )
    const root = within(container)
    fireEvent.change(root.getByLabelText("Search table"), { target: { value: "zebra" } })
    expect(root.getByText("Zebra")).toBeInTheDocument()
    expect(root.queryByText("Alpha")).not.toBeInTheDocument()
  })

  it("sorts rows when clicking sortable header (asc then desc)", () => {
    const { container } = render(
      <TsocDataTable
        columns={columns}
        rows={sampleRows}
        getRowKey={(row) => row.id}
        enablePagination={false}
      />
    )
    const root = within(container)

    const sortBtn = root.getByRole("button", { name: /^Name$/i })
    act(() => {
      fireEvent.click(sortBtn)
    })
    let bodyRows = root.getAllByRole("row").slice(1)
    expect(within(bodyRows[0]).getByText("Alpha")).toBeInTheDocument()

    act(() => {
      fireEvent.click(sortBtn)
    })
    bodyRows = root.getAllByRole("row").slice(1)
    expect(within(bodyRows[0]).getByText("Zebra")).toBeInTheDocument()
  })

  it("shows pagination summary and navigates pages", () => {
    const { container } = render(
      <TsocDataTable
        columns={columns}
        rows={sampleRows}
        getRowKey={(row) => row.id}
        defaultPageSize={2}
      />
    )
    const root = within(container)
    expect(root.getByText(/Showing 1–2 of 4/)).toBeInTheDocument()
    expect(root.getByText(/Page 1 of 2/)).toBeInTheDocument()
    expect(root.getByText("Zebra")).toBeInTheDocument()
    expect(root.queryByText("Beta")).not.toBeInTheDocument()

    fireEvent.click(root.getByRole("button", { name: "Next page" }))
    expect(root.getByText(/Showing 3–4 of 4/)).toBeInTheDocument()
    expect(root.getByText("Beta")).toBeInTheDocument()
    expect(root.queryByText("Zebra")).not.toBeInTheDocument()
  })

  it("hides search toolbar when enableSearch and enableFilters are false", () => {
    const { container } = render(
      <TsocDataTable
        columns={columns}
        rows={sampleRows}
        getRowKey={(row) => row.id}
        enableSearch={false}
        enableFilters={false}
        enablePagination={false}
      />
    )
    const root = within(container)
    expect(root.queryByLabelText("Search table")).not.toBeInTheDocument()
    expect(root.queryByText("Type to filter rows")).not.toBeInTheDocument()
  })

  it("hides pagination footer when enablePagination is false", () => {
    const { container } = render(
      <TsocDataTable
        columns={columns}
        rows={sampleRows}
        getRowKey={(row) => row.id}
        enablePagination={false}
      />
    )
    expect(within(container).queryByText(/Rows per page/)).not.toBeInTheDocument()
  })

  it("invokes onRowClick when a row is clicked", () => {
    const onRowClick = vi.fn()
    const { container } = render(
      <TsocDataTable
        columns={columns}
        rows={sampleRows}
        getRowKey={(row) => row.id}
        enablePagination={false}
        onRowClick={onRowClick}
      />
    )
    fireEvent.click(within(container).getByText("Alpha"))
    expect(onRowClick).toHaveBeenCalledWith(sampleRows[1])
  })

  it("marks selected row with data-state=selected", () => {
    const { container } = render(
      <TsocDataTable
        columns={columns}
        rows={sampleRows}
        getRowKey={(row) => row.id}
        enablePagination={false}
        selectedRowKey="2"
      />
    )
    const selected = container.querySelector('tr[data-state="selected"]')
    expect(selected).toBeTruthy()
    expect(selected?.textContent).toContain("Alpha")
  })

  it("applies table container classes from ui-standard", () => {
    const { container } = render(
      <TsocDataTable
        columns={columns}
        rows={sampleRows}
        getRowKey={(row) => row.id}
        enablePagination={false}
      />
    )
    const root = container.firstElementChild as HTMLElement
    expect(root.className).toContain("rounded-xl")
    expect(root.className).toContain("border-white/10")
    expect(root.className).toContain("bg-black/10")
  })

  it("filters rows by time filter when enabled", () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date("2026-05-18T12:00:00.000Z"))

    const timedRows: Row[] = [
      { id: "1", name: "Recent", kind: "a", createdAt: "2026-05-18T11:30:00.000Z" },
      { id: "2", name: "Old", kind: "a", createdAt: "2026-05-17T10:00:00.000Z" },
    ]

    const { container } = render(
      <TsocDataTable
        columns={columns}
        rows={timedRows}
        getRowKey={(row) => row.id}
        enablePagination={false}
        enableTimeFilter
        getRowTime={(row) => row.createdAt}
      />
    )
    const root = within(container)

    fireEvent.click(root.getByLabelText("Time filter"))
    fireEvent.click(screen.getByRole("option", { name: "Last 1 hour" }))

    expect(root.getByText("Recent")).toBeInTheDocument()
    expect(root.queryByText("Old")).not.toBeInTheDocument()

    vi.useRealTimers()
  })

  it("uses sort header button with header-sort-btn class", () => {
    const { container } = render(
      <TsocDataTable
        columns={columns}
        rows={sampleRows}
        getRowKey={(row) => row.id}
        enablePagination={false}
      />
    )
    const sortBtn = within(container).getByRole("button", { name: /^Name$/i })
    expect(sortBtn.className).toContain("header-sort-btn")
  })
})
