import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { getAccentClasses } from "./accent"
import { NeonTable, NeonTableFrame, NeonTableHeader, NeonTableRow } from "./NeonTable"

describe("NeonTableFrame", () => {
  it("wraps children with panel border glow", () => {
    const { container } = render(
      <NeonTableFrame>
        <NeonTable>
          <tbody>
            <tr>
              <td>cell</td>
            </tr>
          </tbody>
        </NeonTable>
      </NeonTableFrame>
    )
    const frame = container.firstElementChild as HTMLElement
    const teal = getAccentClasses("teal")
    expect(frame.className).toContain(teal.panelBorder)
    expect(frame.className).toContain(teal.panelGlow)
    expect(screen.getByText("cell")).toBeInTheDocument()
  })

  it("renders gradient border overlay", () => {
    const { container } = render(
      <NeonTableFrame accent="orange">
        <span>table</span>
      </NeonTableFrame>
    )
    const overlay = container.querySelector("[aria-hidden]")
    expect(overlay?.className).toContain("opacity-35")
    expect(overlay?.className).toContain("via-orange-400/[0.06]")
  })
})

describe("NeonTable primitives", () => {
  it("uses softer row borders", () => {
    const { container } = render(
      <table>
        <NeonTableHeader>
          <tr>
            <th>H</th>
          </tr>
        </NeonTableHeader>
        <tbody>
          <NeonTableRow>
            <td>Row</td>
          </NeonTableRow>
        </tbody>
      </table>
    )
    const thead = container.querySelector("thead")!
    const row = container.querySelector("tbody tr")!
    expect(thead.className).toContain("border-white/[0.06]")
    expect(row.className).toContain("border-white/[0.06]")
  })
})
