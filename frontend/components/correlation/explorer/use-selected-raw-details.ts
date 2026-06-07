"use client"

import { useMemo } from "react"

import { useGraphState } from "@/components/correlation/explorer/graph-context"
import {
  selectedNodeFromFilteredView,
  useFilteredGraphView,
} from "@/hooks/correlation/use-filtered-graph"

export type AlertNodeDetails = {
  name: string
  timestamp?: string
  risk_score?: number
  threat_status?: string
  alert_row_id?: string
  source: "contributing_alert" | "neo4j_properties"
}

export function useSelectedRawDetails(): AlertNodeDetails | null {
  const { selectedNodeId, finding } = useGraphState()
  const { rawNodes, topology } = useFilteredGraphView()
  const selected = selectedNodeFromFilteredView(
    selectedNodeId,
    rawNodes,
    topology,
  )

  return useMemo(() => {
    if (!selected) return null

    const alertRowId = selected.properties?.alert_row_id as string | undefined
    const contributing = finding?.details?.contributing_alerts ?? []

    if (alertRowId && contributing.length) {
      const match = contributing.find((a) => a.alert_row_id === alertRowId)
      if (match) {
        return {
          name: match.alert_name,
          timestamp: match.timestamp,
          risk_score: match.risk_score,
          threat_status: match.threat_status,
          alert_row_id: match.alert_row_id,
          source: "contributing_alert",
        }
      }
    }

    return {
      name: selected.label,
      timestamp: selected.properties?.timestamp as string | undefined,
      risk_score: selected.properties?.risk_score as number | undefined,
      threat_status: selected.properties?.status as string | undefined,
      alert_row_id: alertRowId,
      source: "neo4j_properties",
    }
  }, [selected, finding])
}
