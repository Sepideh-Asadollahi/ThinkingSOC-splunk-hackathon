"use client"

import * as React from "react"

import {
  Tabs,
  TabsContent,
  TabsContents,
  TabsList,
  TabsTrigger,
} from "@/components/animate-ui/components/radix/tabs"
import { cn } from "@/lib/utils"

import { getAccentClasses, type NeonAccent } from "./accent"

const ACTIVE_TAB: Record<NeonAccent, string> = {
  teal: "data-[state=active]:text-teal-400 data-[state=active]:border-teal-500/40",
  violet:
    "data-[state=active]:text-violet-400 data-[state=active]:border-violet-500/40",
  orange:
    "data-[state=active]:text-orange-400 data-[state=active]:border-orange-500/40",
}

function NeonTabs({ className, ...props }: React.ComponentProps<typeof Tabs>) {
  return <Tabs className={cn("w-full", className)} {...props} />
}

function NeonTabsList({
  accent = "teal",
  className,
  ...props
}: React.ComponentProps<typeof TabsList> & { accent?: NeonAccent }) {
  return (
    <TabsList
      className={cn(
        "h-auto min-h-0 gap-1.5 bg-transparent p-0 text-slate-400",
        className
      )}
      {...props}
    />
  )
}

function NeonTabsTrigger({
  accent = "teal",
  className,
  ...props
}: React.ComponentProps<typeof TabsTrigger> & { accent?: NeonAccent }) {
  return (
    <TabsTrigger
      className={cn(
        "cursor-pointer py-2 px-3 text-xs data-[state=active]:bg-transparent data-[state=active]:shadow-sm",
        "data-[state=active]:border border-transparent",
        ACTIVE_TAB[accent],
        className
      )}
      {...props}
    />
  )
}

function NeonTabsContents({
  className,
  ...props
}: React.ComponentProps<typeof TabsContents>) {
  return <TabsContents className={cn("mt-4", className)} {...props} />
}

function NeonTabsContent({
  className,
  ...props
}: React.ComponentProps<typeof TabsContent>) {
  return <TabsContent className={cn("outline-none", className)} {...props} />
}

export {
  NeonTabs,
  NeonTabsList,
  NeonTabsTrigger,
  NeonTabsContents,
  NeonTabsContent,
}
