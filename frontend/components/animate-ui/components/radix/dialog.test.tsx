import * as React from "react"
import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/components/animate-ui/primitives/radix/dialog", () => ({
  Dialog: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogPortal: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dialog-portal">{children}</div>
  ),
  DialogOverlay: () => <div data-testid="dialog-overlay" />,
  DialogContent: ({
    children,
    className,
  }: {
    children: React.ReactNode
    className?: string
  }) => (
    <div data-testid="dialog-content-motion" className={className}>
      {children}
    </div>
  ),
  DialogClose: ({ children }: { children: React.ReactNode }) => <button>{children}</button>,
  DialogHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogFooter: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogTitle: ({ children }: { children: React.ReactNode }) => <h2>{children}</h2>,
  DialogDescription: ({ children }: { children: React.ReactNode }) => <p>{children}</p>,
  DialogTrigger: ({ children }: { children: React.ReactNode }) => <button>{children}</button>,
}))

import { Dialog, DialogContent } from "./dialog"

describe("DialogContent positioning", () => {
  it("centers content in viewport via flex wrapper (not document flow)", () => {
    const { container } = render(
      <Dialog open>
        <DialogContent>Modal</DialogContent>
      </Dialog>
    )
    const centerWrapper = container.querySelector(
      ".fixed.inset-0.flex.items-center.justify-center"
    )
    expect(centerWrapper).toBeTruthy()
    expect(screen.getByText("Modal")).toBeInTheDocument()
    expect(centerWrapper?.querySelector("[data-testid='dialog-content-motion']")).toBeTruthy()
  })
})
