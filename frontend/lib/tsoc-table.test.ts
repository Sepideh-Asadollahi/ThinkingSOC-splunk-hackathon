/**
 * @vitest-environment node
 */
import { describe, expect, it } from "vitest"

import { compareValues, pageCount, paginateSlice, showingRange } from "./tsoc-table"

describe("compareValues", () => {
  it("orders numbers ascending", () => {
    expect(compareValues(1, 5)).toBeLessThan(0)
    expect(compareValues(5, 1)).toBeGreaterThan(0)
    expect(compareValues(3, 3)).toBe(0)
  })

  it("orders strings with numeric locale", () => {
    expect(compareValues("item-2", "item-10")).toBeLessThan(0)
  })

  it("places null and undefined last", () => {
    expect(compareValues(null, "a")).toBeGreaterThan(0)
    expect(compareValues(undefined, null)).toBe(0)
    expect(compareValues("a", null)).toBeLessThan(0)
  })
})

describe("paginateSlice", () => {
  it("returns page window", () => {
    const rows = [1, 2, 3, 4, 5]
    expect(paginateSlice(rows, 0, 2)).toEqual([1, 2])
    expect(paginateSlice(rows, 1, 2)).toEqual([3, 4])
    expect(paginateSlice(rows, 2, 2)).toEqual([5])
  })

  it("returns empty slice beyond range", () => {
    expect(paginateSlice([1, 2], 5, 10)).toEqual([])
  })
})

describe("pageCount", () => {
  it("returns at least one page", () => {
    expect(pageCount(0, 10)).toBe(1)
    expect(pageCount(25, 10)).toBe(3)
    expect(pageCount(20, 10)).toBe(2)
  })
})

describe("showingRange", () => {
  it("computes human-readable range", () => {
    expect(showingRange(25, 0, 10)).toEqual({ start: 1, end: 10 })
    expect(showingRange(25, 1, 10)).toEqual({ start: 11, end: 20 })
    expect(showingRange(25, 2, 10)).toEqual({ start: 21, end: 25 })
  })

  it("returns zeros when total is empty", () => {
    expect(showingRange(0, 0, 10)).toEqual({ start: 0, end: 0 })
  })
})
