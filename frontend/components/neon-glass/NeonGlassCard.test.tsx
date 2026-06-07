import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { getAccentClasses } from "./accent"
import { NeonCardHeader, NeonGlassCard } from "./NeonGlassCard"

describe("NeonGlassCard", () => {
  it("forwards className to the inner content wrapper (data-testid stays on outer shell)", () => {
    render(
      <NeonGlassCard className="w-full min-w-0" data-testid="card">
        <p>Inner</p>
      </NeonGlassCard>
    )
    const outer = screen.getByTestId("card")
    const inner = outer.children[1] as HTMLElement
    expect(inner).toHaveClass("w-full", "min-w-0")
    expect(outer).not.toHaveClass("w-full")
  })

  it("applies soft panel border and glow classes", () => {
    const { container } = render(
      <NeonGlassCard data-testid="card">
        <p>Content</p>
      </NeonGlassCard>
    )
    const root = container.firstElementChild as HTMLElement
    const teal = getAccentClasses("teal")
    expect(root.className).toContain(teal.panelBorder)
    expect(root.className).toContain("shadow-[inset_0_1px_0_0_rgba(255,255,255,0.06)")
    expect(screen.getByText("Content")).toBeInTheDocument()
  })

  it("renders static border gradient overlay only (no hover layer)", () => {
    const { container } = render(<NeonGlassCard>Child</NeonGlassCard>)
    const overlays = container.querySelectorAll("[aria-hidden]")
    expect(overlays).toHaveLength(1)
    expect(overlays[0]?.className).toContain("opacity-40")
    expect(overlays[0]?.className).toContain("from-white/[0.1]")
    expect(overlays[0]?.className).toContain("via-teal-400/[0.06]")
    expect(container.innerHTML).not.toContain("group-hover:opacity-100")
  })

  it("applies page animation preset", () => {
    const { container } = render(
      <NeonGlassCard animatePreset="page">Child</NeonGlassCard>
    )
    expect((container.firstElementChild as HTMLElement).className).toContain("animate-in")
  })

  it("uses violet accent classes when requested", () => {
    const { container } = render(<NeonGlassCard accent="violet">Child</NeonGlassCard>)
    const violet = getAccentClasses("violet")
    expect((container.firstElementChild as HTMLElement).className).toContain(violet.panelGlow)
  })
})

describe("NeonCardHeader", () => {
  it("renders title and soft panel divider", () => {
    const { container } = render(
      <NeonCardHeader title="Inventory" description="Manage assets" />
    )
    expect(screen.getByRole("heading", { name: "Inventory" })).toBeInTheDocument()
    expect(screen.getByText("Manage assets")).toBeInTheDocument()
    expect((container.firstElementChild as HTMLElement).className).toContain(
      "border-b border-white/[0.06]"
    )
  })
})
