import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { DashboardRunbookOperations } from "./dashboard-runbook-operations"

describe("DashboardRunbookOperations", () => {
  it("renders the ThinkingSOC Lite lifecycle, safe outcomes, Autopilot, and Chat metrics", () => {
    render(
      <DashboardRunbookOperations
        ops={{
          latest_runbooks: 4,
          source_verified: 3,
          human_approved: 2,
          reusable_alert_names: 2,
          executions: 3,
          reused: 2,
          no_evidence: 1,
          failed: 0,
          evidence_rows: 9,
          estimated_minutes_saved: 42.4,
          shadow_runs: 2,
          response_previews: 1,
          autopilot_sessions: 2,
          autopilot_completed: 2,
          chat_conversations: 5,
          chat_messages: 17,
        }}
      />
    )

    expect(screen.getByText("Runbook operations")).toBeInTheDocument()
    expect(screen.getByText("Source verified")).toBeInTheDocument()
    expect(screen.getByText("Human approved")).toBeInTheDocument()
    expect(screen.getByText("Safe abstention / no evidence")).toBeInTheDocument()
    expect(screen.getByText("2/2")).toBeInTheDocument()
    expect(screen.getByText("17 persisted messages")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Runbook Library" })).toHaveAttribute(
      "href",
      "/runbooks/library"
    )
  })
})
