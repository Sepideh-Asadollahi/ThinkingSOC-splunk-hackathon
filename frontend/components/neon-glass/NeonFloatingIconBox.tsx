"use client"

import * as React from "react"

import { cn } from "@/lib/utils"

import { getAccentClasses, type NeonAccent } from "./accent"

type NeonFloatingIconBoxProps = React.ComponentProps<"div"> & {
  accent?: NeonAccent
  animate?: boolean
}

export function NeonFloatingIconBox({
  accent = "teal",
  animate = true,
  className,
  children,
  ...props
}: NeonFloatingIconBoxProps) {
  const a = getAccentClasses(accent)
  return (
    <div
      className={cn(
        a.iconBox,
        "inline-flex items-center justify-center overflow-hidden",
        animate && "animate-float",
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}
