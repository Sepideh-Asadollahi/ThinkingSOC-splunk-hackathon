export type BreadcrumbItem = {
  label: string
  href?: string
}

type RouteNavMeta = {
  section: string
  sectionHref: string
  page: string
}

const ROUTE_NAV: Record<string, RouteNavMeta> = {
  dashboard: {
    section: "Dashboard",
    sectionHref: "/dashboard",
    page: "Overview",
  },
  "soc-chat": {
    section: "AI Assistant",
    sectionHref: "/soc-chat",
    page: "Chat",
  },
  analysis: {
    section: "Services",
    sectionHref: "/analysis",
    page: "Analysis",
  },
  correlation: {
    section: "Services",
    sectionHref: "/correlation",
    page: "Correlation",
  },
  runbooks: {
    section: "Runbooks",
    sectionHref: "/runbooks",
    page: "Forge & Policies",
  },
  inventory: {
    section: "Asset and Identity Management",
    sectionHref: "/inventory",
    page: "Inventory",
  },
  relationships: {
    section: "Asset and Identity Management",
    sectionHref: "/relationships",
    page: "Relationships",
  },
  "splunk-connection": {
    section: "Settings",
    sectionHref: "/splunk-connection",
    page: "Splunk & Integrations",
  },
}

/** @deprecated Use getBreadcrumbsFromPathname for header trails. */
export const PAGE_LABELS: Record<string, string> = Object.fromEntries(
  Object.entries(ROUTE_NAV).map(([segment, meta]) => [segment, meta.page]),
)

export function getPageLabelFromPathname(pathname: string): string {
  const crumbs = getBreadcrumbsFromPathname(pathname)
  return crumbs[crumbs.length - 1]?.label ?? "Overview"
}

export function getBreadcrumbsFromPathname(pathname: string): BreadcrumbItem[] {
  const segments = pathname.split("/").filter(Boolean)
  const root = segments[0] ?? "dashboard"

  if (root === "correlation" && segments[1] === "explorer") {
    const meta = ROUTE_NAV.correlation
    return [
      { label: meta.section, href: meta.sectionHref },
      { label: meta.page, href: meta.sectionHref },
      { label: "Graph Explorer" },
    ]
  }

  if (root === "runbooks" && segments[1] === "library") {
    return [
      { label: "Runbooks", href: "/runbooks" },
      { label: "Runbook Library" },
    ]
  }

  if (root === "runbooks" && segments[1] === "evaluation") {
    return [
      { label: "Runbooks", href: "/runbooks" },
      { label: "Shadow & Evaluation" },
    ]
  }

  const meta = ROUTE_NAV[root]
  if (!meta) {
    return [{ label: root }]
  }

  if (meta.section === meta.page) {
    return [{ label: meta.page, href: meta.sectionHref }]
  }

  return [
    { label: meta.section, href: meta.sectionHref },
    { label: meta.page },
  ]
}
