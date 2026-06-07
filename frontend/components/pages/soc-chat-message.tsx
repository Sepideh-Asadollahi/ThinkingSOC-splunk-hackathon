"use client"

import { NeonBadge } from "@/components/neon-glass"
import { McpMarkdownContent } from "@/components/structured-data/mcp-markdown-content"
import { parseSocChatMessageContent } from "@/lib/soc-chat-parse"
import type { SocChatSqlMeta } from "@/lib/api/soc-chat"

type SocChatMessageBubbleProps = {
  role: string
  content: string
  sqlMeta?: SocChatSqlMeta | null
}

export function SocChatMessageBubble({ role, content, sqlMeta }: SocChatMessageBubbleProps) {
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
      {sqlMeta?.query_mode === "sql" && (sqlMeta.row_count != null || sqlMeta.sql) ? (
        <p className="mt-3 border-t border-white/10 pt-2 text-[11px] text-slate-500">
          {sqlMeta.row_count != null ? `${sqlMeta.row_count} row(s)` : "SQL query"}
          {sqlMeta.tables_used?.length ? ` · ${sqlMeta.tables_used.join(", ")}` : ""}
        </p>
      ) : null}
    </div>
  )
}
