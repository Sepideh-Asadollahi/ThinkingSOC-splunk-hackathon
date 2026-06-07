/**
 * @vitest-environment node
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import {
  parseTimeFilter,
  rowMatchesTimeFilter,
  TIME_FILTER_OPTIONS,
} from "./time-utils"

describe("parseTimeFilter", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date("2026-05-18T12:00:00.000Z"))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns epoch for "all" (case-insensitive)', () => {
    expect(parseTimeFilter("all").getTime()).toBe(0)
    expect(parseTimeFilter("ALL").getTime()).toBe(0)
    expect(parseTimeFilter("  all  ").getTime()).toBe(0)
  })

  it("subtracts supported units from now", () => {
    expect(parseTimeFilter("30s").toISOString()).toBe("2026-05-18T11:59:30.000Z")
    expect(parseTimeFilter("5m").toISOString()).toBe("2026-05-18T11:55:00.000Z")
    expect(parseTimeFilter("2h").toISOString()).toBe("2026-05-18T10:00:00.000Z")
    expect(parseTimeFilter("1d").toISOString()).toBe("2026-05-17T12:00:00.000Z")
    expect(parseTimeFilter("1w").toISOString()).toBe("2026-05-11T12:00:00.000Z")
    expect(parseTimeFilter("1mo").toISOString()).toBe("2026-04-18T12:00:00.000Z")
    expect(parseTimeFilter("1y").toISOString()).toBe("2025-05-18T12:00:00.000Z")
  })

  it("accepts spaced input", () => {
    expect(parseTimeFilter("  1h  ").toISOString()).toBe("2026-05-18T11:00:00.000Z")
  })

  it("returns now for invalid input", () => {
    expect(parseTimeFilter("nope").toISOString()).toBe("2026-05-18T12:00:00.000Z")
    expect(parseTimeFilter("").toISOString()).toBe("2026-05-18T12:00:00.000Z")
  })
})

describe("rowMatchesTimeFilter", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date("2026-05-18T12:00:00.000Z"))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("includes all rows when filter is all", () => {
    expect(rowMatchesTimeFilter(null, "all")).toBe(true)
    expect(rowMatchesTimeFilter("invalid", "all")).toBe(true)
  })

  it("filters by stored timestamp", () => {
    expect(rowMatchesTimeFilter("2026-05-18T11:30:00.000Z", "1h")).toBe(true)
    expect(rowMatchesTimeFilter("2026-05-18T10:00:00.000Z", "1h")).toBe(false)
    expect(rowMatchesTimeFilter(null, "1h")).toBe(false)
  })
})

describe("TIME_FILTER_OPTIONS", () => {
  it("includes all preset values used by the UI", () => {
    const values = TIME_FILTER_OPTIONS.map((o) => o.value)
    expect(values).toContain("all")
    expect(values).toContain("1h")
    expect(values).toContain("24h")
    expect(values).toContain("7d")
  })
})
