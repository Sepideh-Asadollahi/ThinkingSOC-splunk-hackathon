import { describe, expect, it } from "vitest"

import { APP_SIDEBAR_DATA } from "./app-sidebar"
import { isPathActive } from "./nav-main"

describe("AppSidebar navigation", () => {
  it("exposes the library and ThinkingSOC Lite settings under Runbooks", () => {
    expect(APP_SIDEBAR_DATA.navRunbooks).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ title: "Runbook Library", url: "/runbooks/library" }),
        expect.objectContaining({ title: "Shadow & Evaluation", url: "/runbooks/evaluation" }),
        expect.objectContaining({ title: "ThinkingSOC Lite", url: "/runbooks", exact: true }),
      ])
    )
  })

  it("does not select ThinkingSOC Lite while a Runbook child page is active", () => {
    expect(isPathActive("/runbooks/library", "/runbooks", true)).toBe(false)
    expect(isPathActive("/runbooks/evaluation", "/runbooks", true)).toBe(false)
    expect(isPathActive("/runbooks", "/runbooks", true)).toBe(true)
    expect(isPathActive("/runbooks/library", "/runbooks/library")).toBe(true)
  })
})
