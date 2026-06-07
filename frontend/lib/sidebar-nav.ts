import type { ReactNode } from "react"

import type { NavMainItem } from "@/components/nav-main"

export type SidebarIconNavItem = {
  title: string
  url: string
  icon?: ReactNode
}

/** One icon per route for collapsed (icon-only) sidebar rail. */
export function flattenNavItemsForIconRail(items: NavMainItem[]): SidebarIconNavItem[] {
  const flat: SidebarIconNavItem[] = []
  for (const item of items) {
    if (item.items?.length) {
      for (const sub of item.items) {
        flat.push({
          title: sub.title,
          url: sub.url,
          icon: sub.icon ?? item.icon,
        })
      }
      continue
    }
    flat.push({
      title: item.title,
      url: item.url,
      icon: item.icon,
    })
  }
  return flat
}
