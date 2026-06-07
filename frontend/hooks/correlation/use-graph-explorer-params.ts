"use client"

import { useMemo } from "react"
import { useSearchParams } from "next/navigation"

export function useGraphExplorerParams() {
  const searchParams = useSearchParams()

  return useMemo(() => {
    const findingId = searchParams.get("finding_id")?.trim() || null
    const identifier =
      searchParams.get("identifier")?.trim() || findingId || null

    const isReady = Boolean(findingId && identifier)

    return { findingId, identifier, isReady }
  }, [searchParams])
}
