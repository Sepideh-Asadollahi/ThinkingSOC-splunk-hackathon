import { backendFetch } from "@/lib/api/client"
import type { AttackTreeResponse, GraphResponse } from "@/lib/api/graph/types"

const GRAPH_PREFIX = "/api/v1/graph"

export async function getGraphTopology(
  identifier: string,
): Promise<GraphResponse> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "true") {
    const mod = await import("@/lib/api/graph/mock/topology-alert.json")
    return (mod.default ?? mod) as GraphResponse
  }
  return backendFetch<GraphResponse>(`${GRAPH_PREFIX}/topology/${identifier}`)
}

export async function getGraphAttackTree(
  identifier: string,
): Promise<AttackTreeResponse> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "true") {
    const topology = await getGraphTopology(identifier)
    return {
      attack_trees: topology.nodes.map((node, i) => ({
        step: String(i + 1),
        node_id: node.id,
        name: `Alert: ${node.label}`,
        type: "Alert",
        risk_score: node.properties?.risk_score as number | undefined,
        children: [],
      })),
      message: "Success.",
    }
  }
  return backendFetch<AttackTreeResponse>(
    `${GRAPH_PREFIX}/attack-tree/${identifier}`,
  )
}
