"use client"

import * as React from "react"

import { cn } from "@/lib/utils"

import { getAccentClasses, type NeonAccent } from "./accent"

type NeonTableFrameProps = React.ComponentProps<"div"> & {
  accent?: NeonAccent
}

/** Wraps tables with the same soft panel border/glow as NeonGlassCard. */
export function NeonTableFrame({
  accent = "teal",
  className,
  children,
  ...props
}: NeonTableFrameProps) {
  const a = getAccentClasses(accent)
  return (
    <div
      className={cn(
        "group relative min-w-0 overflow-hidden rounded-lg border bg-black/30 backdrop-blur-sm",
        a.panelBorder,
        a.panelGlow,
        className
      )}
      {...props}
    >
      <div
        className={cn(
          "pointer-events-none absolute inset-0 rounded-[inherit] bg-gradient-to-br opacity-35",
          a.panelBorderGradient
        )}
        aria-hidden
      />
      <div className="relative">{children}</div>
    </div>
  )
}

export function NeonTable({ className, ...props }: React.ComponentProps<"table">) {
  return (
    <table
      className={cn("w-full caption-bottom text-sm text-slate-200", className)}
      {...props}
    />
  )
}

export function NeonTableHeader({
  className,
  ...props
}: React.ComponentProps<"thead">) {
  return <thead className={cn("[&_tr]:border-b border-white/[0.06]", className)} {...props} />
}

export function NeonTableBody({
  className,
  ...props
}: React.ComponentProps<"tbody">) {
  return (
    <tbody className={cn("[&_tr:last-child]:border-0", className)} {...props} />
  )
}

export function NeonTableRow({
  className,
  onClick,
  ...props
}: React.ComponentProps<"tr">) {
  return (
    <tr
      className={cn(
        "border-b border-white/[0.06] transition-colors hover:bg-white/5",
        onClick && "cursor-pointer",
        className
      )}
      onClick={onClick}
      {...props}
    />
  )
}

export function NeonTableHead({
  className,
  ...props
}: React.ComponentProps<"th">) {
  return (
    <th
      className={cn(
        "h-10 px-3 text-left align-middle font-medium text-slate-400",
        className
      )}
      {...props}
    />
  )
}

export function NeonTableCell({
  className,
  ...props
}: React.ComponentProps<"td">) {
  return (
    <td className={cn("py-3 pl-4 pr-3 align-middle", className)} {...props} />
  )
}

export function NeonBadge({
  className,
  ...props
}: React.ComponentProps<"span">) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border border-white/15 px-2 py-0.5 text-xs font-medium",
        className
      )}
      {...props}
    />
  )
}
