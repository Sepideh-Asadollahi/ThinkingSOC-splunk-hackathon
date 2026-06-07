import { describe, expect, it } from "vitest"

import {
  tsocNativeScrollbarClasses,
  tsocOverflowAutoClasses,
  tsocOverflowYAutoClasses,
  tsocTableScrollInnerStyle,
  tsocTableScrollOuterStyle,
} from "./ui-scroll"

describe("ui-scroll", () => {
  it("defines native scrollbar thumb styling", () => {
    expect(tsocNativeScrollbarClasses).toContain("tsoc-scrollbar")
    expect(tsocNativeScrollbarClasses).toContain("[&::-webkit-scrollbar-thumb]:bg-white/15")
    expect(tsocNativeScrollbarClasses).toContain("[&::-webkit-scrollbar-thumb:hover]:bg-white/25")
  })

  it("composes vertical overflow classes", () => {
    expect(tsocOverflowYAutoClasses).toContain("overflow-y-auto")
    expect(tsocOverflowYAutoClasses).toContain("overflow-x-hidden")
    expect(tsocOverflowYAutoClasses).toContain("[&::-webkit-scrollbar]:w-2")
  })

  it("composes auto overflow classes", () => {
    expect(tsocOverflowAutoClasses).toContain("overflow-auto")
  })

  it("defines table scroll layout styles", () => {
    expect(tsocTableScrollOuterStyle).toEqual({
      maxWidth: "calc(100vw - 2rem)",
      width: "100%",
    })
    expect(tsocTableScrollInnerStyle).toMatchObject({
      width: "100%",
      maxWidth: "100%",
      WebkitOverflowScrolling: "touch",
    })
  })
})
