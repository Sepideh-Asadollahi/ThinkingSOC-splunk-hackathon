"use client"

import { NeonBadge } from "@/components/neon-glass"
import { McpMarkdownContent } from "@/components/structured-data/mcp-markdown-content"
import { parseSocChatMessageContent } from "@/lib/soc-chat-parse"
import type { SocChatCitation, SocChatSqlMeta } from "@/lib/api/soc-chat"

type SocChatMessageBubbleProps = {
  role: string
  content: string
  sqlMeta?: SocChatSqlMeta | null
  citations?: SocChatCitation[]
}

export function SocChatMessageBubble({ role, content, sqlMeta, citations = [] }: SocChatMessageBubbleProps) {
  const isUser = role === "user"

  if (isUser) {
    return (
      <div className="ml-auto max-w-[85%] rounded-lg bg-teal-900/40 px-3 py-2 text-sm whitespace-pre-wrap">
        {content}
      </div>
    )
  }

  const parsed = parseSocChatMessageContent(content)

  return (
    <div className="mr-auto max-w-[90%] rounded-lg bg-slate-800/60 px-3 py-2 text-sm">
      {parsed.isFallback && parsed.fallbackLabel ? (
        <NeonBadge className="mb-2 border-orange-500/30 text-orange-300">
          {parsed.fallbackLabel}
        </NeonBadge>
      ) : null}
      <McpMarkdownContent content={parsed.body} className="text-sm" />
      {citations.length > 0 ? (
        <details className="mt-3 border-t border-white/10 pt-2">
          <summary className="cursor-pointer text-[11px] font-medium text-teal-300">
            {citations.length} retrieved source{citations.length === 1 ? "" : "s"}
          </summary>
          <div className="mt-2 space-y-2">
            {citations.map((citation, index) => (
              <div
                key={`${citation.doc_id}-${index}`}
                className="rounded-md border border-white/10 bg-black/25 p-2"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <NeonBadge className="border-teal-400/20 text-teal-200">
                    {citation.doc_type.replaceAll("_", " ")}
                  </NeonBadge>
                  {citation.search_name ? (
                    <span className="text-[10px] text-slate-500">{citation.search_name}</span>
                  ) : null}
                </div>
                <p className="mt-1 text-[11px] leading-4 text-slate-400">{citation.summary_line}</p>
                <code className="mt-1 block break-all text-[10px] text-slate-600">{citation.doc_id}</code>
              </div>
            ))}
          </div>
        </details>
      ) : null}
      {sqlMeta?.query_mode === "sql" && (sqlMeta.row_count != null || sqlMeta.sql) ? (
        <p className="mt-3 border-t border-white/10 pt-2 text-[11px] text-slate-500">
          {sqlMeta.row_count != null ? `${sqlMeta.row_count} row(s)` : "SQL query"}
          {sqlMeta.tables_used?.length ? ` · ${sqlMeta.tables_used.join(", ")}` : ""}
        </p>
      ) : null}
    </div>
  )
}
