import { fireEvent, render, screen, within } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { RunbookFlowGraph } from "./runbook-flow-graph"

const draft = {
  runbook_id: "rb-graph-1",
  source_record_id: 42,
  title: "Suspicious login investigation",
  summary: "Correlate identity, network, and authentication evidence without exposing the source payload.",
  applicable_search_name: "Suspicious Login",
  source_verdict: "TRUE_POSITIVE",
  steps: [
    {
      step_id: "identity-correlation",
      title: "Correlate identity activity",
      intent: "Find unusual authentication sources for the affected identity.",
      expected_evidence: "Authentication events grouped by user and source.",
      stop_condition: "Stop when identity telemetry is unavailable.",
    },
    {
      step_id: "network-pivot",
      title: "Pivot to network activity",
      intent: "Compare the source with recent network destinations.",
      expected_evidence: "Destination and transfer-volume evidence.",
      stop_condition: "Stop when no source address is present.",
    },
  ],
  decision_rule: "Escalate only when independent evidence corroborates the source alert.",
  limitations: ["Requires authentication telemetry"],
  source_results: [
    {
      question: "Correlate identity activity",
      spl: "index=auth | stats count by user, src",
      explanation: "Correlates authentication sources",
      time_window: "earliest=-24h latest=now",
      pivots: ["user", "src"],
      notes: [],
      validation: { method: "splunk_parser" as const, valid: true, message: null },
      spl_results: { row_count: 3, rows: [], truncated: false, error: null },
    },
    {
      question: "Pivot to network activity",
      spl: "index=network | stats count by dest",
      explanation: "Groups network destinations",
      time_window: "earliest=-24h latest=now",
      pivots: ["src", "dest"],
      notes: [],
      validation: { method: "splunk_parser" as const, valid: true, message: null },
      spl_results: { row_count: 0, rows: [], truncated: false, error: null },
    },
  ],
  status: "SOURCE_VERIFIED" as const,
  configured_model: "openai/gpt-5.6",
  model: "gpt-5.6-2026-07-01",
  prompt_tokens: 100,
  completion_tokens: 80,
  generation_duration_ms: 400,
  verification_duration_ms: 800,
  compile_duration_ms: 1200,
  parser_valid_step_count: 2,
  successful_step_count: 1,
  total_evidence_rows: 3,
  revision: 1,
  parent_runbook_id: null,
  origin: "compiled" as const,
  revision_note: null,
  edited_by: null,
  imported_from_runbook_id: null,
  created_at: "2026-07-14T10:00:00Z",
}

describe("RunbookFlowGraph", () => {
  it("renders the complete source-to-reuse path as rectangular interactive nodes", () => {
    render(<RunbookFlowGraph draft={draft} approval={null} latestRun={null} />)

    expect(screen.getByRole("heading", { name: "Runbook execution graph" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Source: Investigation #42" })).toHaveAttribute("aria-pressed", "true")
    expect(screen.getByRole("button", { name: "Step 1: Correlate identity activity" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Step 2: Pivot to network activity" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Human gate: Awaiting review" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Safe reuse: Exact-match target" })).toBeInTheDocument()
  })

  it("shows the selected node details without relying on hover", () => {
    render(<RunbookFlowGraph draft={draft} approval={null} latestRun={null} />)

    const step = screen.getByRole("button", { name: "Step 1: Correlate identity activity" })
    fireEvent.click(step)

    expect(step).toHaveAttribute("aria-pressed", "true")
    const details = screen.getByTestId("runbook-flow-details")
    expect(within(details).getByText("Expected evidence")).toBeInTheDocument()
    expect(within(details).getByText("Authentication events grouped by user and source.")).toBeInTheDocument()
    expect(within(details).getByText("Stop when identity telemetry is unavailable.")).toBeInTheDocument()
  })

  it("updates the gate and target nodes after an approved reuse", () => {
    render(
      <RunbookFlowGraph
        draft={draft}
        approval={{
          runbook_id: "rb-graph-1",
          source_record_id: 42,
          decision: "approve",
          analyst: "analyst",
          note: "Queries reviewed",
          created_at: "2026-07-14T10:01:00Z",
        }}
        latestRun={{
          runbook_id: "rb-graph-1",
          source_record_id: 42,
          target_record_id: 84,
          status: "REUSED",
          results: [],
          duration_ms: 4200,
          estimated_manual_minutes: 25,
          estimated_minutes_saved: 24.9,
          savings_percent: 99.6,
          successful_step_count: 2,
          total_evidence_rows: 7,
          created_at: "2026-07-14T10:02:00Z",
        }}
      />
    )

    expect(screen.getByRole("button", { name: "Human gate: Runbook approved" })).toBeInTheDocument()
    const target = screen.getByRole("button", { name: "Safe reuse: Target #84" })
    fireEvent.click(target)
    expect(within(screen.getByTestId("runbook-flow-details")).getByText("24.9 minutes")).toBeInTheDocument()
  })

  it("keeps long graphs scroll-safe on desktop and stacked below the desktop breakpoint", () => {
    render(<RunbookFlowGraph draft={draft} approval={null} latestRun={null} />)

    const graph = screen.getByTestId("runbook-flow-graph")
    const scrollViewport = graph.querySelector(".overflow-x-auto")
    const path = screen.getByRole("list", { name: "Runbook execution path" })
    const firstNode = screen.getByRole("button", { name: "Source: Investigation #42" })

    expect(scrollViewport).toBeInTheDocument()
    expect(path).toHaveClass("flex-col", "xl:flex-row")
    expect(firstNode).toHaveClass("min-w-0", "w-full")
  })
})
