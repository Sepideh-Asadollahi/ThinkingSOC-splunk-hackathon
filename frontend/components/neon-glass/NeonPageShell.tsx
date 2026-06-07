"use client"

import * as React from "react"

import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"

type NeonPageShellProps = {
  header?: React.ReactNode
  children: React.ReactNode
  className?: string
  mainClassName?: string
  scrollable?: boolean
}

export function NeonPageShell({
  header,
  children,
  className,
  mainClassName,
  scrollable = true,
}: NeonPageShellProps) {
  const mainContent = (
    <main
      className={cn(
        "flex flex-1 flex-col min-h-0 min-w-0 p-4 md:p-6 space-y-4",
        mainClassName
      )}
    >
      {children}
    </main>
  )

  return (
    <div
      className={cn(
        "flex h-full min-h-0 min-w-0 flex-col overflow-hidden bg-[#050505]",
        className
      )}
    >
      {header}
      {scrollable ? (
        <ScrollArea className="flex-1 min-h-0 min-w-0">{mainContent}</ScrollArea>
      ) : (
        mainContent
      )}
    </div>
  )
}

