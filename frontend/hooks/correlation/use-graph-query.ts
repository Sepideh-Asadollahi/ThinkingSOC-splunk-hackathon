"use client"

import { useEffect } from "react"

import { useGraphDispatch } from "@/components/correlation/explorer/graph-context"
import { getGraphFindingDetails } from "@/lib/api/graph/graphAnalysis"
import {
  getGraphAttackTree,
  getGraphTopology,
} from "@/lib/api/graph/graphExplorer"

export function useGraphQuery(findingId: string | null) {
  const dispatch = useGraphDispatch()

  useEffect(() => {
    if (!findingId) return
    let cancelled = false

    ;(async () => {
      dispatch({ type: "SET_LOADING", payload: true })
      dispatch({ type: "SET_ERROR", payload: null })
      try {
        const [topology, attackTree, details] = await Promise.all([
          getGraphTopology(findingId),
          getGraphAttackTree(findingId),
          getGraphFindingDetails(findingId),
        ])
        if (cancelled) return

        dispatch({
          type: "SET_FULL_DATA",
          payload: {
            topology,
            attackTrees: attackTree?.attack_trees ?? [],
            notifications: topology.notifications ?? null,
            message: topology.message,
          },
        })
        dispatch({ type: "SET_FINDING_METADATA", payload: details })
      } catch (e) {
        if (!cancelled) {
          dispatch({
            type: "SET_ERROR",
            payload: e instanceof Error ? e.message : String(e),
          })
        }
      } finally {
        if (!cancelled) dispatch({ type: "SET_LOADING", payload: false })
      }
    })()

    return () => {
      cancelled = true
    }
  }, [findingId, dispatch])
}
