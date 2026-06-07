import * as React from "react"
import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

import { getAccentClasses } from "./accent"
import { NeonDialogContent, NeonDialogHeaderWithIcon } from "./NeonDialog"

vi.mock("@/components/animate-ui/components/radix/dialog", () => ({
  Dialog: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogContent: ({
    children,
    className,
    ...props
  }: React.ComponentProps<"div"> & { children: React.ReactNode }) => (
    <div data-testid="dialog-content" className={className} {...props}>
      {children}
    </div>
  ),
  DialogHeader: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dialog-header">{children}</div>
  ),
  DialogTitle: ({ children }: { children: React.ReactNode }) => <h2>{children}</h2>,
  DialogDescription: ({ children }: { children: React.ReactNode }) => (
    <p>{children}</p>
  ),
  DialogFooter: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

afterEach(() => {
  cleanup()
})

describe("NeonDialogContent", () => {
  it("applies panel border glow for default variant", () => {
    render(
      <NeonDialogContent>
        <p>Dialog body</p>
      </NeonDialogContent>
    )
    const dialog = screen.getByTestId("dialog-content")
    const teal = getAccentClasses("teal")
    expect(dialog.className).toContain(teal.panelBorder)
    expect(dialog.className).toContain(teal.panelGlow)
    expect(screen.getByText("Dialog body")).toBeInTheDocument()
  })

  it("renders gradient overlay for default variant", () => {
    const { container } = render(<NeonDialogContent>Body</NeonDialogContent>)
    const overlay = container.querySelector("[aria-hidden]")
    expect(overlay?.className).toContain("opacity-45")
    expect(overlay?.className).toContain("via-teal-400/[0.06]")
  })

  it("uses danger frame without gradient overlay", () => {
    const { container } = render(
      <NeonDialogContent variant="danger">Delete?</NeonDialogContent>
    )
    const dialog = container.querySelector("[data-testid='dialog-content']") as HTMLElement
    expect(dialog.className).toContain("border-red-500/20")
    expect(container.querySelector("[aria-hidden]")).toBeNull()
  })
})

describe("NeonDialogHeaderWithIcon", () => {
  it("renders title with accent gradient", () => {
    render(
      <NeonDialogHeaderWithIcon
        title="Add asset"
        description="Fill in the fields"
        icon={<span data-testid="icon">I</span>}
      />
    )
    expect(screen.getByRole("heading", { name: /Add asset/ })).toBeInTheDocument()
    expect(screen.getByText("Fill in the fields")).toBeInTheDocument()
    expect(screen.getByTestId("icon")).toBeInTheDocument()
  })
})
