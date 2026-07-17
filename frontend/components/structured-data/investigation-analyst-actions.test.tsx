import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { InvestigationAnalystActions } from "./investigation-analyst-actions"

const fetchAnalystActions = vi.fn()
const postAnalystAction = vi.fn()

vi.mock("@/lib/api/investigation-workflow", () => ({
  fetchAnalystActions: (...args: unknown[]) => fetchAnalystActions(...args),
  postAnalystAction: (...args: unknown[]) => postAnalystAction(...args),
}))

describe("InvestigationAnalystActions", () => {
  beforeEach(() => {
    fetchAnalystActions.mockReset()
    postAnalystAction.mockReset()
  })

  it("shows latest acknowledge decision", async () => {
    fetchAnalystActions.mockResolvedValueOnce({
      record_id: 5,
      count: 1,
      results: [
        {
          id: 1,
          created_at: "2026-05-22T10:00:00Z",
          action: "acknowledge",
          note: "False positive",
          recommended_step: "Close ticket",
          investigation_record_id: 5,
        },
      ],
    })

    render(<InvestigationAnalystActions recordId="5" />)

    expect(await screen.findByText("Acknowledged")).toBeInTheDocument()
    expect(screen.getByText("False positive")).toBeInTheDocument()
    expect(screen.getByText(/Close ticket/)).toBeInTheDocument()
  })

  it("posts acknowledge and refreshes latest", async () => {
    fetchAnalystActions
      .mockResolvedValueOnce({ record_id: 5, count: 0, results: [] })
      .mockResolvedValueOnce({
        record_id: 5,
        count: 1,
        results: [
          {
            id: 2,
            created_at: "2026-05-22T11:00:00Z",
            action: "acknowledge",
            note: "Reviewed",
            recommended_step: null,
            investigation_record_id: 5,
          },
        ],
      })
    postAnalystAction.mockResolvedValueOnce({
      record_id: 5,
      saved: { ok: true },
      latest: {
        id: 2,
        action: "acknowledge",
        note: "Reviewed",
        created_at: "2026-05-22T11:00:00Z",
      },
      results: [],
    })

    const onRecorded = vi.fn()
    render(<InvestigationAnalystActions recordId="5" onActionRecorded={onRecorded} />)

    await waitFor(() => expect(screen.getByRole("button", { name: /acknowledge/i })).not.toBeDisabled())

    fireEvent.change(screen.getByLabelText(/optional note/i), {
      target: { value: "Reviewed" },
    })
    fireEvent.click(screen.getByRole("button", { name: /acknowledge/i }))

    await waitFor(() => {
      expect(postAnalystAction).toHaveBeenCalledWith("5", {
        action: "acknowledge",
        note: "Reviewed",
      })
    })
    expect(onRecorded).toHaveBeenCalledWith("acknowledge")
    expect(await screen.findByText("Acknowledged")).toBeInTheDocument()
  })

  it("posts escalate", async () => {
    fetchAnalystActions.mockResolvedValue({ record_id: 7, count: 0, results: [] })
    postAnalystAction.mockResolvedValueOnce({
      record_id: 7,
      saved: { ok: true },
      latest: {
        id: 3,
        action: "escalate",
        note: null,
        created_at: "2026-05-22T12:00:00Z",
      },
      results: [],
    })

    render(<InvestigationAnalystActions recordId="7" />)
    await waitFor(() => expect(screen.getByRole("button", { name: /escalate/i })).not.toBeDisabled())

    fireEvent.click(screen.getByRole("button", { name: /escalate/i }))

    await waitFor(() => {
      expect(postAnalystAction).toHaveBeenCalledWith("7", { action: "escalate", note: undefined })
    })
    expect(await screen.findByText("Escalated")).toBeInTheDocument()
  })
})
