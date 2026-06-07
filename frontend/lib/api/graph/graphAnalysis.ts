import { backendFetch } from "@/lib/api/client"
import type {
  AttackDiscoveryPayload,
  DiscoverAttackPathsResponse,
  GraphFindingDetails,
  OperationStatusResponse,
} from "@/lib/api/graph/types"

const GRAPH_PREFIX = "/api/v1/graph"

export async function initiateAttackDiscovery(
  payload: AttackDiscoveryPayload,
): Promise<DiscoverAttackPathsResponse> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "true") {
    return {
      message: "Task Initiated",
      operation_id: "mock-operation-001",
    }
  }
  return backendFetch<DiscoverAttackPathsResponse>(
    `${GRAPH_PREFIX}/analysis/discover-attack-paths`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  )
}

export async function getOperationStatus(
  operationId: string,
): Promise<OperationStatusResponse> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "true") {
    return {
      operation_id: operationId,
      operation_type: "manual_attack_discovery",
      status: "completed",
      message: "Mock analysis complete",
      detailed_logs: [
        {
          timestamp: new Date().toISOString(),
          level: "info",
          message: "Fetched 6 alerts from Neo4j",
        },
        {
          timestamp: new Date().toISOString(),
          level: "info",
          message: "Created 1 finding",
        },
      ],
      result_payload: {
        findings_created: 1,
        finding_ids: ["22222222-2222-2222-2222-222222222201"],
        smart_analysis_summary: { clusters: 1, alerts_processed: 6 },
      },
    }
  }
  return backendFetch<OperationStatusResponse>(
    `${GRAPH_PREFIX}/analysis/operations/${operationId}/status`,
  )
}

export async function getGraphFindingDetails(
  findingId: string,
): Promise<GraphFindingDetails> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "true") {
    const mod = await import("@/lib/api/graph/mock/finding-detail.json")
    const detail = (mod.default ?? mod) as GraphFindingDetails
    return { ...detail, id: findingId }
  }
  return backendFetch<GraphFindingDetails>(
    `${GRAPH_PREFIX}/findings/${findingId}`,
  )
}
