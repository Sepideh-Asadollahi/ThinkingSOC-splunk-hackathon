import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import {
  tsocTableScrollInnerStyle,
  tsocTableScrollOuterStyle,
} from "@/lib/ui-scroll"

import { TsocHorizontalScroll, TsocOverflowScroll } from "./tsoc-scroll"

describe("TsocHorizontalScroll", () => {
  it("renders grid wrapper with table scroll styles", () => {
    const { container } = render(
      <TsocHorizontalScroll minWidth={640}>
        <table>
          <tbody>
            <tr>
              <td>Wide table</td>
            </tr>
          </tbody>
        </table>
      </TsocHorizontalScroll>
    )
    const outer = container.firstElementChild as HTMLElement
    expect(outer.className).toContain("grid")
    expect(outer.style.maxWidth).toBe(tsocTableScrollOuterStyle.maxWidth as string)
    expect(screen.getByText("Wide table")).toBeInTheDocument()
    const innerMin = container.querySelector("[style*='min-width']") as HTMLElement
    expect(innerMin.style.minWidth).toBe("640px")
  })

  it("applies native scrollbar classes on scroll container", () => {
    const { container } = render(<TsocHorizontalScroll>content</TsocHorizontalScroll>)
    const scroller = container.querySelector(".overflow-x-auto") as HTMLElement
    expect(scroller.className).toContain("[&::-webkit-scrollbar-thumb]:bg-white/15")
    expect(scroller.style.maxWidth).toBe(tsocTableScrollInnerStyle.maxWidth as string)
  })
})

describe("TsocOverflowScroll", () => {
  it("uses vertical scroll by default", () => {
    const { container } = render(<TsocOverflowScroll>scroll me</TsocOverflowScroll>)
    const el = container.firstElementChild as HTMLElement
    expect(el.className).toContain("overflow-y-auto")
    expect(el.className).toContain("overflow-x-hidden")
  })

  it("supports both-axis scroll and maxHeight", () => {
    const { container } = render(
      <TsocOverflowScroll axis="both" maxHeight={400}>
        content
      </TsocOverflowScroll>
    )
    const el = container.firstElementChild as HTMLElement
    expect(el.className).toContain("overflow-auto")
    expect(el.style.maxHeight).toBe("400px")
  })
})
