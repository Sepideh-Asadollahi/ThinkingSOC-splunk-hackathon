import { describe, expect, it } from "vitest"

import {
  getBreadcrumbsFromPathname,
  getPageLabelFromPathname,
  PAGE_LABELS,
} from "./navigation-labels"

describe("getPageLabelFromPathname", () => {
  it.each(Object.entries(PAGE_LABELS))("maps /%s leaf label to %s", (segment, label) => {
    expect(getPageLabelFromPathname(`/${segment}`)).toBe(label)
    expect(getPageLabelFromPathname(`/${segment}/extra`)).toBe(label)
  })

  it("defaults empty path to Overview", () => {
    expect(getPageLabelFromPathname("/")).toBe("Overview")
    expect(getPageLabelFromPathname("")).toBe("Overview")
  })

  it("falls back to raw segment for unknown routes", () => {
    expect(getPageLabelFromPathname("/unknown-page")).toBe("unknown-page")
  })

  it("maps graph explorer to Graph Explorer", () => {
    expect(getPageLabelFromPathname("/correlation/explorer")).toBe("Graph Explorer")
  })
})

describe("getBreadcrumbsFromPathname", () => {
  it("shows Dashboard section and Overview page", () => {
    expect(getBreadcrumbsFromPathname("/dashboard")).toEqual([
      { label: "Dashboard", href: "/dashboard" },
      { label: "Overview" },
    ])
  })

  it("shows AI Assistant section and Chat page", () => {
    expect(getBreadcrumbsFromPathname("/soc-chat")).toEqual([
      { label: "AI Assistant", href: "/soc-chat" },
      { label: "Chat" },
    ])
  })

  it("shows Services section for analysis and correlation", () => {
    expect(getBreadcrumbsFromPathname("/analysis")).toEqual([
      { label: "Services", href: "/analysis" },
      { label: "Analysis" },
    ])
    expect(getBreadcrumbsFromPathname("/correlation")).toEqual([
      { label: "Services", href: "/correlation" },
      { label: "Correlation" },
    ])
  })

  it("shows graph explorer trail under Services", () => {
    expect(getBreadcrumbsFromPathname("/correlation/explorer")).toEqual([
      { label: "Services", href: "/correlation" },
      { label: "Correlation", href: "/correlation" },
      { label: "Graph Explorer" },
    ])
  })

  it("shows asset and settings sections", () => {
    expect(getBreadcrumbsFromPathname("/inventory")[0]?.label).toBe(
      "Asset and Identity Management",
    )
    expect(getBreadcrumbsFromPathname("/splunk-connection")[0]?.label).toBe("Settings")
  })
})
