"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { MessageSquarePlusIcon, SendIcon, Trash2Icon } from "lucide-react"

import {
  NeonActionButton,
  NeonAlert,
  NeonAlertDescription,
  NeonField,
  NeonFieldLabel,
  NeonGlassCard,
  NeonInput,
} from "@/components/neon-glass"
import { SocChatDeleteDialog } from "@/components/pages/soc-chat-delete-dialog"
import { SocChatMessageBubble } from "@/components/pages/soc-chat-message"
import { ApiError } from "@/lib/api/client"
import {
  createSocChatConversation,
  deleteSocChatConversation,
  fetchSocChatConversation,
  fetchSocChatConversations,
  formatConversationTime,
  postSocChat,
  postSocRagBackfill,
  type SocChatConversationSummary,
  type SocChatCitation,
  type SocChatMessage,
  type SocChatSqlMeta,
} from "@/lib/api/soc-chat"
import { tsocOverflowYAutoClasses } from "@/lib/ui-scroll"
import { cn } from "@/lib/utils"

type ChatMessage = SocChatMessage & {
  sql_meta?: SocChatSqlMeta | null
  citations?: SocChatCitation[]
}

export function SocChatContent({ initialPrompt = "" }: { initialPrompt?: string }) {
  const [conversations, setConversations] = useState<SocChatConversationSummary[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState(initialPrompt)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hydrated, setHydrated] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<SocChatConversationSummary | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const refreshConversations = useCallback(async (preferredId?: string | null) => {
    const list = await fetchSocChatConversations()
    setConversations(list)
    const nextActive =
      preferredId && list.some((c) => c.id === preferredId)
        ? preferredId
        : list[0]?.id ?? null
    setActiveConversationId(nextActive)
    return { list, nextActive }
  }, [])

  const loadConversationMessages = useCallback(async (conversationId: string) => {
    const detail = await fetchSocChatConversation(conversationId)
    setMessages(
      detail.messages.map((m) => ({
        role: m.role,
        content: m.content,
        sql_meta: m.sql_meta ?? null,
        citations: m.citations ?? [],
      }))
    )
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const { list, nextActive } = await refreshConversations()
        if (cancelled) return
        if (list.length === 0) {
          const fresh = await createSocChatConversation()
          if (cancelled) return
          setConversations([fresh])
          setActiveConversationId(fresh.id)
          setMessages([])
        } else if (nextActive) {
          await loadConversationMessages(nextActive)
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof ApiError ? e.message : "Failed to load chat history")
        }
      } finally {
        if (!cancelled) setHydrated(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [loadConversationMessages, refreshConversations])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  const selectConversation = async (conversationId: string) => {
    if (conversationId === activeConversationId || loading) return
    setActiveConversationId(conversationId)
    setError(null)
    setLoading(true)
    try {
      await loadConversationMessages(conversationId)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load conversation")
    } finally {
      setLoading(false)
    }
  }

  const startNewChat = async () => {
    setLoading(true)
    setError(null)
    try {
      const fresh = await createSocChatConversation()
      setConversations((prev) => [fresh, ...prev])
      setActiveConversationId(fresh.id)
      setMessages([])
      setInput("")
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to create conversation")
    } finally {
      setLoading(false)
    }
  }

  const deleteConversation = async (conversationId: string) => {
    setLoading(true)
    setError(null)
    try {
      await deleteSocChatConversation(conversationId)
      const { list, nextActive } = await refreshConversations(
        activeConversationId === conversationId ? null : activeConversationId
      )
      if (list.length === 0) {
        const fresh = await createSocChatConversation()
        setConversations([fresh])
        setActiveConversationId(fresh.id)
        setMessages([])
      } else if (nextActive) {
        await loadConversationMessages(nextActive)
      } else {
        setMessages([])
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete conversation")
    } finally {
      setLoading(false)
      setDeleteTarget(null)
    }
  }

  const requestDeleteConversation = (conversation: SocChatConversationSummary, e?: React.MouseEvent) => {
    e?.stopPropagation()
    setDeleteTarget(conversation)
  }

  const confirmDelete = () => {
    if (!deleteTarget) return
    void deleteConversation(deleteTarget.id)
  }

  const activeConversation = conversations.find((c) => c.id === activeConversationId) ?? null

  const send = async () => {
    const text = input.trim()
    if (!text || loading || !activeConversationId) return
    const prior = messages
    const next: ChatMessage[] = [...messages, { role: "user", content: text }]
    setMessages(next)
    setInput("")
    setLoading(true)
    setError(null)
    try {
      const res = await postSocChat(next, activeConversationId)
      const withAssistant: ChatMessage[] = [
        ...next,
        {
          role: "assistant",
          content: res.answer,
          sql_meta: res.sql_meta ?? null,
          citations: res.citations,
        },
      ]
      setMessages(withAssistant)
      const convId = res.conversation_id ?? activeConversationId
      if (convId !== activeConversationId) {
        setActiveConversationId(convId)
      }
      await refreshConversations(convId)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Chat failed")
      setMessages(prior)
    } finally {
      setLoading(false)
    }
  }

  const backfill = async () => {
    setLoading(true)
    setError(null)
    try {
      await postSocRagBackfill()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Backfill failed")
    } finally {
      setLoading(false)
    }
  }

  if (!hydrated) {
    return (
      <div className="flex flex-col gap-4 p-4 md:p-6">
        <p className="text-sm text-muted-foreground">Loading chat history…</p>
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Chat</h1>
          <p className="mt-1 text-xs text-muted-foreground">
            Ask about alerts, analyses, Runbook revisions, approvals, response previews, and Autopilot agent/tool traces.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {activeConversation && (
            <NeonActionButton
              type="button"
              className="border-red-500/30 text-red-200 hover:bg-red-950/40"
              onClick={() => requestDeleteConversation(activeConversation)}
              disabled={loading}
            >
              <Trash2Icon className="size-4" />
              Delete chat
            </NeonActionButton>
          )}
          <NeonActionButton type="button" onClick={() => void backfill()} disabled={loading}>
            Index backfill
          </NeonActionButton>
        </div>
      </div>

      <SocChatDeleteDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null)
        }}
        title={deleteTarget?.title ?? "this chat"}
        onConfirm={confirmDelete}
        deleting={loading && deleteTarget !== null}
      />

      {error && (
        <NeonAlert variant="destructive">
          <NeonAlertDescription>{error}</NeonAlertDescription>
        </NeonAlert>
      )}

      <div className="flex min-h-0 flex-1 flex-col gap-4 lg:flex-row">
        <NeonGlassCard className="flex w-full shrink-0 flex-col p-3 lg:w-72 xl:w-80">
          <NeonActionButton
            type="button"
            className="mb-3 w-full justify-start"
            onClick={() => void startNewChat()}
            disabled={loading}
          >
            <MessageSquarePlusIcon className="size-4" />
            New chat
          </NeonActionButton>
          <div
            className={cn(
              "min-h-[200px] flex-1 space-y-1 overflow-y-auto pr-1 lg:max-h-[calc(100vh-22rem)]",
              tsocOverflowYAutoClasses
            )}
          >
            {conversations.map((c) => {
              const isActive = c.id === activeConversationId
              return (
                <div
                  key={c.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => void selectConversation(c.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault()
                      void selectConversation(c.id)
                    }
                  }}
                  className={cn(
                    "group flex w-full cursor-pointer items-start gap-2 rounded-lg px-2 py-2 text-left text-sm transition-colors",
                    isActive
                      ? "bg-teal-900/40 text-foreground"
                      : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
                  )}
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{c.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatConversationTime(c.updated_at)}
                      {c.message_count > 0 ? ` · ${c.message_count} msgs` : ""}
                    </p>
                  </div>
                  <NeonActionButton
                    type="button"
                    size="sm"
                    className={cn(
                      "shrink-0 transition-opacity",
                      isActive ? "opacity-100" : "opacity-60 group-hover:opacity-100"
                    )}
                    aria-label={`Delete ${c.title}`}
                    onClick={(e) => requestDeleteConversation(c, e)}
                    disabled={loading}
                  >
                    <Trash2Icon className="size-3.5" />
                  </NeonActionButton>
                </div>
              )
            })}
          </div>
        </NeonGlassCard>

        <NeonGlassCard className="flex min-h-[420px] min-w-0 flex-1 flex-col p-4">
          <div className={cn("flex-1 space-y-3 overflow-y-auto pr-1", tsocOverflowYAutoClasses)}>
            {messages.length === 0 && (
              <p className="text-sm text-muted-foreground">
                Example: Which correlation findings have the highest risk? What alerts share entity hostname:workstation-01?
              </p>
            )}
            {messages.map((m, i) => (
              <SocChatMessageBubble
                key={i}
                role={m.role}
                content={m.content}
                sqlMeta={m.role === "assistant" ? m.sql_meta : null}
                citations={m.role === "assistant" ? m.citations : undefined}
              />
            ))}
            {loading && <p className="text-sm text-muted-foreground">Thinking…</p>}
            <div ref={bottomRef} />
          </div>

          <div className="mt-4 flex gap-2 border-t border-white/10 pt-4">
            <NeonField className="flex-1">
              <NeonFieldLabel className="sr-only">Message</NeonFieldLabel>
              <NeonInput
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about alerts—or run an approved Runbook by SID…"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    void send()
                  }
                }}
                disabled={loading}
              />
            </NeonField>
            <NeonActionButton type="button" onClick={() => void send()} disabled={loading || !input.trim()}>
              <SendIcon className="size-4" />
              Send
            </NeonActionButton>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Try: “Run the approved Runbook for SID demo-123”.
          </p>
        </NeonGlassCard>
      </div>
    </div>
  )
}
