import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { EnrichmentPanelContent } from "./soc-analysis-view"

describe("EnrichmentPanelContent", () => {
  it("shows resolution, risk, relationships, and inventory rows", () => {
    render(
      <EnrichmentPanelContent
        data={{
          enrichment: {
            confidence: "high",
            resolved_user_id: "jdoe",
            resolved_asset_id: "srv-web-01",
            matched_relationship_ids: ["rel-jdoe-web"],
            notes: "Linked via hostname match and relationship rel-jdoe-web.",
          },
          risk_context:
            "Asset srv-web-01: criticality=high, risk_score=4. User jdoe: risk_score=6, department=IT.",
          inventory_user: {
            user_id: "jdoe",
            department: "IT",
            risk_score: 6,
            display_name: "Jane Doe",
          },
          inventory_asset: {
            asset_id: "srv-web-01",
            hostname: "web-prod-01",
            criticality: "high",
            risk_score: 4,
          },
        }}
      />
    )

    expect(screen.getByText("Inventory resolution")).toBeInTheDocument()
    expect(screen.getByText("Risk context")).toBeInTheDocument()
    expect(screen.getByText("Matched user (inventory)")).toBeInTheDocument()
    expect(screen.getByText("Matched asset (inventory)")).toBeInTheDocument()
    expect(screen.getByText(/criticality=high/)).toBeInTheDocument()
    expect(screen.getByText("rel-jdoe-web")).toBeInTheDocument()
    expect(screen.getByText("Jane Doe")).toBeInTheDocument()
    expect(screen.getByText("web-prod-01")).toBeInTheDocument()
    expect(screen.getByText(/Linked via hostname/)).toBeInTheDocument()
  })
})
