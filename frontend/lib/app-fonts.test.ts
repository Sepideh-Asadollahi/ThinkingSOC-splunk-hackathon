import { describe, expect, it } from "vitest"

import {
  APP_MONO_FONT_VARIABLE,
  APP_SANS_FONT_VARIABLE,
  LAYOUT_FONT_CLASS_NAMES,
} from "./app-fonts"

describe("app-fonts", () => {
  it("documents Inter and JetBrains Mono CSS variables used in layout", () => {
    expect(APP_SANS_FONT_VARIABLE).toBe("--font-inter")
    expect(APP_MONO_FONT_VARIABLE).toBe("--font-mono-family")
  })

  it("documents layout html font utility classes", () => {
    expect(LAYOUT_FONT_CLASS_NAMES).toContain("font-sans")
    expect(LAYOUT_FONT_CLASS_NAMES).toContain("antialiased")
  })
})
