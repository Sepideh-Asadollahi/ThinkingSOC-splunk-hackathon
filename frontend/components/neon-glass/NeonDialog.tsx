"use client"

import * as React from "react"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/animate-ui/components/radix/dialog"
import { cn } from "@/lib/utils"

import { getAccentClasses, type NeonAccent } from "./accent"
import { NeonActionButton } from "./NeonActionButton"

type NeonDialogContentProps = React.ComponentProps<typeof DialogContent> & {
  accent?: NeonAccent
  variant?: "default" | "danger"
}

export function NeonDialogContent({
  accent = "teal",
  variant = "default",
  className,
  children,
  ...props
}: NeonDialogContentProps) {
  const a = getAccentClasses(variant === "danger" ? "orange" : accent)
  const frame =
    variant === "danger"
      ? "border-red-500/20 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.06),0_0_0_1px_rgba(255,255,255,0.04),0_12px_40px_-16px_rgba(239,68,68,0.1)]"
      : cn(a.panelBorder, a.panelGlow)
  return (
    <DialogContent
      className={cn(
        "relative overflow-hidden border bg-[#09090b] text-white sm:max-w-lg",
        frame,
        className
      )}
      {...props}
    >
      {variant !== "danger" ? (
        <div
          className={cn(
            "pointer-events-none absolute inset-0 rounded-[inherit] bg-gradient-to-br opacity-45",
            a.panelBorderGradient
          )}
          aria-hidden
        />
      ) : null}
      <div className="relative">{children}</div>
    </DialogContent>
  )
}

type NeonDialogHeaderWithIconProps = {
  accent?: NeonAccent
  variant?: "default" | "danger"
  icon?: React.ReactNode
  title: string
  description?: string
}

export function NeonDialogHeaderWithIcon({
  accent = "teal",
  variant = "default",
  icon,
  title,
  description,
}: NeonDialogHeaderWithIconProps) {
  const a = getAccentClasses(variant === "danger" ? "orange" : accent)
  return (
    <DialogHeader>
      <DialogTitle className="inline-flex flex-row flex-nowrap items-center gap-3">
        {icon ? <span className={a.iconBox}>{icon}</span> : null}
        <span className={a.gradientTitle}>{title}</span>
      </DialogTitle>
      {description ? (
        <DialogDescription className="text-slate-400">{description}</DialogDescription>
      ) : null}
    </DialogHeader>
  )
}

type NeonDialogFooterButtonProps = React.ComponentProps<typeof NeonActionButton> & {
  footerVariant?: "primary" | "secondary"
}

export function NeonDialogFooterButton({
  footerVariant = "primary",
  accent = "teal",
  ...props
}: NeonDialogFooterButtonProps) {
  if (footerVariant === "secondary") {
    return (
      <NeonActionButton
        accent={accent}
        className="border-white/15 text-slate-300"
        {...props}
      />
    )
  }
  return <NeonActionButton accent={accent} {...props} />
}

export { Dialog, DialogFooter as NeonDialogFooter }
