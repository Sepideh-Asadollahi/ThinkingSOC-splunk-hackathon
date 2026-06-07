import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { AttackNarrative } from "@/components/correlation/attack-narrative"

describe("AttackNarrative", () => {
  it("renders numbered steps and executive summary", () => {
    render(
      <AttackNarrative
        executiveSummary="Phishing led to lateral movement."
        steps={[
          {
            phase_label: "Initial Access",
            description: "User clicked phishing link.",
            mitre_technique_id: "T1566",
            mitre_technique_name: "Phishing",
          },
          {
            phase_label: "Lateral Movement",
            description: "RDP to SERVER01.",
            mitre_technique_id: "T1021",
          },
        ]}
      />,
    )
    expect(screen.getByText("Phishing led to lateral movement.")).toBeTruthy()
    expect(screen.getByText("1")).toBeTruthy()
    expect(screen.getByText("2")).toBeTruthy()
    expect(screen.getByText("Initial Access")).toBeTruthy()
    expect(screen.getByText("User clicked phishing link.")).toBeTruthy()
    expect(screen.getByText(/T1566/)).toBeTruthy()
  })

  it("shows placeholder when empty", () => {
    render(<AttackNarrative />)
    expect(screen.getByText(/No attack narrative yet/)).toBeTruthy()
  })
})
