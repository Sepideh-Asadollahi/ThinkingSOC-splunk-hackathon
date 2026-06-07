import type { ReactNode } from "react"
import { render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi, beforeEach } from "vitest"

import { InvestigationContent } from "./investigation-content"
import { OpsInvestigationContent } from "./ops-investigation-content"
import type { StoredEventRecord } from "@/lib/api/types"

const securityRecord: StoredEventRecord = {
  id: 42,
  sid: "sid-sec",
  search_name: "Security alert",
  tsoc_record_type: "soc_analysis",
  payload: {
    security_result: {
      summary: "Security summary",
      judge: { verdict: "investigate", recommended_next_step: "Review" },
    },
  },
}

const opsRecord: StoredEventRecord = {
  id: 7,
  sid: "sid-ops",
  search_name: "Ops alert",
  tsoc_record_type: "observability_analysis",
  payload: {
    analysis: {
      summary: "Ops summary",
      ops_judge: { verdict: "degraded" },
    },
  },
}

const useParamsMock = vi.fn(() => ({ id: "42" }))

vi.mock("next/navigation", () => ({
  useParams: () => useParamsMock(),
}))

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}))

const backendFetch = vi.fn()

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status = 500) {
      super(message)
      this.status = status
    }
  },
  backendFetch: (...args: unknown[]) => backendFetch(...args),
}))

vi.mock("@/components/structured-data", () => ({
  StorageEventDetail: () => <div data-testid="storage-event-detail-stub" />,
}))

describe("Investigation pages Export button", () => {
  beforeEach(() => {
    useParamsMock.mockReturnValue({ id: "42" })
    backendFetch.mockReset()
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:mock"),
      revokeObjectURL: vi.fn(),
    })
  })

  it("shows visible Export on Security investigation after load", async () => {
    backendFetch.mockImplementation((path: string) => {
      if (String(path).includes("admin_org_gap_suggest")) {
        return Promise.resolve({ results: [] })
      }
      return Promise.resolve(securityRecord)
    })
    render(<InvestigationContent />)

    const exportBtn = await screen.findByTestId("investigation-export-button")
    expect(exportBtn).toBeVisible()
    expect(exportBtn).toHaveTextContent("Export")
    expect(exportBtn).not.toBeDisabled()
    expect(screen.getByRole("heading", { name: /investigation/i })).toBeInTheDocument()
  })

  it("shows visible Export on Observability investigation after load", async () => {
    useParamsMock.mockReturnValue({ id: "7" })
    backendFetch.mockResolvedValueOnce(opsRecord)
    render(<OpsInvestigationContent />)

    const exportBtn = await screen.findByTestId("investigation-export-button")
    await waitFor(() => expect(exportBtn).not.toBeDisabled())
    expect(exportBtn).toBeVisible()
    expect(screen.getByRole("heading", { name: /ops investigation/i })).toBeInTheDocument()
  })

  it("disables Export while Security investigation is loading", () => {
    backendFetch.mockImplementation(() => new Promise(() => {}))
    render(<InvestigationContent />)
    expect(screen.getByTestId("investigation-export-button")).toBeDisabled()
  })
})
