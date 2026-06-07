"use client"

import { useMemo } from "react"

import { useGraphState } from "@/components/correlation/explorer/graph-context"
import { useFilteredGraphView } from "@/hooks/correlation/use-filtered-graph"
import {
  buildAlertFrameworkByNodeId,
  uniqueKillChainPhases,
  uniqueMitreTechniques,
  type AlertFrameworkContext,
} from "@/lib/api/graph/attack-framework"

export function useAlertFrameworkMap(): {
  byNodeId: Map<string, AlertFrameworkContext>
  killChainPhases: string[]
  mitreTechniques: string[]
} {
  const { finding } = useGraphState()
  const { topology } = useFilteredGraphView()

  return useMemo(() => {
    const nodes = topology?.nodes ?? []
    const edges = topology?.edges ?? []
    const byNodeId = buildAlertFrameworkByNodeId(nodes, edges, finding)
    return {
      byNodeId,
      killChainPhases: uniqueKillChainPhases(byNodeId),
      mitreTechniques: uniqueMitreTechniques(byNodeId),
    }
  }, [topology, finding])
}
