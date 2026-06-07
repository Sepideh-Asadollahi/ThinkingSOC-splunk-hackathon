import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import {
  INVESTIGATION_TAB,
  InvestigationTabbedLayout,
} from "./investigation-tabbed-layout"

vi.mock("./investigation-timeline", () => ({
  InvestigationTimeline: () => <div data-testid="investigation-timeline-mock">Event timeline</div>,
}))

vi.mock("./investigation-analyst-actions", () => ({
  InvestigationAnalystActions: () => <div data-testid="investigation-analyst-mock">Analyst gate</div>,
}))

describe("InvestigationTabbedLayout", () => {
  it("renders timeline and analyst gate in Overview when recordId is set", () => {
    render(
      <InvestigationTabbedLayout
        event={{ id: "42", sid: "sid-1", search_name: "demo" }}
        payload={{}}
        analysis={{ summary: "Test summary" }}
        triage={null}
        classification={null}
        rawAlert={null}
        analysisInput={null}
        analysisOutput={null}
        phase={null}
        content={undefined}
        recordId="42"
      />
    )

    expect(screen.getByTestId("investigation-timeline-mock")).toBeInTheDocument()
    expect(screen.getByTestId("investigation-analyst-mock")).toBeInTheDocument()
    expect(screen.getByTestId("investigation-tabs-bar")).toBeInTheDocument()

    const summary = screen.getByTestId("security-summary-card")
    const analyst = screen.getByTestId("investigation-analyst-mock")
    expect(
      summary.compareDocumentPosition(analyst) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy()
  })

  it("shows Overview first and opens it by default", () => {
    render(
      <InvestigationTabbedLayout
        event={{ id: "5", sid: "sid-1", search_name: "demo" }}
        payload={{}}
        analysis={{
          summary: "Test summary",
          defender: "Contain host",
          hunter: { narrative: "Hunt more", splunk_search_suggestions: [] },
          judge: {
            verdict: "needs_investigation",
            priority: "high",
            confidence: "high",
            recommended_next_step: "Isolate endpoint immediately",
            rationale: "Critical asset and LOLBAS pattern require containment first.",
          },
          enrichment: {
            confidence: "high",
            resolved_user_id: "u1",
            resolved_asset_id: "a1",
            matched_relationship_ids: ["rel-1"],
            notes: "ok",
          },
          risk_context: "User u1: risk_score=5, department=Finance.",
          inventory_user: { user_id: "u1", risk_score: 5, department: "Finance" },
          inventory_asset: { asset_id: "a1", criticality: "high", risk_score: 8 },
        }}
        triage={null}
        classification={null}
        rawAlert={null}
        analysisInput={null}
        analysisOutput={null}
        phase={null}
        content={undefined}
      />
    )

    const tablist = screen.getByRole("tablist")
    const tabs = within(tablist).getAllByRole("tab")
    expect(tabs[0]).toHaveTextContent(INVESTIGATION_TAB.overview)
    expect(tabs[0]).toHaveAttribute("data-state", "active")

    expect(screen.getByTestId("investigation-tabs")).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: INVESTIGATION_TAB.overview })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: INVESTIGATION_TAB.recommendedAction })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: INVESTIGATION_TAB.agents })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: INVESTIGATION_TAB.enrichment })).toBeInTheDocument()
    expect(screen.getByText("Test summary")).toBeInTheDocument()
    expect(screen.queryByText("needs_investigation")).not.toBeInTheDocument()
    expect(screen.queryByText("Isolate endpoint immediately")).not.toBeInTheDocument()
    expect(screen.queryByText(/LOLBAS pattern/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Contain host/)).not.toBeInTheDocument()
  })

  it("does not show Admin question tab when no org gap is suggested", () => {
    render(
      <InvestigationTabbedLayout
        event={{ id: "7", sid: "sid-2", search_name: "demo" }}
        payload={{}}
        analysis={{
          summary: "No admin gap yet",
          judge: {
            verdict: "low",
            priority: "low",
            confidence: "medium",
            recommended_next_step: "Monitor",
            rationale: "Routine",
          },
        }}
        triage={null}
        classification={null}
        rawAlert={null}
        analysisInput={null}
        analysisOutput={null}
        phase={null}
        content={undefined}
      />
    )

    expect(screen.queryByRole("tab", { name: INVESTIGATION_TAB.adminQuestion })).not.toBeInTheDocument()
    expect(screen.queryByTestId("security-admin-gap-panel")).not.toBeInTheDocument()
  })

  it("shows judge step and rationale on Recommended action tab (not defender playbook)", async () => {
    const user = userEvent.setup()
    render(
      <InvestigationTabbedLayout
        event={{ id: "5", sid: "sid-1", search_name: "demo" }}
        payload={{}}
        analysis={{
          summary: "Test summary",
          defender: "Contain host",
          hunter: { narrative: "Hunt more", splunk_search_suggestions: [] },
          judge: {
            verdict: "needs_investigation",
            priority: "high",
            confidence: "high",
            recommended_next_step: "Isolate endpoint immediately",
            rationale: "Critical asset and LOLBAS pattern require containment first.",
          },
        }}
        triage={null}
        classification={null}
        rawAlert={null}
        analysisInput={null}
        analysisOutput={null}
        phase={null}
        content={undefined}
      />
    )

    await user.click(screen.getByRole("tab", { name: INVESTIGATION_TAB.recommendedAction }))
    const panel = await screen.findByTestId("security-recommended-action-panel")
    expect(within(panel).getByText("Isolate endpoint immediately")).toBeInTheDocument()
    expect(within(panel).getByText(/LOLBAS pattern/)).toBeInTheDocument()
    expect(within(panel).queryByText(/Contain host/)).not.toBeInTheDocument()
    expect(within(panel).queryByText("needs_investigation")).not.toBeInTheDocument()
    expect(within(panel).queryByText("Triage report")).not.toBeInTheDocument()
  })

  it("shows defender and rationale on Hunter & defender tab", async () => {
    const user = userEvent.setup()
    render(
      <InvestigationTabbedLayout
        event={{ id: "5", sid: "sid-1", search_name: "demo" }}
        payload={{}}
        analysis={{
          defender: "Contain host",
          hunter: { narrative: "Hunt more", splunk_search_suggestions: [] },
          judge: {
            verdict: "needs_investigation",
            recommended_next_step: "Isolate endpoint immediately",
            rationale: "Critical asset and LOLBAS pattern require containment first.",
          },
        }}
        triage={null}
        classification={null}
        rawAlert={null}
        analysisInput={null}
        analysisOutput={null}
        phase={null}
        content={undefined}
      />
    )

    await user.click(screen.getByRole("tab", { name: INVESTIGATION_TAB.agents }))
    expect(await screen.findByText(/Contain host/)).toBeInTheDocument()
    expect(screen.getByText(/LOLBAS pattern/)).toBeInTheDocument()
    expect(screen.getByText("needs_investigation")).toBeInTheDocument()
  })

  it("shows full triage report on Triage tab when triage is embedded in analysis", async () => {
    const user = userEvent.setup()
    render(
      <InvestigationTabbedLayout
        event={{ id: "8", sid: "sid-3", search_name: "demo" }}
        payload={{}}
        analysis={{
          summary: "Alert",
          judge: { recommended_next_step: "Review logs" },
          triage: {
            review_verdict: "NEEDS_HUMAN_REVIEW",
            investigation_priority: "high",
            triage_score: 72,
            report: {
              headline: "Suspicious login pattern",
              why_verdict: "Low judge confidence",
              why_priority: "Critical asset",
              recommended_action: "Escalate to tier-2 within 1 hour",
            },
          },
        }}
        triage={null}
        classification={null}
        rawAlert={null}
        analysisInput={null}
        analysisOutput={null}
        phase={null}
        content={undefined}
      />
    )

    expect(screen.getByRole("tab", { name: INVESTIGATION_TAB.triage })).toBeInTheDocument()
    await user.click(screen.getByRole("tab", { name: INVESTIGATION_TAB.triage }))
    expect(await screen.findByTestId("security-triage-panel")).toBeInTheDocument()
    expect(screen.getByText("Suspicious login pattern")).toBeInTheDocument()
    expect(screen.getByText(/Low judge confidence/)).toBeInTheDocument()
  })

  it("shows Admin question tab and overview card when org gap is active", () => {
    render(
      <InvestigationTabbedLayout
        event={{ id: "6", sid: "sid-osk", search_name: "osk alert" }}
        payload={{}}
        analysis={{
          summary: "LOLBAS osk.exe",
          admin_org_gap: {
            should_suggest_question: true,
            gap_summary: "Process policy unclear for osk.exe on workstation.",
            question_for_admin:
              "On workstation we8105desk, is osk.exe approved for end users when launched from PowerShell?",
          },
          judge: {
            verdict: "needs_investigation",
            priority: "high",
            confidence: "high",
            recommended_next_step: "Review",
            rationale: "Suspicious",
          },
        }}
        triage={null}
        classification={null}
        rawAlert={null}
        analysisInput={null}
        analysisOutput={null}
        phase={null}
        content={undefined}
      />
    )

    expect(screen.getByRole("tab", { name: INVESTIGATION_TAB.adminQuestion })).toBeInTheDocument()
    expect(screen.getByTestId("admin-org-gap-panel")).toBeInTheDocument()
    expect(screen.getByText(/osk.exe approved/i)).toBeInTheDocument()
  })

  it("shows Evidence chain tab when evidence_chain exists", async () => {
    const user = userEvent.setup()
    render(
      <InvestigationTabbedLayout
        event={{ id: "9", sid: "sid-ec", search_name: "demo" }}
        payload={{}}
        analysis={{
          summary: "Has chain",
          judge: {
            verdict: "needs_investigation",
            priority: "high",
            recommended_next_step: "Review",
            rationale: "test",
          },
          evidence_chain: {
            request: { sid: "sid-ec", row_index: 0 },
            decision: { verdict: "needs_investigation" },
          },
        }}
        triage={null}
        classification={null}
        rawAlert={null}
        analysisInput={null}
        analysisOutput={null}
        phase={null}
        content={undefined}
      />
    )

    expect(screen.getByRole("tab", { name: INVESTIGATION_TAB.evidenceChain })).toBeInTheDocument()
    await user.click(screen.getByRole("tab", { name: INVESTIGATION_TAB.evidenceChain }))
    expect(await screen.findByTestId("security-evidence-chain-panel")).toBeInTheDocument()
    expect(screen.getByText(/sid-ec/)).toBeInTheDocument()
  })
})
