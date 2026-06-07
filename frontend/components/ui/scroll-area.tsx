"use client"

import * as React from "react"
import { ScrollArea as ScrollAreaPrimitive } from "radix-ui"

import { cn } from "@/lib/utils"

type ScrollAreaProps = React.ComponentProps<typeof ScrollAreaPrimitive.Root> & {
  /** Hide scrollbars until pointer hovers (sidebar nav — ui-standard scroll §7). */
  scrollbarOnHover?: boolean
}

function ScrollArea({
  className,
  children,
  scrollbarOnHover = false,
  ...props
}: ScrollAreaProps) {
  const [hovered, setHovered] = React.useState(false)

  return (
    <ScrollAreaPrimitive.Root
      data-slot="scroll-area"
      className={cn("relative", className)}
      onMouseEnter={() => scrollbarOnHover && setHovered(true)}
      onMouseLeave={() => scrollbarOnHover && setHovered(false)}
      {...props}
    >
      <ScrollAreaPrimitive.Viewport
        data-slot="scroll-area-viewport"
        className={cn(
          "no-scrollbar size-full overflow-auto rounded-[inherit] transition-[color,box-shadow] outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-1"
        )}
      >
        {children}
      </ScrollAreaPrimitive.Viewport>
      <ScrollBar orientation="vertical" showOnHover={scrollbarOnHover} hovered={hovered} />
      <ScrollBar orientation="horizontal" showOnHover={scrollbarOnHover} hovered={hovered} />
      <ScrollAreaPrimitive.Corner className="z-10 bg-white/10" />
    </ScrollAreaPrimitive.Root>
  )
}

type ScrollBarProps = React.ComponentProps<typeof ScrollAreaPrimitive.ScrollAreaScrollbar> & {
  showOnHover?: boolean
  hovered?: boolean
}

function ScrollBar({
  className,
  orientation = "vertical",
  showOnHover = false,
  hovered = false,
  ...props
}: ScrollBarProps) {
  const visible = !showOnHover || hovered

  return (
    <ScrollAreaPrimitive.ScrollAreaScrollbar
      data-slot="scroll-area-scrollbar"
      data-orientation={orientation}
      orientation={orientation}
      className={cn(
        "z-10 flex shrink-0 touch-none select-none p-px transition-[opacity,width,height] duration-200",
        "data-horizontal:h-2.5 data-horizontal:flex-col data-horizontal:border-t data-horizontal:border-t-transparent",
        "data-vertical:h-full data-vertical:w-2.5 data-vertical:border-l data-vertical:border-l-transparent",
        showOnHover && !visible && "pointer-events-none opacity-0",
        showOnHover && !visible && orientation === "vertical" && "w-0",
        showOnHover && !visible && orientation === "horizontal" && "h-0",
        showOnHover && visible && "opacity-100",
        className
      )}
      {...props}
    >
      <ScrollAreaPrimitive.ScrollAreaThumb
        data-slot="scroll-area-thumb"
        className="relative flex-1 rounded-full bg-white/15 transition-colors hover:bg-white/25"
      />
    </ScrollAreaPrimitive.ScrollAreaScrollbar>
  )
}

export { ScrollArea, ScrollBar }
