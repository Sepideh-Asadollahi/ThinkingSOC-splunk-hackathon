"use client"

import * as React from "react"

import {
  tsocNativeScrollbarClasses,
  tsocOverflowAutoClasses,
  tsocOverflowYAutoClasses,
  tsocTableScrollInnerStyle,
  tsocTableScrollOuterStyle,
} from "@/lib/ui-scroll"
import { cn } from "@/lib/utils"

type TsocHorizontalScrollProps = {
  children: React.ReactNode
  className?: string
  innerClassName?: string
  minWidth?: number
}

/** Horizontal table/content scroll — ui-standard §5 (grid + maxWidth + overflow-x-auto). */
export function TsocHorizontalScroll({
  children,
  className,
  innerClassName,
  minWidth = 800,
}: TsocHorizontalScrollProps) {
  return (
    <div className={cn("grid w-full min-w-0", className)} style={tsocTableScrollOuterStyle}>
      <div
        className={cn("w-full overflow-x-auto", tsocNativeScrollbarClasses, innerClassName)}
        style={tsocTableScrollInnerStyle}
      >
        <div style={{ minWidth }}>{children}</div>
      </div>
    </div>
  )
}

type TsocOverflowScrollProps = {
  children: React.ReactNode
  className?: string
  axis?: "y" | "both"
  maxHeight?: string | number
}

/** Vertical or both-axis native scroll with standard thumb styling. */
export function TsocOverflowScroll({
  children,
  className,
  axis = "y",
  maxHeight,
}: TsocOverflowScrollProps) {
  const scrollClasses = axis === "both" ? tsocOverflowAutoClasses : tsocOverflowYAutoClasses
  return (
    <div
      className={cn(scrollClasses, className)}
      style={maxHeight !== undefined ? { maxHeight } : undefined}
    >
      {children}
    </div>
  )
}
