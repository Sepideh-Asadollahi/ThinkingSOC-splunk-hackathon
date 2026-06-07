"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"

import { TooltipProvider } from "@/components/animate-ui/components/animate/tooltip"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/animate-ui/components/radix/sidebar"
import { AppSidebar } from "@/components/app-sidebar"
import { NeonPageShell } from "@/components/neon-glass"
import { getBreadcrumbsFromPathname } from "@/lib/navigation-labels"

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const breadcrumbs = getBreadcrumbsFromPathname(pathname)
  return (
    <TooltipProvider>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <div className="flex h-screen min-w-0 flex-col">
            <NeonPageShell
              header={
                <header className="flex h-16 shrink-0 flex-wrap items-center gap-2 border-b border-white/[0.06] bg-[#050505] shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)] px-4">
                  <SidebarTrigger className="-ml-1" />
                  <div
                    role="separator"
                    aria-orientation="vertical"
                    className="mr-2 h-4 w-px shrink-0 bg-white/10"
                  />
                  <nav aria-label="Breadcrumb">
                    <ol className="flex flex-wrap items-center gap-1.5 text-sm text-slate-400">
                      {breadcrumbs.map((crumb, index) => {
                        const isLast = index === breadcrumbs.length - 1
                        return (
                          <li key={`${crumb.label}-${index}`} className="flex items-center gap-1.5">
                            {index > 0 ? (
                              <span aria-hidden className="text-slate-600">
                                /
                              </span>
                            ) : null}
                            {crumb.href && !isLast ? (
                              <Link
                                href={crumb.href}
                                className="transition-colors hover:text-white"
                              >
                                {crumb.label}
                              </Link>
                            ) : (
                              <span
                                className={
                                  isLast ? "font-medium text-white" : "text-slate-400"
                                }
                              >
                                {crumb.label}
                              </span>
                            )}
                          </li>
                        )
                      })}
                    </ol>
                  </nav>
                </header>
              }
            >
              <div className="neon-ambient-top" aria-hidden />
              <div className="neon-ambient-bottom" aria-hidden />
              {children}
            </NeonPageShell>
          </div>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  )
}
