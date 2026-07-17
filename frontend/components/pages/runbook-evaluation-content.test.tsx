import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { RunbookEvaluationContent } from "./runbook-evaluation-content"

const fetchRunbookEvaluation = vi.fn()
const fetchRunbookLibrary = vi.fn()
const fetchCompatibleRunbookTargets = vi.fn()
const runShadowReplay = vi.fn()

vi.mock("@/lib/api/investigation-workflow", () => ({
  fetchRunbookEvaluation: (...args: unknown[]) => fetchRunbookEvaluation(...args),
  fetchRunbookLibrary: (...args: unknown[]) => fetchRunbookLibrary(...args),
  fetchCompatibleRunbookTargets: (...args: unknown[]) => fetchCompatibleRunbookTargets(...args),
  runShadowReplay: (...args: unknown[]) => runShadowReplay(...args),
}))

const evaluation = {
  generated_at: "2026-07-15T10:00:00Z",
  revision_count: 1,
  alert_count: 1,
  latest_runbook_count: 1,
  approved_runbook_count: 0,
  production_run_count: 0,
  shadow_run_count: 1,
  source_verified_revision_count: 0,
  parser_valid_revision_count: 1,
  failed_revision_count: 0,
  total_step_count: 1,
  parser_valid_step_count: 1,
  parser_valid_rate: 100,
  shadow_evidence_run_count: 1,
  evidence_coverage_rate: 100,
  total_shadow_evidence_rows: 3,
  total_execution_errors: 0,
  average_compile_duration_ms: 1000,
  average_shadow_duration_ms: 2000,
  projected_minutes_saved: 24.9,
  projected_labor_savings_usd: 26.98,
  realized_minutes_saved: 0,
  total_prompt_tokens: 1000,
  total_completion_tokens: 500,
  estimated_compile_llm_cost_usd: 0,
  analyst_hourly_cost_usd: 65,
  shadow_status_breakdown: { EVIDENCE_FOUND: 1, NO_EVIDENCE: 0, FAILED: 0 },
  recent_shadow_runs: [],
}

const draft = {
  runbook_id: "rb-1",
  source_record_id: 10,
  title: "Investigate login",
  summary: "Summary",
  applicable_search_name: "Suspicious Login",
  source_verdict: "needs_investigation",
  steps: [{ step_id: "step-1", title: "Step", intent: "Intent", expected_evidence: "Events", stop_condition: "Stop" }],
  decision_rule: "Escalate with evidence",
  limitations: [],
  source_results: [],
  status: "PARSER_VALID",
  configured_model: "test-model",
  model: "test-model",
  prompt_tokens: 1000,
  completion_tokens: 500,
  generation_duration_ms: 500,
  verification_duration_ms: 500,
  compile_duration_ms: 1000,
  parser_valid_step_count: 1,
  successful_step_count: 0,
  total_evidence_rows: 0,
  revision: 1,
  parent_runbook_id: null,
  origin: "compiled",
  revision_note: null,
  edited_by: null,
  imported_from_runbook_id: null,
  created_at: "2026-07-15T09:00:00Z",
}

describe("RunbookEvaluationContent", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchRunbookEvaluation.mockResolvedValue(evaluation)
    fetchRunbookLibrary.mockResolvedValue({
      count: 1,
      alert_count: 1,
      groups: [{ alert_name: "Suspicious Login", count: 1, runbooks: [{ draft, latest_approval: null, latest_run: null, is_latest_for_source: true }] }],
    })
    fetchCompatibleRunbookTargets.mockResolvedValue({
      source_record_id: 10,
      search_name: "Suspicious Login",
      count: 1,
      results: [{ record_id: 20, sid: "sid-20", search_name: "Suspicious Login", created_at: null, row_index: 0, summary: "Historical alert", review_verdict: "TRUE_POSITIVE" }],
    })
    runShadowReplay.mockResolvedValue({
      shadow_run_id: "shadow-2",
      runbook_id: "rb-1",
      source_record_id: 10,
      target_record_id: 20,
      source_sid: "sid-10",
      target_sid: "sid-20",
      search_name: "Suspicious Login",
      status: "EVIDENCE_FOUND",
      results: [],
      duration_ms: 2000,
      estimated_manual_minutes: 25,
      projected_minutes_saved: 24.9,
      projected_labor_savings_usd: 26.98,
      parser_valid_step_count: 1,
      successful_step_count: 1,
      total_evidence_rows: 3,
      execution_error_count: 0,
      failure_reason: null,
      created_at: "2026-07-15T10:00:00Z",
    })
  })

  it("renders measured quality and loads only compatible distinct-SID targets", async () => {
    render(<RunbookEvaluationContent />)
    expect(await screen.findByText("Shadow Replay & Evaluation")).toBeInTheDocument()
    expect(await screen.findAllByText("100.0%")).not.toHaveLength(0)
    await waitFor(() => expect(fetchCompatibleRunbookTargets).toHaveBeenCalledWith(10, 50))
    expect(screen.getByRole("button", { name: "Run Shadow Replay" })).toBeEnabled()
  })

  it("executes replay and renders its persisted result", async () => {
    render(<RunbookEvaluationContent />)
    const button = await screen.findByRole("button", { name: "Run Shadow Replay" })
    await waitFor(() => expect(button).toBeEnabled())
    fireEvent.click(button)
    await waitFor(() => expect(runShadowReplay).toHaveBeenCalledWith(20, {
      source_record_id: 10,
      runbook_id: "rb-1",
      estimated_manual_minutes: 25,
    }))
    expect(await screen.findByTestId("shadow-replay-result")).toHaveTextContent("EVIDENCE FOUND")
  })
})
