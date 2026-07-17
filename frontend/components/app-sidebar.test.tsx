import { describe, expect, it } from "vitest"

import { APP_SIDEBAR_DATA } from "./app-sidebar"
import { isPathActive } from "./nav-main"

describe("AppSidebar navigation", () => {
  it("exposes the library and Forge settings under Runbooks", () => {
    expect(APP_SIDEBAR_DATA.navRunbooks).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ title: "Runbook Library", url: "/runbooks/library" }),
        expect.objectContaining({ title: "Shadow & Evaluation", url: "/runbooks/evaluation" }),
        expect.objectContaining({ title: "Forge & Policies", url: "/runbooks", exact: true }),
      ])
    )
  })

  it("does not select Forge & Policies while a Runbook child page is active", () => {
    expect(isPathActive("/runbooks/library", "/runbooks", true)).toBe(false)
    expect(isPathActive("/runbooks/evaluation", "/runbooks", true)).toBe(false)
    expect(isPathActive("/runbooks", "/runbooks", true)).toBe(true)
    expect(isPathActive("/runbooks/library", "/runbooks/library")).toBe(true)
  })
})
