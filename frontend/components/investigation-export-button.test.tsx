import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi, beforeEach } from "vitest"

import { InvestigationExportButton } from "./investigation-export-button"
import type { StoredEventRecord } from "@/lib/api/types"

const sampleEvent: StoredEventRecord = {
  id: 99,
  sid: "sid-export",
  search_name: "Demo alert",
  payload: { security_result: { summary: "test" } },
}

const downloadInvestigationExport = vi.fn()

vi.mock("@/lib/investigation-export", () => ({
  downloadInvestigationExport: (...args: unknown[]) => downloadInvestigationExport(...args),
}))

describe("InvestigationExportButton", () => {
  beforeEach(() => {
    downloadInvestigationExport.mockClear()
  })

  it("renders a visible Export control", () => {
    render(
      <InvestigationExportButton event={sampleEvent} track="security" accent="orange" />
    )
    const button = screen.getByTestId("investigation-export-button")
    expect(button).toBeInTheDocument()
    expect(button).toBeVisible()
    expect(button).toHaveTextContent("Export")
    expect(button).toHaveAttribute("aria-label", "Export investigation")
    expect(button).not.toBeDisabled()
  })

  it("is disabled when event is missing or parent disables it", () => {
    const { rerender } = render(
      <InvestigationExportButton event={null} track="security" accent="orange" />
    )
    expect(screen.getByTestId("investigation-export-button")).toBeDisabled()

    rerender(
      <InvestigationExportButton
        event={sampleEvent}
        track="security"
        accent="orange"
        disabled
      />
    )
    expect(screen.getByTestId("investigation-export-button")).toBeDisabled()
  })

  it("triggers export on click when enabled", () => {
    render(
      <InvestigationExportButton event={sampleEvent} track="observability" accent="teal" />
    )
    fireEvent.click(screen.getByRole("button", { name: /export investigation/i }))
    expect(downloadInvestigationExport).toHaveBeenCalledWith(sampleEvent, "observability")
  })
})
