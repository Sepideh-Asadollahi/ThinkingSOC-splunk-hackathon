import { describe, expect, it } from "vitest"

import { getAccentClasses, type NeonAccent } from "./accent"

const ACCENTS: NeonAccent[] = ["teal", "violet", "orange"]

describe("getAccentClasses", () => {
  it("defaults to teal", () => {
    expect(getAccentClasses().text).toBe("text-teal-400")
  })

  it.each(ACCENTS)("returns panel tokens for %s accent", (accent) => {
    const classes = getAccentClasses(accent)
    expect(classes.panelBorder).toBe("border-white/[0.07]")
    expect(classes.panelDivider).toBe("border-b border-white/[0.06]")
    expect(classes.panelGlow).toContain("inset_0_1px_0_0_rgba(255,255,255,0.06)")
    expect(classes.panelBorderGradient).toMatch(/^from-white\/\[0\.1\] via-/)
    expect(classes.gradientFromOverlay).toBe(`from-${accent}-500/[22.5%]`)
  })

  it("uses distinct glow colors per accent", () => {
    expect(getAccentClasses("teal").panelGlow).toContain("rgba(20,184,166")
    expect(getAccentClasses("violet").panelGlow).toContain("rgba(139,92,246")
    expect(getAccentClasses("orange").panelGlow).toContain("rgba(249,115,22")
  })
})
