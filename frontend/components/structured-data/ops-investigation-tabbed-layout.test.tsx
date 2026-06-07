import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { OpsInvestigationTabbedLayout } from "./ops-investigation-tabbed-layout"

describe("OpsInvestigationTabbedLayout", () => {
  it("shows Overview as the first tab and opens it by default", () => {
    render(
      <OpsInvestigationTabbedLayout
        event={{ id: "5", sid: "sid-obs", search_name: "High CPU" }}
        payload={{}}
        analysis={{
          summary: "CPU and latency elevated on payment-api",
          entity_resolution: {
            resolved_host: "web-prod-01",
            resolved_service: "payment-api",
            resolved_asset_id: "srv-web-01",
            confidence: "high",
            notes: "Matched inventory",
          },
          impact_context: {
            impact_level: "high",
            affected_entities: ["payment-api"],
            customer_impact: "Checkout delays",
            business_criticality: "critical",
          },
          diagnoser: {
            root_cause_hypotheses: [
              {
                hypothesis: "Resource saturation on host",
                confidence: "medium",
                evidence_refs: ["cpu"],
              },
            ],
            followup_searches: ["index=metrics host=web-prod-01 earliest=-1h | timechart avg(cpu)"],
          },
          responder: {
            recommended_actions: ["Scale out payment-api pods"],
            safety_notes: ["Confirm with SRE before restart"],
          },
          ops_judge: {
            verdict: "needs_investigation",
            priority: "high",
            recommended_next_step: "Review metrics and recent deploys",
            confidence: "medium",
            rationale: "Critical service impact",
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

    expect(screen.getByTestId("ops-investigation-tabs")).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "Overview" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "Entity" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "Diagnoser" })).toBeInTheDocument()
    expect(screen.getByText(/CPU and latency elevated/)).toBeInTheDocument()
    expect(screen.queryByText(/Scale out payment-api/)).not.toBeInTheDocument()
  })
})
