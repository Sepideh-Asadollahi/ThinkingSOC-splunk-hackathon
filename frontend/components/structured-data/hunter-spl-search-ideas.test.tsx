import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { HunterSplSearchIdeasPanel, HunterSplSearchIdeasSection } from "./hunter-spl-search-ideas"

describe("HunterSplSearchIdeas", () => {
  it("renders full-width SPL list", () => {
    render(
      <HunterSplSearchIdeasSection
        suggestions={[
          'index=wineventlog EventCode=4624 user="admin"',
          "index=firewall dest_port=445",
        ]}
      />
    )

    const section = screen.getByTestId("hunter-spl-search-ideas-section")
    expect(section.children[1]).toHaveClass("w-full", "min-w-0")
    expect(screen.getByTestId("hunter-spl-search-ideas")).toBeInTheDocument()
    expect(screen.getByText(/wineventlog/)).toBeInTheDocument()
  })

  it("returns null when suggestions are empty", () => {
    const { container } = render(<HunterSplSearchIdeasPanel suggestions={[]} />)
    expect(container.firstChild).toBeNull()
  })
})
