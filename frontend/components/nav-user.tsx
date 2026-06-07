"use client"

import { useRouter } from "next/navigation"
import { ChevronsUpDownIcon, LogOutIcon } from "lucide-react"

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/animate-ui/components/radix/dropdown-menu"
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/animate-ui/components/radix/sidebar"
import { cn } from "@/lib/utils"

function UserAvatar({ name, className }: { name: string; className?: string }) {
  const initials =
    name
      .split(/\s+/)
      .map((s) => s[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() || "U"
  return (
    <div
      className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-lg bg-teal-500/20 text-xs font-medium text-teal-300",
        className
      )}
    >
      {initials}
    </div>
  )
}

export function NavUser({
  user,
}: {
  user: {
    name: string
    email: string
    avatar: string
  }
}) {
  const { isMobile, state } = useSidebar()
  const collapsed = state === "collapsed"
  const router = useRouter()

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" })
    router.push("/login")
    router.refresh()
  }

  return (
    <SidebarMenu className={cn(collapsed && "items-center px-0")}>
      <SidebarMenuItem className={cn(collapsed && "flex w-full justify-center")}>
        <DropdownMenu>
          <SidebarMenuButton
            asChild
            size={collapsed ? "default" : "lg"}
            tooltip={user.name}
            className={cn(
              "data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground",
              collapsed && "mx-auto size-8! p-0!"
            )}
          >
            <DropdownMenuTrigger asChild>
              <button type="button">
                <UserAvatar name={user.name} />
                {!collapsed ? (
                  <>
                    <div className="grid min-w-0 flex-1 text-left text-sm leading-tight">
                      <span className="truncate font-medium">{user.name}</span>
                      <span className="truncate text-xs">{user.email}</span>
                    </div>
                    <ChevronsUpDownIcon className="ml-auto size-4 shrink-0" />
                  </>
                ) : null}
              </button>
            </DropdownMenuTrigger>
          </SidebarMenuButton>
          <DropdownMenuContent
            className="w-(--radix-dropdown-menu-trigger-width) min-w-56 rounded-lg"
            side={isMobile ? "bottom" : "right"}
            align={collapsed ? "start" : "end"}
            sideOffset={4}
          >
            <DropdownMenuLabel className="p-0 font-normal">
              <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
                <UserAvatar name={user.name} />
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-medium">{user.name}</span>
                  <span className="truncate text-xs">{user.email}</span>
                </div>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => void logout()}>
              <LogOutIcon />
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
