import { describe, expect, it } from "vitest"

import {
  alertNodeTier,
  hexagonPath,
} from "@/components/correlation/explorer/graph-alert-node-mark"

describe("graph alert node mark", () => {
  it("maps risk to tiers", () => {
    expect(alertNodeTier(78)).toBe("critical")
    expect(alertNodeTier(55)).toBe("elevated")
    expect(alertNodeTier(30)).toBe("low")
  })

  it("builds a closed hex path", () => {
    expect(hexagonPath(10)).toMatch(/^M .+ Z$/)
  })
})
