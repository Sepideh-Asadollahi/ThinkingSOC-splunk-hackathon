import * as React from "react"
import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { AppShell } from "./app-shell"

vi.mock("next/navigation", () => ({
  usePathname: () => "/inventory",
}))

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode
    href: string
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}))

vi.mock("@/components/animate-ui/components/animate/tooltip", () => ({
  TooltipProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock("@/components/animate-ui/components/radix/sidebar", () => ({
  SidebarProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  SidebarInset: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  SidebarTrigger: () => <button type="button">Menu</button>,
}))

vi.mock("@/components/app-sidebar", () => ({
  AppSidebar: () => <aside data-testid="sidebar" />,
}))

vi.mock("@/components/neon-glass", () => ({
  NeonPageShell: ({
    header,
    children,
  }: {
    header?: React.ReactNode
    children: React.ReactNode
  }) => (
    <div>
      {header}
      {children}
    </div>
  ),
}))

describe("AppShell", () => {
  it("shows breadcrumb label for current route", () => {
    render(
      <AppShell>
        <p>Page content</p>
      </AppShell>
    )
    expect(screen.getByRole("navigation", { name: "Breadcrumb" })).toBeInTheDocument()
    expect(screen.getByText("Asset and Identity Management")).toBeInTheDocument()
    expect(screen.getByText("Inventory")).toBeInTheDocument()
    expect(screen.getByText("Page content")).toBeInTheDocument()
  })

  it("uses soft header border and inset highlight", () => {
    const { container } = render(
      <AppShell>
        <p>child</p>
      </AppShell>
    )
    const header = container.querySelector("header") as HTMLElement
    expect(header.className).toContain("border-white/[0.06]")
    expect(header.className).toContain("shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)]")
  })
})
