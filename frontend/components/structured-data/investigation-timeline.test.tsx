import { render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { InvestigationTimeline } from "./investigation-timeline"

const fetchInvestigationTimeline = vi.fn()

vi.mock("@/lib/api/investigation-workflow", () => ({
  fetchInvestigationTimeline: (...args: unknown[]) => fetchInvestigationTimeline(...args),
}))

describe("InvestigationTimeline", () => {
  beforeEach(() => {
    fetchInvestigationTimeline.mockReset()
  })

  it("renders pipeline steps after load", async () => {
    fetchInvestigationTimeline.mockResolvedValueOnce({
      record_id: 10,
      found: true,
      sid: "sid-1",
      steps: [
        {
          record_id: 1,
          record_type: "splunk_ingest",
          title: "Splunk ingest",
          description: "Alert received",
          detail: "Fields: 10.0.0.1",
          created_at: "2026-05-20T10:00:00Z",
          is_current_record: false,
          is_analyst_action: false,
        },
        {
          record_id: 10,
          record_type: "soc_analysis",
          title: "SOC analysis",
          description: "Pipeline completed",
          detail: "Verdict suspicious",
          created_at: "2026-05-20T12:00:00Z",
          is_current_record: true,
          is_analyst_action: false,
        },
      ],
    })

    render(<InvestigationTimeline recordId="10" />)

    expect(await screen.findByText("Splunk ingest")).toBeInTheDocument()
    expect(screen.getByText("SOC analysis")).toBeInTheDocument()
    expect(screen.getByText("Fields: 10.0.0.1")).toBeInTheDocument()
    expect(screen.getByText("Verdict suspicious")).toBeInTheDocument()
    expect(screen.getByText("This record")).toBeInTheDocument()
    expect(fetchInvestigationTimeline).toHaveBeenCalledWith("10")
  })

  it("shows error when timeline fetch fails", async () => {
    fetchInvestigationTimeline.mockRejectedValueOnce(new Error("Service unavailable"))

    render(<InvestigationTimeline recordId="99" />)

    await waitFor(() => {
      expect(screen.getByText("Timeline unavailable")).toBeInTheDocument()
    })
    expect(screen.getByText("Service unavailable")).toBeInTheDocument()
  })

  it("shows step count and Show more when many steps", async () => {
    const manySteps = Array.from({ length: 6 }, (_, i) => ({
      record_id: i + 1,
      record_type: i === 0 ? "splunk_ingest" : "soc_analysis",
      title: `Step ${i + 1}`,
      description: "desc",
      detail: null,
      created_at: `2026-05-20T1${i}:00:00Z`,
      is_current_record: i === 5,
      is_analyst_action: false,
    }))
    fetchInvestigationTimeline.mockResolvedValueOnce({
      record_id: 10,
      found: true,
      sid: "sid-1",
      steps: manySteps,
    })

    render(<InvestigationTimeline recordId="10" />)

    expect(await screen.findByText("6 steps")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /show 2 more/i })).toBeInTheDocument()
    expect(screen.queryByText("Step 6")).not.toBeInTheDocument()

    screen.getByRole("button", { name: /show 2 more/i }).click()
    expect(await screen.findByText("Step 6")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /show less/i })).toBeInTheDocument()
  })

  it("refetches when refreshKey changes", async () => {
    fetchInvestigationTimeline.mockResolvedValue({
      record_id: 10,
      found: true,
      sid: "sid-1",
      steps: [],
    })

    const { rerender } = render(<InvestigationTimeline recordId="10" refreshKey={0} />)
    await waitFor(() => expect(fetchInvestigationTimeline).toHaveBeenCalledTimes(1))

    rerender(<InvestigationTimeline recordId="10" refreshKey={1} />)
    await waitFor(() => expect(fetchInvestigationTimeline).toHaveBeenCalledTimes(2))
  })
})
