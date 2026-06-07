import { describe, expect, it } from "vitest"

import { groupFrameworkMapping, isKillChainFramework, isMitreFramework } from "./framework-mapping"

describe("framework-mapping", () => {
  it("detects framework labels", () => {
    expect(isMitreFramework("MITRE ATT&CK")).toBe(true)
    expect(isKillChainFramework("Cyber Kill Chain")).toBe(true)
  })

  it("groups MITRE and Kill Chain separately", () => {
    const grouped = groupFrameworkMapping([
      { framework: "MITRE ATT&CK", id: "T1078", name: "Valid Accounts" },
      { framework: "Cyber Kill Chain", id: "KC-4", name: "Exploitation" },
    ])
    expect(grouped.mitre).toHaveLength(1)
    expect(grouped.killChain).toHaveLength(1)
    expect(grouped.other).toHaveLength(0)
  })
})
