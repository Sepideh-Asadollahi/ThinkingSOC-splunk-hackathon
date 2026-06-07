import { fireEvent, render, screen, within } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { TsocTablePagination } from "./tsoc-table-pagination"

describe("TsocTablePagination", () => {
  it("shows empty summary when totalRows is zero", () => {
    render(
      <TsocTablePagination
        totalRows={0}
        pageIndex={0}
        pageSize={10}
        onPageIndexChange={vi.fn()}
        onPageSizeChange={vi.fn()}
      />
    )
    expect(screen.getByText("Showing 0 of 0")).toBeInTheDocument()
    expect(screen.getByText("Page 1 of 1")).toBeInTheDocument()
  })

  it("shows range for middle page", () => {
    render(
      <TsocTablePagination
        totalRows={25}
        pageIndex={1}
        pageSize={10}
        onPageIndexChange={vi.fn()}
        onPageSizeChange={vi.fn()}
      />
    )
    expect(screen.getByText("Showing 11–20 of 25")).toBeInTheDocument()
    expect(screen.getByText("Page 2 of 3")).toBeInTheDocument()
  })

  it("calls onPageIndexChange for prev and next", () => {
    const onPageIndexChange = vi.fn()
    const { container } = render(
      <TsocTablePagination
        totalRows={30}
        pageIndex={1}
        pageSize={10}
        onPageIndexChange={onPageIndexChange}
        onPageSizeChange={vi.fn()}
      />
    )

    const root = within(container)
    fireEvent.click(root.getByRole("button", { name: "Previous page" }))
    expect(onPageIndexChange).toHaveBeenCalledWith(0)

    fireEvent.click(root.getByRole("button", { name: "Next page" }))
    expect(onPageIndexChange).toHaveBeenCalledWith(2)
  })

  it("disables prev on first page and next on last page", () => {
    const { container, rerender } = render(
      <TsocTablePagination
        totalRows={15}
        pageIndex={0}
        pageSize={10}
        onPageIndexChange={vi.fn()}
        onPageSizeChange={vi.fn()}
      />
    )
    const root = within(container)
    expect(root.getByRole("button", { name: "Previous page" })).toBeDisabled()
    expect(root.getByRole("button", { name: "Next page" })).not.toBeDisabled()

    rerender(
      <TsocTablePagination
        totalRows={15}
        pageIndex={1}
        pageSize={10}
        onPageIndexChange={vi.fn()}
        onPageSizeChange={vi.fn()}
      />
    )
    expect(root.getByRole("button", { name: "Previous page" })).not.toBeDisabled()
    expect(root.getByRole("button", { name: "Next page" })).toBeDisabled()
  })

  it("uses px-4 sm:px-6 on footer wrapper (ui-standard)", () => {
    const { container } = render(
      <TsocTablePagination
        totalRows={5}
        pageIndex={0}
        pageSize={10}
        onPageIndexChange={vi.fn()}
        onPageSizeChange={vi.fn()}
      />
    )
    const footer = container.firstElementChild as HTMLElement
    expect(footer.className).toContain("px-4")
    expect(footer.className).toContain("sm:px-6")
  })
})
