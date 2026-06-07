import { backendFetch } from "@/lib/api/client"

export type SocChatMessage = { role: string; content: string }

export type SocChatCitation = {
  doc_id: string
  sid?: string | null
  search_name?: string | null
  summary_line: string
  doc_type: string
  similarity_score?: number | null
}

export type SocChatSqlMeta = {
  query_mode: "sql" | "rag"
  sql?: string | null
  row_count?: number | null
  tables_used?: string[] | null
}

export type SocChatResponse = {
  answer: string
  citations: SocChatCitation[]
  splunk_mcp_used: boolean
  retrieval_backend: string
  retrieval_meta: Record<string, unknown>
  sql_meta?: SocChatSqlMeta | null
  conversation_id?: string | null
}

export type SocChatStatus = {
  enabled: boolean
  postgres_configured: boolean
  vector_enabled: boolean
  qdrant_reachable: boolean
  qdrant_url?: string | null
  embedding_model?: string | null
  document_count: number
  last_indexed_at?: string | null
  default_retrieval?: string
  correlation_enabled?: boolean
  correlation_neo4j_reachable?: boolean
}

export type SocChatConversationSummary = {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export type SocChatStoredMessage = SocChatMessage & {
  message_id?: number | null
  seq?: number | null
  sql_meta?: SocChatSqlMeta | null
}

export type SocChatConversationDetail = {
  id: string
  title: string
  created_at: string
  updated_at: string
  messages: SocChatStoredMessage[]
}

export async function fetchSocChatStatus(): Promise<SocChatStatus> {
  return backendFetch<SocChatStatus>("/soc/chat/status")
}

export async function fetchSocChatConversations(): Promise<SocChatConversationSummary[]> {
  return backendFetch<SocChatConversationSummary[]>("/soc/chat/conversations")
}

export async function createSocChatConversation(title?: string): Promise<SocChatConversationSummary> {
  return backendFetch<SocChatConversationSummary>("/soc/chat/conversations", {
    method: "POST",
    body: JSON.stringify(title ? { title } : {}),
  })
}

export async function fetchSocChatConversation(conversationId: string): Promise<SocChatConversationDetail> {
  return backendFetch<SocChatConversationDetail>(`/soc/chat/conversations/${encodeURIComponent(conversationId)}`)
}

export async function deleteSocChatConversation(conversationId: string): Promise<{ ok: boolean }> {
  return backendFetch(`/soc/chat/conversations/${encodeURIComponent(conversationId)}`, {
    method: "DELETE",
  })
}

export async function postSocChat(
  messages: SocChatMessage[],
  conversationId?: string | null
): Promise<SocChatResponse> {
  return backendFetch<SocChatResponse>("/soc/chat", {
    method: "POST",
    body: JSON.stringify({
      messages,
      conversation_id: conversationId ?? undefined,
    }),
  })
}

export async function postSocRagBackfill(limit = 200): Promise<{ ok: boolean; counts: Record<string, number> }> {
  return backendFetch(`/soc/rag/backfill?limit=${limit}`, { method: "POST" })
}

export function formatConversationTime(iso: string): string {
  if (!iso) return ""
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}
