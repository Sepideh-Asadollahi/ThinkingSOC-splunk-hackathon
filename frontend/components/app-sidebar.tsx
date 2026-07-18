"use client"

import Link from "next/link"
import {
  BookOpenCheckIcon,
  FlaskConicalIcon,
  GitBranchIcon,
  Link2Icon,
  LayoutDashboardIcon,
  LibraryIcon,
  LineChartIcon,
  MessageSquareIcon,
  PackageIcon,
  PlugIcon,
  ShieldIcon,
} from "lucide-react"

import { NavMain } from "@/components/nav-main"
import { NavUser } from "@/components/nav-user"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@/components/animate-ui/components/radix/sidebar"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"

export const APP_SIDEBAR_DATA = {
  user: {
    name: "Admin",
    email: "admin",
    avatar: "",
  },
  navDashboard: [
    {
      title: "Overview",
      url: "/dashboard",
      icon: <LayoutDashboardIcon className="size-4" />,
    },
  ],
  navAIAssistant: [
    {
      title: "Chat",
      url: "/soc-chat",
      icon: <MessageSquareIcon className="size-4" />,
    },
  ],
  navServices: [
    {
      title: "Analysis",
      url: "/analysis",
      icon: <LineChartIcon className="size-4" />,
    },
    {
      title: "Correlation",
      url: "/correlation",
      icon: <GitBranchIcon className="size-4" />,
    },
  ],
  navRunbooks: [
    {
      title: "Runbook Library",
      url: "/runbooks/library",
      icon: <LibraryIcon className="size-4" />,
    },
    {
      title: "Shadow & Evaluation",
      url: "/runbooks/evaluation",
      icon: <FlaskConicalIcon className="size-4" />,
    },
    {
      title: "ThinkingSOC Lite",
      url: "/runbooks",
      exact: true,
      icon: <BookOpenCheckIcon className="size-4" />,
    },
  ],
  navAssetIdentity: [
    {
      title: "Inventory",
      url: "/inventory",
      icon: <PackageIcon className="size-4" />,
    },
    {
      title: "Relationships",
      url: "/relationships",
      icon: <Link2Icon className="size-4" />,
    },
  ],
  navSettings: [
    {
      title: "Splunk & Integrations",
      url: "/splunk-connection",
      icon: <PlugIcon className="size-4" />,
    },
  ],
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { state } = useSidebar()
  const collapsed = state === "collapsed"

  return (
    <Sidebar collapsible="icon" animateOnHover={!collapsed} {...props}>
      {!collapsed ? (
        <SidebarHeader>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton size="lg" asChild>
                <Link href="/dashboard" className="flex min-w-0 items-center gap-2">
                  <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-teal-500/20 text-teal-400">
                    <ShieldIcon className="size-4 shrink-0" />
                  </div>
                  <div className="grid min-w-0 flex-1 text-left text-sm leading-tight">
                    <span className="truncate font-medium">ThinkingSOC Lite</span>
                    <span className="truncate text-xs text-muted-foreground">
                      Hackathon Demo
                    </span>
                  </div>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>
      ) : null}
      <SidebarContent scrollable={false} className="flex flex-col p-0">
        <ScrollArea className="flex-1 min-h-0" scrollbarOnHover>
          <div
            className={cn(
              "flex flex-col",
              collapsed ? "items-center gap-1 px-1 py-2" : "gap-0 p-2"
            )}
          >
            <NavMain items={APP_SIDEBAR_DATA.navDashboard} label="Dashboard" />
            <NavMain items={APP_SIDEBAR_DATA.navAIAssistant} label="AI Assistant" />
            <NavMain items={APP_SIDEBAR_DATA.navServices} label="Services" />
            <NavMain items={APP_SIDEBAR_DATA.navRunbooks} label="Runbooks" />
            <NavMain
              items={APP_SIDEBAR_DATA.navAssetIdentity}
              label="Asset and Identity Management"
            />
            <NavMain items={APP_SIDEBAR_DATA.navSettings} label="Settings" />
          </div>
        </ScrollArea>
      </SidebarContent>
      <SidebarFooter
        className={cn(
          "mt-auto shrink-0 border-t border-sidebar-border",
          collapsed && "items-center px-1"
        )}
      >
        <NavUser user={APP_SIDEBAR_DATA.user} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
