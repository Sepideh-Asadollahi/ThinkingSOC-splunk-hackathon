import { describe, expect, it } from "vitest"

import { flattenNavItemsForIconRail } from "./sidebar-nav"

describe("flattenNavItemsForIconRail", () => {
  it("flattens submenu routes into one icon each", () => {
    const flat = flattenNavItemsForIconRail([
      {
        title: "Group",
        url: "/dashboard",
        icon: "group-icon",
        items: [
          { title: "Dashboard", url: "/dashboard", icon: "dash-icon" },
          { title: "Inventory", url: "/inventory" },
        ],
      },
      { title: "Splunk", url: "/splunk-connection", icon: "plug-icon" },
    ])

    expect(flat).toHaveLength(3)
    expect(flat[0]).toEqual({
      title: "Dashboard",
      url: "/dashboard",
      icon: "dash-icon",
    })
    expect(flat[1]).toEqual({
      title: "Inventory",
      url: "/inventory",
      icon: "group-icon",
    })
    expect(flat[2]?.url).toBe("/splunk-connection")
  })
})
