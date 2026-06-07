"use client"

import { useEffect, useState } from "react"

import { ApiError, backendFetch } from "@/lib/api/client"
import {
  buildTriageAnalysisIndex,
  type TriageAnalysisIndex,
} from "@/lib/api/graph/alert-display"
import type { TriageQueueResponse } from "@/lib/api/types"

export function useTriageAnalysisIndex(): {
  index: TriageAnalysisIndex | null
  loading: boolean
  error: string | null
} {
  const [index, setIndex] = useState<TriageAnalysisIndex | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await backendFetch<TriageQueueResponse>(
          "/triage/queue?limit=200&track=all",
        )
        if (cancelled) return
        setIndex(buildTriageAnalysisIndex(data.results ?? []))
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof ApiError ? e.message : "Failed to load analysis links")
          setIndex(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  return { index, loading, error }
}
