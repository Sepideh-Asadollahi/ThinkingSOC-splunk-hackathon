"use client"

import * as React from "react"
import { motion } from "motion/react"

import { cn } from "@/lib/utils"

import { getAccentClasses, type NeonAccent } from "./accent"

type NeonActionButtonProps = React.ComponentProps<typeof motion.button> & {
  accent?: NeonAccent
  loading?: boolean
  size?: "default" | "sm"
}

export function NeonActionButton({
  accent = "teal",
  className,
  loading,
  children,
  disabled,
  type = "button",
  size = "default",
  ...props
}: NeonActionButtonProps) {
  const a = getAccentClasses(accent)
  return (
    <motion.button
      type={type}
      whileTap={{ scale: 0.95 }}
      whileHover={{ scale: 1.05 }}
      className={cn(
        "inline-flex cursor-pointer items-center justify-center gap-1.5 rounded-md border bg-transparent text-sm font-medium transition-all disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" ? "h-8 px-2" : "px-3 py-2",
        a.buttonOutline,
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {children}
    </motion.button>
  )
}
