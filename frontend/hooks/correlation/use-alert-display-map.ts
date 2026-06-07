"use client"

import { useMemo } from "react"

import { useGraphState } from "@/components/correlation/explorer/graph-context"
import { useFilteredGraphView } from "@/hooks/correlation/use-filtered-graph"
import { useTriageAnalysisIndex } from "@/hooks/correlation/use-triage-analysis-index"
import {
  buildAlertDisplayByNodeId,
  type AlertDisplayInfo,
} from "@/lib/api/graph/alert-display"

export function useAlertDisplayMap(): {
  byNodeId: Map<string, AlertDisplayInfo>
  indexLoading: boolean
  indexError: string | null
} {
  const { finding } = useGraphState()
  const { topology } = useFilteredGraphView()
  const { index, loading, error } = useTriageAnalysisIndex()

  const byNodeId = useMemo(
    () => buildAlertDisplayByNodeId(topology?.nodes ?? [], finding, index),
    [topology?.nodes, finding, index],
  )

  return { byNodeId, indexLoading: loading, indexError: error }
}
