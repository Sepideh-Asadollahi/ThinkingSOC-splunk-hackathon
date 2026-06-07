import { describe, expect, it } from "vitest"

import { isTruncated, truncateLabel } from "@/components/correlation/explorer/graph-canvas-tooltip"

describe("graph canvas tooltip helpers", () => {
  it("truncates long labels", () => {
    const full = "Sysmon: PowerShell Download Activity (t8372)"
    expect(truncateLabel(full, 28).endsWith("…")).toBe(true)
    expect(isTruncated(full, 28)).toBe(true)
  })

  it("does not truncate short labels", () => {
    expect(truncateLabel("RDP", 28)).toBe("RDP")
    expect(isTruncated("RDP", 28)).toBe(false)
  })
})
