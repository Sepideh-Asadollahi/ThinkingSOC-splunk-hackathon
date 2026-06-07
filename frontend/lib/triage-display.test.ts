import { describe, expect, it } from "vitest"

import { formatTriageHeadline, pickTriageRiskScore, triageRiskScoreBadgeClass } from "./triage-display"

describe("pickTriageRiskScore", () => {
  it("reads triage_score from triage object", () => {
    expect(
      pickTriageRiskScore({
        triage_score: 82,
        investigation_priority: "critical",
      })
    ).toBe(82)
  })

  it("falls back to payload triage_score", () => {
    expect(pickTriageRiskScore(null, { triage_score: 64 })).toBe(64)
  })
})

describe("triageRiskScoreBadgeClass", () => {
  it("uses critical red styling at 80+", () => {
    expect(triageRiskScoreBadgeClass(82)).toContain("red")
  })

  it("uses orange styling at 60-79", () => {
    expect(triageRiskScoreBadgeClass(72)).toContain("orange")
  })

  it("uses yellow styling at 40-59", () => {
    expect(triageRiskScoreBadgeClass(45)).toContain("yellow")
  })
})

describe("formatTriageHeadline", () => {
  it("builds full headline when report is missing", () => {
    expect(
      formatTriageHeadline({
        investigation_priority: "critical",
        review_verdict: "NEEDS_HUMAN_REVIEW",
        triage_score: 82,
      })
    ).toBe("CRITICAL priority — NEEDS HUMAN REVIEW — score 82")
  })
})
