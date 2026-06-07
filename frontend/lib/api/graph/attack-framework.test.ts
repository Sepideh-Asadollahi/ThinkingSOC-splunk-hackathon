import { describe, expect, it } from "vitest"

import { buildAlertFrameworkByNodeId } from "@/lib/api/graph/attack-framework"
import type { GraphFindingDetails, GraphNode } from "@/lib/api/graph/types"

const finding: GraphFindingDetails = {
  id: "f1",
  display_id: "GF-1",
  finding_type: "smart_attack_discovery",
  title: "Test",
  summary: "s",
  risk_score: 70,
  created_at: "2026-01-01T00:00:00Z",
  ticket_status: "open",
  owner: "u",
  updated_at: "2026-01-01T00:00:00Z",
  details: {
    incident_id: "inc-1",
    incident_title: "T",
    executive_summary: "e",
    attack_analysis_steps: [
      {
        phase_label: "Initial Access",
        description: "Phishing",
        mitre_technique_id: "T1566",
        mitre_technique_name: "Phishing",
      },
      {
        phase_label: "Lateral Movement",
        description: "RDP",
        mitre_technique_id: "T1021",
        mitre_technique_name: "Remote Services",
      },
    ],
    contributing_alerts: [
      {
        alert_row_id: "ALERT-1",
        alert_name: "Phishing",
        timestamp: "2026-05-20T09:00:00Z",
        threat_status: "open",
        risk_score: 60,
      },
      {
        alert_row_id: "ALERT-2",
        alert_name: "Suspicious RDP",
        timestamp: "2026-05-20T10:00:00Z",
        threat_status: "open",
        risk_score: 75,
      },
    ],
    key_entities: { identities: [], assets: [], iocs: [] },
    recommended_next_steps: [],
    smart_hunt_queries: [],
    aggregated_mitre_techniques: [],
    raw_analysis: {},
    raw_paths: [],
  },
}

const nodes: GraphNode[] = [
  {
    id: "n1",
    label: "Phishing",
    group: ["Alert"],
    properties: { alert_row_id: "ALERT-1", timestamp: "2026-05-20T09:00:00Z" },
  },
  {
    id: "n2",
    label: "Suspicious RDP",
    group: ["Alert"],
    properties: { alert_row_id: "ALERT-2", timestamp: "2026-05-20T10:00:00Z" },
  },
]

describe("buildAlertFrameworkByNodeId", () => {
  it("maps steps via contributing alert_row_id", () => {
    const map = buildAlertFrameworkByNodeId(nodes, [], finding)
    expect(map.get("n1")?.killChainPhase).toBe("Initial Access")
    expect(map.get("n1")?.mitreTechniqueId).toBe("T1566")
    expect(map.get("n2")?.mitreTechniqueId).toBe("T1021")
  })

  it("maps steps by chronological index when contributing_alerts are out of order", () => {
    const shuffled: GraphFindingDetails = {
      ...finding,
      details: {
        ...finding.details!,
        attack_analysis_steps: [
          {
            phase_label: "Initial Access",
            description: "Phishing link",
            mitre_technique_id: "T1566",
            mitre_technique_name: "Phishing",
          },
          {
            phase_label: "Command and Control",
            description: "C2 beacon",
            mitre_technique_id: "T1071",
            mitre_technique_name: "Application Layer Protocol",
          },
          {
            phase_label: "Lateral Movement",
            description: "Suspicious RDP session",
            mitre_technique_id: "T1021.001",
            mitre_technique_name: "Remote Desktop Protocol",
          },
        ],
        contributing_alerts: [
          {
            alert_row_id: "ALERT-1",
            alert_name: "Phishing",
            timestamp: "2026-05-20T09:00:00Z",
            threat_status: "open",
            risk_score: 60,
          },
          {
            alert_row_id: "ALERT-3",
            alert_name: "Suspicious RDP",
            timestamp: "2026-05-20T11:00:00Z",
            threat_status: "open",
            risk_score: 75,
          },
          {
            alert_row_id: "ALERT-2",
            alert_name: "Outbound C2 beacon",
            timestamp: "2026-05-20T10:00:00Z",
            threat_status: "closed",
            risk_score: 65,
          },
        ],
      },
    }
    const graphNodes: GraphNode[] = [
      {
        id: "n1",
        label: "Phishing",
        group: ["Alert"],
        properties: { alert_row_id: "ALERT-1", timestamp: "2026-05-20T09:00:00Z" },
      },
      {
        id: "n2",
        label: "Outbound C2 beacon",
        group: ["Alert"],
        properties: { alert_row_id: "ALERT-2", timestamp: "2026-05-20T10:00:00Z" },
      },
      {
        id: "n3",
        label: "Suspicious RDP",
        group: ["Alert"],
        properties: { alert_row_id: "ALERT-3", timestamp: "2026-05-20T11:00:00Z" },
      },
    ]
    const map = buildAlertFrameworkByNodeId(graphNodes, [], shuffled)
    expect(map.get("n1")?.mitreTechniqueId).toBe("T1566")
    expect(map.get("n2")?.mitreTechniqueId).toBe("T1071")
    expect(map.get("n3")?.mitreTechniqueId).toBe("T1021.001")
  })
})
