"use client"

import { usePathname } from "next/navigation"

import { PAGE_ENTER_CLASSES } from "@/lib/page-enter"
import { cn } from "@/lib/utils"

export default function AppTemplate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <div key={pathname} className={cn("min-h-0", PAGE_ENTER_CLASSES)}>
      {children}
    </div>
  )
}
