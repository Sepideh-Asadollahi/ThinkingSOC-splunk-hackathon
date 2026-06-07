"use client"

import * as React from "react"

import { PAGE_ENTER_CLASSES } from "@/lib/page-enter"
import { cn } from "@/lib/utils"

import { getAccentClasses, type NeonAccent } from "./accent"

type NeonGlassCardProps = React.ComponentProps<"div"> & {
  accent?: NeonAccent
  animatePreset?: "page" | "none"
}

export function NeonGlassCard({
  accent = "teal",
  animatePreset = "none",
  className,
  children,
  ...props
}: NeonGlassCardProps) {
  const a = getAccentClasses(accent)

  return (
    <div
      className={cn(
        "relative min-w-0 overflow-hidden rounded-xl border bg-black/40 backdrop-blur-md",
        a.panelBorder,
        a.panelGlow,
        animatePreset === "page" && PAGE_ENTER_CLASSES,
        className?.includes("h-full") && "h-full"
      )}
      {...props}
    >
      <div
        className={cn(
          "pointer-events-none absolute inset-0 rounded-[inherit] bg-gradient-to-br opacity-40",
          a.panelBorderGradient
        )}
        aria-hidden
      />
      <div className={cn("relative min-h-0", className)}>{children}</div>
    </div>
  )
}

type NeonCardHeaderProps = {
  accent?: NeonAccent
  icon?: React.ReactNode
  title: string
  description?: string
  actions?: React.ReactNode
  className?: string
}

export function NeonCardHeader({
  accent = "teal",
  icon,
  title,
  description,
  actions,
  className,
}: NeonCardHeaderProps) {
  const a = getAccentClasses(accent)

  return (
    <div
      className={cn(
        "flex flex-wrap items-start justify-between gap-3 px-6 py-4",
        a.panelDivider,
        className
      )}
    >
      <div className="flex min-w-0 items-start gap-3">
        {icon ? <div className={a.iconBox}>{icon}</div> : null}
        <div className="min-w-0 space-y-1">
          <h2 className={cn("text-lg font-semibold tracking-tight", a.gradientTitle)}>
            {title}
          </h2>
          {description ? (
            <p className="text-sm text-slate-400">{description}</p>
          ) : null}
        </div>
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  )
}
