"use client"

import * as React from "react"

import { cn } from "@/lib/utils"

export function NeonFieldGroup({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return <div className={cn("flex flex-col gap-4", className)} {...props} />
}

export function NeonField({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return <div className={cn("flex flex-col gap-2", className)} {...props} />
}

export function NeonFieldLabel({
  className,
  ...props
}: React.ComponentProps<"label">) {
  return (
    <label className={cn("text-sm font-medium text-slate-300", className)} {...props} />
  )
}
