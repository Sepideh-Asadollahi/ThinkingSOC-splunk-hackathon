import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { VerifiedRunbookPanel } from "./verified-runbook-panel"

const fetchVerifiedRunbook = vi.fn()
const fetchAnalystActions = vi.fn()
const fetchRunbookRuntimeStatus = vi.fn()
const fetchRunbookAutopilot = vi.fn()
const fetchCompatibleRunbookTargets = vi.fn()
const buildVerifiedRunbook = vi.fn()
const buildSafeResponsePreview = vi.fn()
const decideSafeResponsePreview = vi.fn()
const decideVerifiedRunbook = vi.fn()
const runVerifiedRunbook = vi.fn()
const runRunbookAutopilot = vi.fn()

vi.mock("@/lib/api/investigation-workflow", () => ({
  fetchVerifiedRunbook: (...args: unknown[]) => fetchVerifiedRunbook(...args),
  fetchAnalystActions: (...args: unknown[]) => fetchAnalystActions(...args),
  fetchRunbookRuntimeStatus: (...args: unknown[]) => fetchRunbookRuntimeStatus(...args),
  fetchRunbookAutopilot: (...args: unknown[]) => fetchRunbookAutopilot(...args),
  fetchCompatibleRunbookTargets: (...args: unknown[]) => fetchCompatibleRunbookTargets(...args),
  buildVerifiedRunbook: (...args: unknown[]) => buildVerifiedRunbook(...args),
  buildSafeResponsePreview: (...args: unknown[]) => buildSafeResponsePreview(...args),
  decideSafeResponsePreview: (...args: unknown[]) => decideSafeResponsePreview(...args),
  decideVerifiedRunbook: (...args: unknown[]) => decideVerifiedRunbook(...args),
  runVerifiedRunbook: (...args: unknown[]) => runVerifiedRunbook(...args),
  runRunbookAutopilot: (...args: unknown[]) => runRunbookAutopilot(...args),
}))

const result = {
  question: "Correlate authentication activity",
  spl: "index=auth | stats count by user, src",
  explanation: "**5. Generating command**  \n\n- The query starts with the `search` command.",
  time_window: "earliest=-24h latest=now",
  pivots: ["user", "src"],
  notes: [],
  validation: { method: "splunk_parser", valid: true, message: null },
  spl_results: {
    row_count: 3,
    rows: [{ count: 3 }],
    truncated: false,
    error: null,
    execution_transport: "rest",
  },
}

const sourceVerifiedDraft = {
  runbook_id: "rb-1",
  source_record_id: 5,
  title: "Suspicious login investigation",
  summary: "Correlate authentication evidence",
  applicable_search_name: "Suspicious Login",
  source_verdict: "TRUE_POSITIVE",
  steps: [
    {
      step_id: "step-1",
      title: "Correlate authentication",
      intent: "Find unusual authentication sources",
      expected_evidence: "Authentication events grouped by source",
      stop_condition: "Abstain when identity data is absent",
    },
  ],
  decision_rule: "Escalate on corroboration; otherwise abstain.",
  limitations: ["Requires authentication telemetry"],
  source_results: [result],
  status: "SOURCE_VERIFIED",
  configured_model: "openai/gpt-5.6",
  model: "gpt-5.6-2026-07-01",
  prompt_tokens: 100,
  completion_tokens: 80,
  generation_duration_ms: 400,
  verification_duration_ms: 800,
  compile_duration_ms: 1200,
  parser_valid_step_count: 1,
  successful_step_count: 1,
  total_evidence_rows: 3,
  created_at: "2026-07-14T10:00:00Z",
}

const responsePreview = {
  preview_id: "preview-1",
  runbook_id: "rb-1",
  source_record_id: 5,
  source_verdict: "TRUE_POSITIVE",
  status: "READY_FOR_REVIEW",
  evidence_basis: "SOURCE_EVIDENCE",
  actions: [
    {
      action_id: "action-1",
      action_type: "ISOLATE_ENDPOINT",
      title: "Contain the affected endpoint",
      target_type: "endpoint",
      target: "source-host",
      risk_level: "high",
      rationale: "Verified evidence supports containment review.",
      prerequisites: ["Confirm business owner"],
      expected_effect: "Stop external communication.",
      rollback_plan: "Restore connectivity after eradication.",
      verification_steps: ["Confirm external communication has stopped"],
      requires_human_approval: true,
      execution_mode: "PREVIEW_ONLY",
    },
  ],
  decision_summary: "Review operational impact before manual action.",
  limitations: ["No action has been executed"],
  configured_model: "openai/gpt-5.6",
  model: "openai/gpt-5.6",
  prompt_tokens: 100,
  completion_tokens: 50,
  generation_duration_ms: 500,
  execution_supported: false,
  created_at: "2026-07-15T10:00:00Z",
}

describe("VerifiedRunbookPanel", () => {
  beforeEach(() => {
    fetchVerifiedRunbook.mockReset()
    fetchAnalystActions.mockReset()
    fetchRunbookRuntimeStatus.mockReset()
    fetchRunbookAutopilot.mockReset()
    fetchCompatibleRunbookTargets.mockReset()
    buildVerifiedRunbook.mockReset()
    buildSafeResponsePreview.mockReset()
    decideSafeResponsePreview.mockReset()
    decideVerifiedRunbook.mockReset()
    runVerifiedRunbook.mockReset()
    runRunbookAutopilot.mockReset()
    fetchRunbookAutopilot.mockResolvedValue({ record_id: 5, latest_session: null })
    fetchRunbookRuntimeStatus.mockResolvedValue({
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
    })
    fetchCompatibleRunbookTargets.mockResolvedValue({
      source_record_id: 5,
      search_name: "Suspicious Login",
      count: 0,
      results: [],
    })
  })

  it("requires the latest analyst action to be acknowledge", async () => {
    fetchVerifiedRunbook.mockResolvedValueOnce({
      record_id: 5,
      draft: null,
      latest_approval: null,
      latest_run: null,
    })
    fetchAnalystActions.mockResolvedValueOnce({
      record_id: 5,
      count: 1,
      results: [{ action: "escalate" }],
    })
    render(<VerifiedRunbookPanel recordId="5" />)

    expect(await screen.findByText("Acknowledge this investigation first.")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /build verified runbook/i })).toBeDisabled()
  })

  it("builds and renders honest source verification evidence", async () => {
    fetchVerifiedRunbook.mockResolvedValueOnce({
      record_id: 5,
      draft: null,
      latest_approval: null,
      latest_run: null,
    })
    fetchAnalystActions.mockResolvedValueOnce({
      record_id: 5,
      count: 1,
      results: [{ action: "acknowledge" }],
    })
    buildVerifiedRunbook.mockResolvedValueOnce(sourceVerifiedDraft)
    render(<VerifiedRunbookPanel recordId="5" />)

    fireEvent.click(await screen.findByRole("button", { name: /build verified runbook/i }))

    expect(await screen.findByText("Verified on the source investigation")).toBeInTheDocument()
    expect(screen.getByText(/does not prove universal correctness/i)).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Runbook execution graph" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Human gate: Awaiting review" })).toBeInTheDocument()
    expect(screen.getAllByText("3 evidence row(s)")).toHaveLength(2)
    expect(screen.getByText("Splunk REST")).toBeInTheDocument()
    expect(screen.getByText("index=auth | stats count by user, src")).toBeInTheDocument()
    expect(screen.getByText("5. Generating command").tagName).toBe("STRONG")
    expect(screen.getByText(/The query starts with the/).closest("li")).not.toBeNull()
  })

  it("automatically builds after a newly recorded acknowledge action", async () => {
    fetchVerifiedRunbook.mockResolvedValueOnce({
      record_id: 5,
      draft: null,
      latest_approval: null,
      latest_run: null,
    })
    fetchAnalystActions.mockResolvedValueOnce({
      record_id: 5,
      count: 1,
      results: [{ action: "acknowledge" }],
    })
    buildVerifiedRunbook.mockResolvedValueOnce(sourceVerifiedDraft)

    render(<VerifiedRunbookPanel recordId="5" autoBuildRequestKey={1} />)

    await waitFor(() =>
      expect(buildVerifiedRunbook).toHaveBeenCalledWith("5", { rebuild: false })
    )
    expect(await screen.findByText("Verified on the source investigation")).toBeInTheDocument()
  })

  it("consumes an old acknowledge trigger without rebuilding an existing draft", async () => {
    fetchVerifiedRunbook.mockResolvedValueOnce({
      record_id: 5,
      draft: sourceVerifiedDraft,
      latest_approval: null,
      latest_run: null,
    })
    fetchAnalystActions.mockResolvedValueOnce({
      record_id: 5,
      count: 1,
      results: [{ action: "acknowledge" }],
    })

    render(<VerifiedRunbookPanel recordId="5" autoBuildRequestKey={1} />)

    expect(await screen.findByText("Verified on the source investigation")).toBeInTheDocument()
    await waitFor(() => expect(buildVerifiedRunbook).not.toHaveBeenCalled())
  })

  it("prevents duplicate compilation while a build is in progress", async () => {
    fetchVerifiedRunbook.mockResolvedValueOnce({
      record_id: 5,
      draft: null,
      latest_approval: null,
      latest_run: null,
    })
    fetchAnalystActions.mockResolvedValueOnce({
      record_id: 5,
      count: 1,
      results: [{ action: "acknowledge" }],
    })
    let finishBuild: (value: typeof sourceVerifiedDraft) => void = () => undefined
    buildVerifiedRunbook.mockReturnValueOnce(
      new Promise((resolve) => {
        finishBuild = resolve
      })
    )
    render(<VerifiedRunbookPanel recordId="5" />)

    const button = await screen.findByRole("button", { name: /build verified runbook/i })
    fireEvent.click(button)
    expect(button).toBeDisabled()
    finishBuild(sourceVerifiedDraft)
    expect(await screen.findByText("Verified on the source investigation")).toBeInTheDocument()
  })

  it("shows an in-progress warning instead of the previous failed status during rebuild", async () => {
    fetchVerifiedRunbook.mockResolvedValueOnce({
      record_id: 5,
      draft: { ...sourceVerifiedDraft, status: "FAILED" },
      latest_approval: null,
      latest_run: null,
    })
    fetchAnalystActions.mockResolvedValueOnce({
      record_id: 5,
      count: 1,
      results: [{ action: "acknowledge" }],
    })
    let finishBuild: (value: typeof sourceVerifiedDraft) => void = () => undefined
    buildVerifiedRunbook.mockReturnValueOnce(
      new Promise((resolve) => {
        finishBuild = resolve
      })
    )
    render(<VerifiedRunbookPanel recordId="5" />)

    fireEvent.click(await screen.findByRole("button", { name: /rebuild/i }))

    expect(await screen.findByText("Runbook rebuild in progress")).toBeInTheDocument()
    expect(screen.getByText("REBUILDING")).toBeInTheDocument()
    expect(
      screen.queryByText(/approval stays disabled until every step/i)
    ).not.toBeInTheDocument()

    finishBuild(sourceVerifiedDraft)
    expect(await screen.findByText("Verified on the source investigation")).toBeInTheDocument()
  })

  it("describes a partial verification as incomplete rather than a system failure", async () => {
    fetchVerifiedRunbook.mockResolvedValueOnce({
      record_id: 5,
      draft: {
        ...sourceVerifiedDraft,
        status: "FAILED",
        steps: [
          ...sourceVerifiedDraft.steps,
          {
            step_id: "step-2",
            title: "Correlate endpoint activity",
            intent: "Inspect endpoint evidence",
            expected_evidence: "Endpoint rows",
            stop_condition: "Stop when telemetry is unavailable",
          },
        ],
      },
      latest_approval: null,
      latest_run: null,
    })
    fetchAnalystActions.mockResolvedValueOnce({
      record_id: 5,
      count: 1,
      results: [{ action: "acknowledge" }],
    })
    render(<VerifiedRunbookPanel recordId="5" />)

    expect((await screen.findAllByText("VERIFICATION INCOMPLETE")).length).toBeGreaterThan(0)
    expect(screen.getByText("Verification produced 1 of 2 required step results.")).toBeInTheDocument()
    expect(screen.queryByText("FAILED")).not.toBeInTheDocument()
  })

  it("shows a retryable provider error without hiding the ready state", async () => {
    fetchVerifiedRunbook.mockResolvedValueOnce({
      record_id: 5,
      draft: null,
      latest_approval: null,
      latest_run: null,
    })
    fetchAnalystActions.mockResolvedValueOnce({
      record_id: 5,
      count: 1,
      results: [{ action: "acknowledge" }],
    })
    buildVerifiedRunbook.mockRejectedValueOnce(new Error("LLM provider timed out"))
    render(<VerifiedRunbookPanel recordId="5" />)

    fireEvent.click(await screen.findByRole("button", { name: /build verified runbook/i }))
    expect(await screen.findByText("LLM provider timed out")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /build verified runbook/i })).toBeEnabled()
  })

  it("keeps approval disabled for parser-only drafts", async () => {
    fetchVerifiedRunbook.mockResolvedValueOnce({
      record_id: 5,
      draft: {
        ...sourceVerifiedDraft,
        status: "PARSER_VALID",
        source_results: [
          { ...result, spl_results: { ...result.spl_results, row_count: 0, rows: [] } },
        ],
      },
      latest_approval: null,
      latest_run: null,
    })
    fetchAnalystActions.mockResolvedValueOnce({
      record_id: 5,
      count: 1,
      results: [{ action: "acknowledge" }],
    })
    render(<VerifiedRunbookPanel recordId="5" />)

    expect((await screen.findAllByText("PARSER VALID")).length).toBeGreaterThan(0)
    expect(screen.getByRole("button", { name: /^approve$/i })).toBeDisabled()
  })

  it("runs an approved draft on a target and shows measured savings", async () => {
    fetchVerifiedRunbook.mockResolvedValueOnce({
      record_id: 5,
      draft: sourceVerifiedDraft,
      latest_approval: {
        runbook_id: "rb-1",
        source_record_id: 5,
        decision: "approve",
        analyst: "analyst",
        note: null,
        created_at: "2026-07-14T10:01:00Z",
      },
      latest_run: null,
    })
    fetchAnalystActions.mockResolvedValueOnce({
      record_id: 5,
      count: 1,
      results: [{ action: "acknowledge" }],
    })
    runVerifiedRunbook.mockResolvedValueOnce({
      runbook_id: "rb-1",
      source_record_id: 5,
      target_record_id: 8,
      status: "REUSED",
      results: [result],
      duration_ms: 5000,
      estimated_manual_minutes: 25,
      estimated_minutes_saved: 24.917,
      savings_percent: 99.67,
      successful_step_count: 1,
      total_evidence_rows: 3,
      created_at: "2026-07-14T10:02:00Z",
    })
    render(<VerifiedRunbookPanel recordId="5" />)

    fireEvent.change(await screen.findByLabelText(/compatible target alert/i), {
      target: { value: "8" },
    })
    fireEvent.click(screen.getByRole("button", { name: /run approved runbook/i }))

    await waitFor(() => {
      expect(runVerifiedRunbook).toHaveBeenCalledWith("8", {
        source_record_id: 5,
        runbook_id: "rb-1",
        estimated_manual_minutes: 25,
      })
    })
    expect(await screen.findByText("24.9 min")).toBeInTheDocument()
    expect(screen.getByText("#8")).toBeInTheDocument()
  })

  it("discovers exact-match targets and selects the newest candidate", async () => {
    fetchVerifiedRunbook.mockResolvedValueOnce({
      record_id: 5,
      draft: sourceVerifiedDraft,
      latest_approval: {
        runbook_id: "rb-1",
        source_record_id: 5,
        decision: "approve",
        analyst: "analyst",
        note: null,
        created_at: "2026-07-14T10:01:00Z",
      },
      latest_run: null,
    })
    fetchAnalystActions.mockResolvedValueOnce({
      record_id: 5,
      count: 1,
      results: [{ action: "acknowledge" }],
    })
    fetchCompatibleRunbookTargets.mockResolvedValueOnce({
      source_record_id: 5,
      search_name: "Suspicious Login",
      count: 1,
      results: [
        {
          record_id: 8,
          created_at: "2026-07-14T10:02:00Z",
          sid: "sid-8",
          search_name: "Suspicious Login",
          row_index: 0,
          summary: "A compatible investigation",
          review_verdict: "TRUE_POSITIVE",
        },
      ],
    })

    render(<VerifiedRunbookPanel recordId="5" />)

    expect(await screen.findByText(/1 exact-match candidate/i)).toBeInTheDocument()
    expect(fetchCompatibleRunbookTargets).toHaveBeenCalledWith("5")
    expect(screen.getByRole("combobox", { name: /compatible target alert/i })).toHaveTextContent("#8")
    expect(screen.getByRole("button", { name: /run approved runbook/i })).toBeEnabled()
  })

  it("generates and approves a response preview without automatic execution", async () => {
    fetchVerifiedRunbook.mockResolvedValueOnce({
      record_id: 5,
      draft: sourceVerifiedDraft,
      latest_approval: null,
      latest_run: null,
      latest_response_preview: null,
      latest_response_decision: null,
    })
    fetchAnalystActions.mockResolvedValueOnce({
      record_id: 5,
      count: 1,
      results: [{ action: "acknowledge" }],
    })
    buildSafeResponsePreview.mockResolvedValueOnce(responsePreview)
    decideSafeResponsePreview.mockResolvedValueOnce({
      preview_id: "preview-1",
      runbook_id: "rb-1",
      source_record_id: 5,
      decision: "approve_for_manual_action",
      analyst: "analyst",
      note: "Evidence, impact, and rollback reviewed",
      automatic_execution_performed: false,
      created_at: "2026-07-15T10:01:00Z",
    })

    render(<VerifiedRunbookPanel recordId="5" />)

    expect(await screen.findByText(/automatic execution is impossible/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /generate preview/i }))

    expect(await screen.findByText("Contain the affected endpoint")).toBeInTheDocument()
    expect(screen.getAllByText(/preview only/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/No action has been executed/i)).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/required approval note/i), {
      target: { value: "Evidence, impact, and rollback reviewed" },
    })
    fireEvent.click(screen.getByRole("button", { name: /approve for manual action/i }))

    await waitFor(() => {
      expect(decideSafeResponsePreview).toHaveBeenCalledWith("5", {
        preview_id: "preview-1",
        decision: "approve_for_manual_action",
        note: "Evidence, impact, and rollback reviewed",
      })
    })
    expect(await screen.findByText("Approved for manual action")).toBeInTheDocument()
  })

  it("runs bounded autopilot and renders agent tool handoffs", async () => {
    const state = {
      record_id: 5,
      draft: sourceVerifiedDraft,
      latest_approval: null,
      latest_run: null,
      latest_response_preview: responsePreview,
      latest_response_decision: null,
    }
    fetchVerifiedRunbook.mockResolvedValue(state)
    fetchAnalystActions.mockResolvedValue({
      record_id: 5,
      count: 1,
      results: [{ action: "acknowledge" }],
    })
    runRunbookAutopilot.mockResolvedValue({
      session_id: "autopilot-1",
      source_record_id: 5,
      objective: "Assess and advance safely.",
      mode: "ADVANCE",
      status: "AWAITING_HUMAN_APPROVAL",
      agents: ["SUPERVISOR", "EVIDENCE_SCOUT", "POLICY_GUARD"],
      tools_used: ["storage.get_record", "runbook.state"],
      trace: [
        {
          event_id: "event-1",
          sequence: 1,
          agent: "SUPERVISOR",
          kind: "HANDOFF",
          status: "SUCCEEDED",
          summary: "Delegated source readiness to Evidence Scout.",
          tool_name: null,
          duration_ms: 0,
          metadata: {},
          created_at: "2026-07-15T10:00:00Z",
        },
        {
          event_id: "event-2",
          sequence: 2,
          agent: "EVIDENCE_SCOUT",
          kind: "TOOL_RESULT",
          status: "SUCCEEDED",
          summary: "Stored SOC analysis loaded.",
          tool_name: "storage.get_record",
          duration_ms: 10,
          metadata: {},
          created_at: "2026-07-15T10:00:00Z",
        },
      ],
      runbook_id: "rb-1",
      runbook_status: "SOURCE_VERIFIED",
      response_preview_id: "preview-1",
      next_recommended_action: "Review source evidence and approve or reject this Runbook revision.",
      human_approval_required: true,
      automatic_execution_performed: false,
      started_at: "2026-07-15T10:00:00Z",
      completed_at: "2026-07-15T10:00:01Z",
      duration_ms: 1000,
    })

    render(<VerifiedRunbookPanel recordId="5" />)

    expect(await screen.findByText("Runbook Autopilot Agents")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /run autopilot/i }))

    expect(await screen.findByTestId("runbook-autopilot-trace")).toBeInTheDocument()
    expect(screen.getAllByText("EVIDENCE SCOUT").length).toBeGreaterThan(0)
    expect(screen.getByText("storage.get_record")).toBeInTheDocument()
    expect(screen.getByText(/approve or reject this Runbook revision/i)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /ask about this runbook in chat/i })).toHaveAttribute(
      "href",
      expect.stringContaining("record_id=5")
    )
  })
})
