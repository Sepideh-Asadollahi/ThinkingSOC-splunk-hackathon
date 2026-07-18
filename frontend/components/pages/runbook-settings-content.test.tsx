import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { RunbookSettingsContent } from "./runbook-settings-content"

const backendFetch = vi.fn()
const fetchRunbookRuntimeStatus = vi.fn()

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  backendFetch: (...args: unknown[]) => backendFetch(...args),
}))

vi.mock("@/lib/api/investigation-workflow", () => ({
  fetchRunbookRuntimeStatus: (...args: unknown[]) => fetchRunbookRuntimeStatus(...args),
}))

const settingRows = [
  { id: "tsoc_runbook_enabled", category: "runbook", key: "TSOC_RUNBOOK_ENABLED", value: "true", builtin: true },
  { id: "tsoc_runbook_autopilot_enabled", category: "runbook", key: "TSOC_RUNBOOK_AUTOPILOT_ENABLED", value: "true", builtin: true },
  { id: "tsoc_runbook_max_steps", category: "runbook", key: "TSOC_RUNBOOK_MAX_STEPS", value: "3", builtin: true },
  { id: "tsoc_runbook_default_manual_minutes", category: "runbook", key: "TSOC_RUNBOOK_DEFAULT_MANUAL_MINUTES", value: "25", builtin: true },
  { id: "tsoc_runbook_artifact_scan_limit", category: "runbook", key: "TSOC_RUNBOOK_ARTIFACT_SCAN_LIMIT", value: "500", builtin: true },
]

const runtimeStatus = {
  enabled: true,
  autopilot_enabled: true,
  ready: true,
  configured_model: "openai/gpt-5.6",
  max_steps: 3,
  default_manual_minutes: 25,
  artifact_scan_limit: 500,
  postgres_configured: true,
  llm_configured: true,
  splunk_configured: true,
  mcp_configured: false,
  rest_api_configured: true,
  execution_transport_policy: "mcp_then_rest",
  execution_enabled: true,
  acknowledgment_required: true,
  exact_search_name_required: true,
  source_evidence_required: true,
}

describe("RunbookSettingsContent", () => {
  beforeEach(() => {
    backendFetch.mockReset()
    fetchRunbookRuntimeStatus.mockReset()
    backendFetch.mockImplementation((path: string) => {
      if (path === "/integrations/settings") return Promise.resolve(settingRows)
      return Promise.resolve({})
    })
    fetchRunbookRuntimeStatus.mockResolvedValue(runtimeStatus)
  })

  it("shows runtime readiness, editable settings, and fixed trust policy", async () => {
    render(<RunbookSettingsContent />)

    expect(await screen.findByRole("heading", { name: "ThinkingSOC Lite" })).toBeInTheDocument()
    expect(await screen.findByText("PostgreSQL configured")).toBeInTheDocument()
    expect(screen.getByText("REST API fallback ready")).toBeInTheDocument()
    expect(screen.getByLabelText("Maximum steps")).toHaveValue(3)
    expect(screen.getByText("Enable Runbook Autopilot Agents")).toBeInTheDocument()
    expect(screen.getByText("Exact detection match")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /save changes/i })).toBeDisabled()
  })

  it("persists all operational settings after a validated change", async () => {
    render(<RunbookSettingsContent />)
    const baseline = await screen.findByLabelText("Default manual baseline")
    fireEvent.change(baseline, { target: { value: "30" } })
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }))

    await waitFor(() => {
      expect(backendFetch).toHaveBeenCalledWith(
        "/integrations/settings/tsoc_runbook_default_manual_minutes",
        expect.objectContaining({ method: "PATCH", body: JSON.stringify({ value: "30" }) })
      )
    })
    expect(await screen.findByText(/settings saved and applied/i)).toBeInTheDocument()
  })

  it("rejects values outside the documented step limit before calling PATCH", async () => {
    render(<RunbookSettingsContent />)
    fireEvent.change(await screen.findByLabelText("Maximum steps"), { target: { value: "4" } })
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }))

    expect(await screen.findByText(/between 1 and 3/i)).toBeInTheDocument()
    expect(backendFetch.mock.calls.some((call) => call[1]?.method === "PATCH")).toBe(false)
  })
})
