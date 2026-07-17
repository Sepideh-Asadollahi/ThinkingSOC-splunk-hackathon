import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest"

import { RunbookLibraryContent } from "./runbook-library-content"

const fetchRunbookLibrary = vi.fn()
const exportRunbooks = vi.fn()
const importRunbooks = vi.fn()
const reviseRunbook = vi.fn()

beforeAll(() => {
  Object.defineProperties(Element.prototype, {
    hasPointerCapture: { configurable: true, value: () => false },
    setPointerCapture: { configurable: true, value: () => undefined },
    releasePointerCapture: { configurable: true, value: () => undefined },
    scrollIntoView: { configurable: true, value: () => undefined },
  })
})

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
}))

vi.mock("@/lib/api/investigation-workflow", () => ({
  fetchRunbookLibrary: (...args: unknown[]) => fetchRunbookLibrary(...args),
  exportRunbooks: (...args: unknown[]) => exportRunbooks(...args),
  importRunbooks: (...args: unknown[]) => importRunbooks(...args),
  reviseRunbook: (...args: unknown[]) => reviseRunbook(...args),
}))

function draft(id: string, revision: number) {
  return {
    runbook_id: id,
    source_record_id: 10,
    title: `Login checks r${revision}`,
    summary: "**5. Generating command**  \n\n- The query starts with the `search` command and passes events to `stats`.",
    applicable_search_name: "Suspicious Login",
    source_verdict: "TRUE_POSITIVE",
    steps: [{
      step_id: "step-1",
      title: "Correlate authentication",
      intent: "Inspect identity activity",
      expected_evidence: "Authentication rows",
      stop_condition: "Stop when telemetry is missing",
    }],
    decision_rule: "Escalate on corroboration",
    limitations: [],
    source_results: [],
    status: revision === 2 ? "SOURCE_VERIFIED" : "FAILED",
    configured_model: null,
    model: "manual-editor",
    prompt_tokens: null,
    completion_tokens: null,
    generation_duration_ms: 0,
    verification_duration_ms: 0,
    compile_duration_ms: 1,
    parser_valid_step_count: 0,
    successful_step_count: 0,
    total_evidence_rows: 0,
    revision,
    parent_runbook_id: revision === 2 ? "rb-1" : null,
    origin: revision === 2 ? "edited" : "compiled",
    revision_note: null,
    edited_by: null,
    imported_from_runbook_id: null,
    created_at: "2026-07-14T10:00:00Z",
  }
}

function twoAlertLibrary() {
  const alpha = { ...draft("alpha-r1", 1), applicable_search_name: "Alpha Alert", created_at: "2026-07-15T12:00:00Z" }
  const zeta = { ...draft("zeta-r1", 1), applicable_search_name: "Zeta Alert", created_at: "2026-07-14T12:00:00Z" }
  return {
    count: 2,
    alert_count: 2,
    groups: [
      { alert_name: "Zeta Alert", count: 1, runbooks: [{ draft: zeta, latest_approval: null, latest_run: null, is_latest_for_source: true }] },
      { alert_name: "Alpha Alert", count: 1, runbooks: [{ draft: alpha, latest_approval: null, latest_run: null, is_latest_for_source: true }] },
    ],
  }
}

describe("RunbookLibraryContent", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchRunbookLibrary.mockResolvedValue({
      count: 2,
      alert_count: 1,
      groups: [{
        alert_name: "Suspicious Login",
        count: 2,
        runbooks: [
          { draft: draft("rb-2", 2), latest_approval: null, latest_run: null, is_latest_for_source: true },
          { draft: draft("rb-1", 1), latest_approval: null, latest_run: null, is_latest_for_source: false },
        ],
      }],
    })
  })

  it("shows every revision grouped under the exact Alert Name", async () => {
    render(<RunbookLibraryContent />)

    expect(await screen.findByRole("heading", { name: "Suspicious Login" })).toBeInTheDocument()
    expect(screen.getByText("Login checks r1")).toBeInTheDocument()
    expect(screen.getByText("Login checks r2")).toBeInTheDocument()
    expect(screen.getByText(/2 stored revisions/)).toBeInTheDocument()
  })

  it("opens the complete immutable revision editor", async () => {
    render(<RunbookLibraryContent />)
    await screen.findByText("Login checks r2")
    fireEvent.click(screen.getAllByRole("button", { name: /edit/i })[0])

    expect(await screen.findByText("Create a new runbook revision")).toBeInTheDocument()
    expect(screen.getByDisplayValue("Suspicious Login")).toBeInTheDocument()
    expect(screen.getByText(/approval never carries/i)).toBeInTheDocument()
    expect(screen.getByRole("dialog").querySelector(".overflow-y-auto")).not.toBeNull()
  })

  it("shows an incomplete historical verification as a warning instead of a failure", async () => {
    render(<RunbookLibraryContent />)
    await screen.findByText("Login checks r1")

    expect(screen.getByText("VERIFICATION INCOMPLETE")).toHaveClass("text-amber-300")
    expect(screen.getByText("SUPERSEDED")).toBeInTheDocument()
    expect(screen.queryByText("FAILED")).not.toBeInTheDocument()

    fireEvent.click(screen.getAllByRole("button", { name: /view details/i })[1])
    const dialog = await screen.findByRole("dialog")
    expect(within(dialog).getByText("Verification produced 0 of 1 required step results.")).toBeInTheDocument()
  })

  it("opens a scrollable detail modal for every runbook revision", async () => {
    render(<RunbookLibraryContent />)
    await screen.findByText("Login checks r2")

    const viewButtons = screen.getAllByRole("button", { name: /view details/i })
    expect(viewButtons).toHaveLength(2)
    fireEvent.click(viewButtons[0])

    const dialog = await screen.findByRole("dialog")
    expect(within(dialog).getByText("Decision rule")).toBeInTheDocument()
    expect(within(dialog).getByText("Steps and source evidence")).toBeInTheDocument()
    expect(within(dialog).getByText("Escalate on corroboration")).toBeInTheDocument()
    expect(within(dialog).getByText("5. Generating command").tagName).toBe("STRONG")
    expect(within(dialog).getByText(/The query starts with the/).closest("li")).not.toBeNull()
    expect(dialog.querySelector(".overflow-y-auto")).not.toBeNull()
    expect(within(dialog).getAllByRole("button", { name: "Close" }).length).toBeGreaterThan(0)
  })

  it("filters groups by Alert Name", async () => {
    render(<RunbookLibraryContent />)
    await screen.findByRole("heading", { name: "Suspicious Login" })
    fireEvent.change(screen.getByLabelText("Filter by Alert Name"), {
      target: { value: "endpoint malware" },
    })
    await waitFor(() => {
      expect(screen.getByText("No runbooks match this Alert Name.")).toBeInTheDocument()
    })
  })

  it("sorts alert groups and keeps revision cards on a neutral black background", async () => {
    const user = userEvent.setup()
    fetchRunbookLibrary.mockResolvedValueOnce(twoAlertLibrary())
    render(<RunbookLibraryContent />)

    await screen.findByRole("heading", { name: "Alpha Alert" })
    expect(screen.getAllByRole("heading", { level: 2 }).map((heading) => heading.textContent)).toEqual([
      "Alpha Alert",
      "Zeta Alert",
    ])

    await user.click(screen.getByRole("combobox", { name: "Sort runbooks" }))
    await user.click(screen.getByRole("option", { name: "Alert Name Z–A" }))
    expect(screen.getAllByRole("heading", { level: 2 }).map((heading) => heading.textContent)).toEqual([
      "Zeta Alert",
      "Alpha Alert",
    ])
    expect(screen.getAllByTestId("runbook-revision-card")[0]).toHaveClass("bg-black/60")
    expect(screen.getByTestId("runbook-library-page")).toHaveClass("bg-black")
  })

  it("lists every Alert Name and filters to the exact selected alert", async () => {
    const user = userEvent.setup()
    fetchRunbookLibrary.mockResolvedValueOnce(twoAlertLibrary())
    render(<RunbookLibraryContent />)

    await screen.findByRole("heading", { name: "Alpha Alert" })
    const selector = screen.getByRole("combobox", { name: "Select Alert Name" })
    await user.click(selector)
    expect(screen.getByRole("option", { name: "All Alert Names (2)" })).toBeInTheDocument()
    expect(screen.getByRole("option", { name: "Alpha Alert (1 revision)" })).toBeInTheDocument()
    const zetaOption = screen.getByRole("option", { name: "Zeta Alert (1 revision)" })
    expect(zetaOption).toBeInTheDocument()

    await user.click(zetaOption)
    expect(screen.getByRole("heading", { name: "Zeta Alert" })).toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: "Alpha Alert" })).not.toBeInTheDocument()
  })
})
