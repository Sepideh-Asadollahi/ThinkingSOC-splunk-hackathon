import { backendFetch } from "@/lib/api/client"
import type { McpStatusResponse } from "@/lib/api/types"

export async function fetchMcpStatus(): Promise<McpStatusResponse> {
  return backendFetch<McpStatusResponse>("/mcp/status")
}
