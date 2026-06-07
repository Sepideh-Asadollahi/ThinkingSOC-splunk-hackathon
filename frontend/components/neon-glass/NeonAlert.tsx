"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const alertVariants = cva("rounded-lg border px-4 py-3 text-sm", {
  variants: {
    variant: {
      default: "border-white/10 bg-black/40 text-slate-200",
      destructive: "border-red-500/30 bg-red-500/10 text-red-200",
    },
  },
  defaultVariants: { variant: "default" },
})

export function NeonAlert({
  className,
  variant,
  ...props
}: React.ComponentProps<"div"> & VariantProps<typeof alertVariants>) {
  return (
    <div role="alert" className={cn(alertVariants({ variant }), className)} {...props} />
  )
}

export function NeonAlertTitle({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("mb-1 font-medium", className)} {...props} />
}

export function NeonAlertDescription({ className, ...props }: React.ComponentProps<"p">) {
  return <p className={cn("text-sm opacity-90", className)} {...props} />
}
