"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { ChevronRightIcon } from "lucide-react"

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  useSidebar,
} from "@/components/animate-ui/components/radix/sidebar"
import { flattenNavItemsForIconRail } from "@/lib/sidebar-nav"

export type NavMainItem = {
  title: string
  url: string
  icon?: React.ReactNode
  isActive?: boolean
  items?: { title: string; url: string; icon?: React.ReactNode }[]
}

function isPathActive(pathname: string, url: string) {
  return pathname === url || pathname.startsWith(`${url}/`)
}

function itemHasActiveChild(pathname: string, item: NavMainItem) {
  if (isPathActive(pathname, item.url)) return true
  return item.items?.some((sub) => isPathActive(pathname, sub.url)) ?? false
}

function NavIconRail({
  items,
  pathname,
}: {
  items: ReturnType<typeof flattenNavItemsForIconRail>
  pathname: string
}) {
  return (
    <SidebarMenu className="gap-1 px-0">
      {items.map((item) => (
        <SidebarMenuItem key={item.url} className="flex w-full justify-center">
          <SidebarMenuButton
            asChild
            isActive={isPathActive(pathname, item.url)}
            tooltip={item.title}
            className="mx-auto size-8! p-0!"
          >
            <Link
              href={item.url}
              aria-label={item.title}
              className="flex size-8 items-center justify-center text-sidebar-foreground [&>svg]:size-4"
            >
              {item.icon}
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
      ))}
    </SidebarMenu>
  )
}

export function NavMain({
  items,
  label = "Platform",
}: {
  items: NavMainItem[]
  label?: string
}) {
  const pathname = usePathname()
  const { state } = useSidebar()

  if (state === "collapsed") {
    return (
      <SidebarGroup className="p-0">
        <NavIconRail items={flattenNavItemsForIconRail(items)} pathname={pathname} />
      </SidebarGroup>
    )
  }

  return (
    <SidebarGroup>
      <SidebarGroupLabel>{label}</SidebarGroupLabel>
      <SidebarMenu>
        {items.map((item) => {
          const hasSub = Boolean(item.items?.length)
          const open = item.isActive ?? itemHasActiveChild(pathname, item)

          if (!hasSub) {
            return (
              <SidebarMenuItem key={item.title}>
                <SidebarMenuButton
                  asChild
                  isActive={isPathActive(pathname, item.url)}
                  tooltip={item.title}
                >
                  <Link
                    href={item.url}
                    className="flex w-full min-w-0 items-center gap-2 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:gap-0"
                  >
                    <span className="flex size-4 shrink-0 items-center justify-center [&>svg]:size-4">
                      {item.icon}
                    </span>
                    <span className="truncate group-data-[collapsible=icon]:hidden">
                      {item.title}
                    </span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            )
          }

          return (
            <Collapsible
              key={item.title}
              asChild
              defaultOpen={open}
              className="group/collapsible"
            >
              <SidebarMenuItem>
                <CollapsibleTrigger asChild>
                  <SidebarMenuButton
                    tooltip={item.title}
                    className="group-data-[collapsible=icon]:justify-center"
                  >
                    <span className="flex size-4 shrink-0 items-center justify-center [&>svg]:size-4">
                      {item.icon}
                    </span>
                    <span className="truncate group-data-[collapsible=icon]:hidden">
                      {item.title}
                    </span>
                    <ChevronRightIcon className="ml-auto size-4 shrink-0 transition-transform duration-200 group-data-[collapsible=icon]:hidden group-data-[state=open]/collapsible:rotate-90" />
                  </SidebarMenuButton>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <SidebarMenuSub>
                    {item.items!.map((subItem) => (
                      <SidebarMenuSubItem key={subItem.title}>
                        <SidebarMenuSubButton
                          asChild
                          isActive={isPathActive(pathname, subItem.url)}
                        >
                          <Link href={subItem.url}>
                            <span>{subItem.title}</span>
                          </Link>
                        </SidebarMenuSubButton>
                      </SidebarMenuSubItem>
                    ))}
                  </SidebarMenuSub>
                </CollapsibleContent>
              </SidebarMenuItem>
            </Collapsible>
          )
        })}
      </SidebarMenu>
    </SidebarGroup>
  )
}
