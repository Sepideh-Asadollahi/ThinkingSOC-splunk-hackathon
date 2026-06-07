/**
 * @vitest-environment node
 */
import { describe, expect, it } from "vitest"

import {
  formatEventCreatedAt,
  getEventSummary,
  getEventVerdict,
  getStorageEventId,
} from "./storage-events"

describe("storage-events helpers", () => {
  it("formatEventCreatedAt returns dash for empty values", () => {
    expect(formatEventCreatedAt(null)).toBe("—")
    expect(formatEventCreatedAt("")).toBe("—")
  })

  it("formatEventCreatedAt formats valid ISO timestamps", () => {
    const out = formatEventCreatedAt("2026-05-16T12:00:00.000Z")
    expect(out).not.toBe("—")
    expect(out.length).toBeGreaterThan(0)
  })

  it("getEventVerdict reads judge verdict from analysis payload", () => {
    const event = {
      payload: {
        analysis: {
          judge: { verdict: "needs_investigation" },
        },
      },
    }
    expect(getEventVerdict(event)).toBe("needs_investigation")
  })

  it("getEventVerdict falls back to analysis_output.verdict", () => {
    const event = {
      payload: {
        analysis_output: { verdict: "false_positive" },
      },
    }
    expect(getEventVerdict(event)).toBe("false_positive")
  })

  it("getEventVerdict returns dash when missing", () => {
    expect(getEventVerdict({})).toBe("—")
  })

  it("getEventSummary returns analysis summary or phase", () => {
    expect(
      getEventSummary({
        payload: { analysis: { summary: "Suspicious login pattern" } },
      })
    ).toBe("Suspicious login pattern")
    expect(getEventSummary({ payload: { phase: "hunter" } })).toBe("hunter")
    expect(getEventSummary({ payload: {} })).toBeNull()
  })

  it("getStorageEventId stringifies numeric id", () => {
    expect(getStorageEventId({ id: 42 })).toBe("42")
    expect(getStorageEventId({})).toBeNull()
  })
})
