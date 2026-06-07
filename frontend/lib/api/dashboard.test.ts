import { describe, expect, it } from "vitest"

import {
  formatActivityTimelineForChart,
  formatShortDate,
  hasChartData,
  priorityChartData,
  topRecordTypes,
  verdictChartData,
} from "@/lib/api/dashboard"

describe("dashboard transforms", () => {
  it("formats short dates", () => {
    const label = formatShortDate("2026-05-18")
    expect(label).toMatch(/May|18/)
  })

  it("maps activity timeline labels", () => {
    const rows = formatActivityTimelineForChart([
      { date: "2026-05-18", security: 1, observability: 0, correlation: 0, other: 0 },
    ])
    expect(rows[0].label).toBeTruthy()
    expect(rows[0].security).toBe(1)
  })

  it("limits record types", () => {
    const top = topRecordTypes(
      [
        { type: "a", count: 1 },
        { type: "b", count: 5 },
        { type: "c", count: 3 },
      ],
      2
    )
    expect(top).toHaveLength(2)
    expect(top[0].type).toBe("b")
  })

  it("builds verdict chart rows", () => {
    const rows = verdictChartData([{ verdict: "TRUE_POSITIVE", count: 2 }])
    expect(rows[0].value).toBe(2)
    expect(rows[0].fill).toContain("hsl")
  })

  it("builds priority chart rows", () => {
    const rows = priorityChartData([{ priority: "critical", count: 1 }])
    expect(rows[0].priority).toBe("critical")
  })

  it("detects empty chart data", () => {
    expect(hasChartData([0, 0])).toBe(false)
    expect(hasChartData([0, 3])).toBe(true)
  })
})
