import { describe, expect, it } from "vitest"

import {
  buildTriageAnalysisIndex,
  resolveAlertDisplayInfo,
} from "@/lib/api/graph/alert-display"
import type { GraphFindingDetails, GraphNode } from "@/lib/api/graph/types"

describe("alert display + analysis links", () => {
  it("indexes triage queue by sid and search_name", () => {
    const index = buildTriageAnalysisIndex([
      {
        id: "42",
        sid: "scheduler__demo",
        search_name: "Suspicious RDP",
        source_track: "security",
      },
    ])
    expect(index.bySid.get("scheduler__demo")).toBe("/analysis/investigation/42")
    expect(index.bySearchName.get("suspicious rdp")).toBe("/analysis/investigation/42")
  })

  it("prefers contributing alert_name and resolves analysis href", () => {
    const node: GraphNode = {
      id: "n1",
      label: "Short",
      group: ["Alert"],
      properties: {
        alert_row_id: "ALERT-2",
        sid: "scheduler__demo",
        name: "Short",
      },
    }
    const finding = {
      details: {
        contributing_alerts: [
          {
            alert_row_id: "ALERT-2",
            alert_name: "Sysmon: PowerShell Download Activity (t8372)",
            sid: "scheduler__demo",
            search_name: "Sysmon: PowerShell Download Activity (t8372)",
            timestamp: "",
            threat_status: "open",
            risk_score: 55,
          },
        ],
      },
    } as unknown as GraphFindingDetails
    const index = buildTriageAnalysisIndex([
      { id: "99", sid: "scheduler__demo", search_name: "Other", source_track: "security" },
    ])
    const info = resolveAlertDisplayInfo(node, finding, index)
    expect(info.displayName).toBe("Sysmon: PowerShell Download Activity (t8372)")
    expect(info.analysisHref).toBe("/analysis/investigation/99")
  })
})
