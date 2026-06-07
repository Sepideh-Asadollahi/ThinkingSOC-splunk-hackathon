import { cn } from "@/lib/utils"

/** Native overflow regions — thin dark-theme thumb (Firefox + WebKit). */
export const tsocNativeScrollbarClasses = cn(
  "tsoc-scrollbar",
  "[&::-webkit-scrollbar]:w-2",
  "[&::-webkit-scrollbar]:h-2",
  "[&::-webkit-scrollbar-track]:bg-transparent",
  "[&::-webkit-scrollbar-thumb]:rounded-full",
  "[&::-webkit-scrollbar-thumb]:bg-white/15",
  "[&::-webkit-scrollbar-thumb:hover]:bg-white/25",
  "[&::-webkit-scrollbar-button]:hidden",
  "[&::-webkit-scrollbar-corner]:bg-transparent"
)

export const tsocOverflowYAutoClasses = cn(
  "overflow-y-auto overflow-x-hidden",
  tsocNativeScrollbarClasses
)

export const tsocOverflowAutoClasses = cn("overflow-auto", tsocNativeScrollbarClasses)

import type { CSSProperties } from "react"

export const tsocTableScrollOuterStyle: CSSProperties = {
  maxWidth: "calc(100vw - 2rem)",
  width: "100%",
}

export const tsocTableScrollInnerStyle: CSSProperties = {
  width: "100%",
  maxWidth: "100%",
  WebkitOverflowScrolling: "touch",
}
