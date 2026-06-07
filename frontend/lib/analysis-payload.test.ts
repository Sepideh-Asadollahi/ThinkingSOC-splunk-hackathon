import { describe, expect, it } from "vitest"

import {
  getRecordSourceTrack,
  investigationHrefForRow,
  pickObservabilityAnalysis,
  pickSecurityAnalysis,
} from "./analysis-payload"

describe("analysis-payload", () => {
  it("infers observability from record type", () => {
    expect(
      getRecordSourceTrack({
        tsoc_record_type: "observability_analysis",
        payload: { analysis: { ops_judge: { verdict: "degraded" } } },
      })
    ).toBe("observability")
  })

  it("prefers explicit source_track", () => {
    expect(getRecordSourceTrack({ source_track: "security", payload: {} })).toBe("security")
  })

  it("pickObservabilityAnalysis reads analysis and observability_result", () => {
    const fromAnalysis = pickObservabilityAnalysis({
      tsoc_record_type: "observability_analysis",
      analysis: {
        track: "observability",
        summary: "CPU spike",
        ops_judge: { verdict: "investigate" },
      },
    })
    expect(fromAnalysis?.summary).toBe("CPU spike")

    const fromRoute = pickObservabilityAnalysis({
      observability_result: { summary: "Latency", ops_judge: { verdict: "ok" } },
    })
    expect(fromRoute?.summary).toBe("Latency")
  })

  it("pickSecurityAnalysis skips observability-shaped analysis", () => {
    expect(
      pickSecurityAnalysis({
        analysis: { ops_judge: { verdict: "x" }, summary: "ops" },
      })
    ).toBeNull()

    expect(
      pickSecurityAnalysis({
        security_result: { summary: "sec", judge: { verdict: "fp" } },
      })?.summary
    ).toBe("sec")
  })

  it("investigationHrefForRow routes by track", () => {
    expect(
      investigationHrefForRow({ id: "42", source_track: "observability" })
    ).toBe("/analysis/ops-investigation/42")
    expect(
      investigationHrefForRow({ id: "7", tsoc_record_type: "soc_analysis" })
    ).toBe("/analysis/investigation/7")
    expect(investigationHrefForRow({})).toBeNull()
  })
})
