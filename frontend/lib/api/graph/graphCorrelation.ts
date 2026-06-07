import { backendFetch } from "@/lib/api/client"
import type {
  GraphFindingDetails,
  GraphFindingsFilters,
  PaginatedGraphFindingsResponse,
  PatchFindingTicketBody,
} from "@/lib/api/graph/types"

const GRAPH_PREFIX = "/api/v1/graph"

function buildQuery(
  limit: number,
  offset: number,
  filters?: GraphFindingsFilters,
): string {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    finding_type: filters?.finding_type ?? "smart_attack_discovery",
  })
  if (filters?.exclude_finding_type) {
    params.set("exclude_finding_type", filters.exclude_finding_type)
  }
  return `${GRAPH_PREFIX}/findings?${params.toString()}`
}

async function mockFindings(
  limit: number,
  offset: number,
): Promise<PaginatedGraphFindingsResponse> {
  const mod = await import("@/lib/api/graph/mock/findings.json")
  const data = (mod.default ?? mod) as PaginatedGraphFindingsResponse
  return {
    ...data,
    limit,
    offset,
    items: data.items.slice(offset, offset + limit),
    total: data.total,
  }
}

export async function getGraphFindings(
  limit = 20,
  offset = 0,
  filters?: GraphFindingsFilters,
): Promise<PaginatedGraphFindingsResponse> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "true") {
    return mockFindings(limit, offset)
  }
  return backendFetch<PaginatedGraphFindingsResponse>(
    buildQuery(limit, offset, filters),
  )
}

export async function updateGraphFindingTicket(
  findingId: string,
  body: PatchFindingTicketBody,
): Promise<GraphFindingDetails> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "true") {
    const mod = await import("@/lib/api/graph/mock/finding-detail.json")
    const detail = (mod.default ?? mod) as GraphFindingDetails
    return {
      ...detail,
      id: findingId,
      ticket_status: body.ticket_status ?? detail.ticket_status,
      owner: body.assigned_to_user_id ?? detail.owner,
    }
  }
  return backendFetch<GraphFindingDetails>(
    `${GRAPH_PREFIX}/findings/${findingId}/ticket`,
    {
      method: "PATCH",
      body: JSON.stringify(body),
    },
  )
}
