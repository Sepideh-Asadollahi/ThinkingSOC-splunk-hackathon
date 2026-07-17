import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import {
  buildVerifiedRunbook,
  buildSafeResponsePreview,
  decideSafeResponsePreview,
  decideVerifiedRunbook,
  fetchAnalystActions,
  fetchCompatibleRunbookTargets,
  fetchInvestigationTimeline,
  fetchInvestigationWorkflowForExport,
  fetchRunbookLibrary,
  fetchRunbookEvaluation,
  fetchRunbookAutopilot,
  fetchRunbookRuntimeStatus,
  fetchVerifiedRunbook,
  postAnalystAction,
  exportRunbooks,
  importRunbooks,
  reviseRunbook,
  runVerifiedRunbook,
  runShadowReplay,
  runRunbookAutopilot,
} from "@/lib/api/investigation-workflow"

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

describe("investigation-workflow API", () => {
  beforeEach(() => {
    backendFetch.mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it("fetchInvestigationTimeline calls correct path", async () => {
    backendFetch.mockResolvedValueOnce({
      record_id: 10,
      found: true,
      sid: "sid-1",
      steps: [],
    })
    const data = await fetchInvestigationTimeline(10)
    expect(backendFetch).toHaveBeenCalledWith("/investigation/records/10/timeline")
    expect(data.sid).toBe("sid-1")
  })

  it("fetchAnalystActions calls correct path", async () => {
    backendFetch.mockResolvedValueOnce({
      record_id: 5,
      count: 0,
      results: [],
    })
    await fetchAnalystActions("5")
    expect(backendFetch).toHaveBeenCalledWith("/investigation/records/5/analyst-actions")
  })

  it("postAnalystAction sends JSON body", async () => {
    backendFetch.mockResolvedValueOnce({
      record_id: 5,
      saved: { ok: true },
      latest: { action: "acknowledge" },
      results: [{ action: "acknowledge" }],
    })
    const res = await postAnalystAction(5, { action: "acknowledge", note: "LGTM" })
    expect(backendFetch).toHaveBeenCalledWith(
      "/investigation/records/5/analyst-actions",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ action: "acknowledge", note: "LGTM" }),
      })
    )
    expect(res.latest?.action).toBe("acknowledge")
  })

  it("postAnalystAction supports escalate", async () => {
    backendFetch.mockResolvedValueOnce({
      record_id: 7,
      saved: { ok: true },
      latest: { action: "escalate" },
      results: [],
    })
    await postAnalystAction("7", { action: "escalate" })
    const call = backendFetch.mock.calls[0]
    expect(call[1]).toMatchObject({ method: "POST" })
    expect(JSON.parse(String(call[1]?.body))).toEqual({ action: "escalate" })
  })

  it("fetchVerifiedRunbook loads latest state", async () => {
    backendFetch.mockResolvedValueOnce({ record_id: 5, draft: null })
    await fetchVerifiedRunbook(5)
    expect(backendFetch).toHaveBeenCalledWith("/investigation/records/5/runbook")
  })

  it("loads the latest Runbook Autopilot trace", async () => {
    backendFetch.mockResolvedValueOnce({ record_id: 5, latest_session: null })
    await fetchRunbookAutopilot(5)
    expect(backendFetch).toHaveBeenCalledWith(
      "/investigation/records/5/runbook/autopilot"
    )
  })

  it("runs bounded Runbook Autopilot with an objective", async () => {
    backendFetch.mockResolvedValueOnce({ session_id: "autopilot-1" })
    const body = {
      objective: "Assess and advance safely.",
      mode: "ADVANCE" as const,
      generate_response_preview: true,
    }
    await runRunbookAutopilot(5, body)
    expect(backendFetch).toHaveBeenCalledWith(
      "/investigation/records/5/runbook/autopilot",
      { method: "POST", body: JSON.stringify(body) }
    )
  })

  it("fetchRunbookRuntimeStatus loads non-secret policy readiness", async () => {
    backendFetch.mockResolvedValueOnce({ enabled: true, ready: true })
    await fetchRunbookRuntimeStatus()
    expect(backendFetch).toHaveBeenCalledWith("/investigation/runbook-settings")
  })

  it("loads bounded compatible reuse targets", async () => {
    backendFetch.mockResolvedValueOnce({ results: [] })
    await fetchCompatibleRunbookTargets(42, 8)
    expect(backendFetch).toHaveBeenCalledWith(
      "/investigation/records/42/runbook/compatible-targets?limit=8"
    )
  })

  it("buildVerifiedRunbook posts an empty request", async () => {
    backendFetch.mockResolvedValueOnce({ runbook_id: "rb-1" })
    await buildVerifiedRunbook("5")
    expect(backendFetch).toHaveBeenCalledWith(
      "/investigation/records/5/runbook",
      { method: "POST" }
    )
  })

  it("buildVerifiedRunbook supports idempotent create-if-missing", async () => {
    backendFetch.mockResolvedValueOnce({ runbook_id: "rb-1" })
    await buildVerifiedRunbook("5", { rebuild: false })
    expect(backendFetch).toHaveBeenCalledWith(
      "/investigation/records/5/runbook?rebuild=false",
      { method: "POST" }
    )
  })

  it("decideVerifiedRunbook sends approval", async () => {
    backendFetch.mockResolvedValueOnce({ decision: "approve" })
    const body = { runbook_id: "rb-1", decision: "approve" as const, note: "Reviewed" }
    await decideVerifiedRunbook(5, body)
    expect(backendFetch).toHaveBeenCalledWith(
      "/investigation/records/5/runbook/approval",
      { method: "POST", body: JSON.stringify(body) }
    )
  })

  it("builds a preview-only response recommendation", async () => {
    backendFetch.mockResolvedValueOnce({ preview_id: "preview-1", execution_supported: false })
    const body = { runbook_id: "rb-1" }
    await buildSafeResponsePreview(5, body)
    expect(backendFetch).toHaveBeenCalledWith(
      "/investigation/records/5/runbook/response-preview",
      { method: "POST", body: JSON.stringify(body) }
    )
  })

  it("records response approval for manual action only", async () => {
    backendFetch.mockResolvedValueOnce({ automatic_execution_performed: false })
    const body = {
      preview_id: "preview-1",
      decision: "approve_for_manual_action" as const,
      note: "Evidence and rollback reviewed",
    }
    await decideSafeResponsePreview(5, body)
    expect(backendFetch).toHaveBeenCalledWith(
      "/investigation/records/5/runbook/response-preview/decision",
      { method: "POST", body: JSON.stringify(body) }
    )
  })

  it("runVerifiedRunbook targets the selected record", async () => {
    backendFetch.mockResolvedValueOnce({ status: "REUSED" })
    const body = {
      source_record_id: 5,
      runbook_id: "rb-1",
      estimated_manual_minutes: 25,
    }
    await runVerifiedRunbook(8, body)
    expect(backendFetch).toHaveBeenCalledWith(
      "/investigation/records/8/runbook-runs",
      { method: "POST", body: JSON.stringify(body) }
    )
  })

  it("runShadowReplay targets a historical record without approval input", async () => {
    backendFetch.mockResolvedValueOnce({ status: "NO_EVIDENCE" })
    const body = {
      source_record_id: 5,
      runbook_id: "rb-1",
      estimated_manual_minutes: 25,
    }
    await runShadowReplay(9, body)
    expect(backendFetch).toHaveBeenCalledWith(
      "/investigation/records/9/runbook-shadow-runs",
      { method: "POST", body: JSON.stringify(body) }
    )
  })

  it("loads measured runbook evaluation metrics", async () => {
    backendFetch.mockResolvedValueOnce({ revision_count: 2, shadow_run_count: 1 })
    await fetchRunbookEvaluation()
    expect(backendFetch).toHaveBeenCalledWith("/investigation/runbook-evaluations")
  })

  it("loads the grouped runbook library", async () => {
    backendFetch.mockResolvedValueOnce({ count: 0, alert_count: 0, groups: [] })
    await fetchRunbookLibrary()
    expect(backendFetch).toHaveBeenCalledWith("/investigation/runbooks")
  })

  it("exports one runbook with a URL-safe filter", async () => {
    backendFetch.mockResolvedValueOnce({ runbooks: [] })
    await exportRunbooks({ runbookId: "rb /1" })
    expect(backendFetch).toHaveBeenCalledWith(
      "/investigation/runbooks/export?runbook_id=rb+%2F1"
    )
  })

  it("imports a portable document", async () => {
    const document = {
      schema_version: "thinking-soc.runbook-library/v1" as const,
      exported_at: "2026-07-14T10:00:00Z",
      runbooks: [],
    }
    backendFetch.mockResolvedValueOnce({ imported_count: 0, runbooks: [] })
    await importRunbooks({ document })
    expect(backendFetch).toHaveBeenCalledWith("/investigation/runbooks/import", {
      method: "POST",
      body: JSON.stringify({ document }),
    })
  })

  it("saves edits as a new revision", async () => {
    backendFetch.mockResolvedValueOnce({ runbook_id: "rb-2" })
    const body = {
      title: "Title",
      summary: "Summary",
      applicable_search_name: "Alert Name",
      steps: [
        {
          step_id: "step-1",
          title: "Check",
          intent: "Inspect evidence",
          expected_evidence: "Rows",
          stop_condition: "Stop without telemetry",
        },
      ],
      decision_rule: "Escalate on evidence",
      limitations: [],
      verify_on_source: false,
    }
    await reviseRunbook("rb/1", body)
    expect(backendFetch).toHaveBeenCalledWith(
      "/investigation/runbooks/rb%2F1",
      { method: "PATCH", body: JSON.stringify(body) }
    )
  })

  it("exports timeline, analyst actions, and Forge state", async () => {
    backendFetch
      .mockResolvedValueOnce({ record_id: 9, found: true, steps: [] })
      .mockResolvedValueOnce({ record_id: 9, count: 0, results: [] })
      .mockResolvedValueOnce({
        record_id: 9,
        draft: null,
        latest_approval: null,
        latest_run: null,
        latest_response_preview: null,
        latest_response_decision: null,
      })

    const exported = await fetchInvestigationWorkflowForExport(9)

    expect(backendFetch).toHaveBeenCalledTimes(3)
    expect(exported.event_timeline?.record_id).toBe(9)
    expect(exported.analyst_actions?.record_id).toBe(9)
    expect(exported.verified_runbook?.record_id).toBe(9)
    expect(exported.fetch_errors).toEqual([])
  })
})
