import { parseSaiaAnswerText } from "@/components/structured-data/mcp-evidence-panel"

const THINKING_TAG_RE =
  /<\s*(?:redacted_thinking|thinking|budget:thinking)\s*>[\s\S]*?<\s*\/\s*(?:redacted_thinking|thinking|budget:thinking)\s*>/gi
const LEGACY_THINK_RE = /```think[\s\S]*?```/gi

function stripThinkingBlocks(text: string): string {
  let out = text.replace(THINKING_TAG_RE, "")
  out = out.replace(LEGACY_THINK_RE, "")
  const thinkClose = "```/think```"
  const idx = out.indexOf(thinkClose)
  if (idx >= 0) {
    out = out.slice(idx + thinkClose.length)
  }
  return out.trim()
}

function unwrapJsonAnswer(text: string): string {
  const trimmed = text.trim()
  if (!trimmed.startsWith("{")) return trimmed
  try {
    const data = JSON.parse(trimmed) as { answer?: unknown; content?: unknown; text?: unknown }
    for (const key of ["answer", "content", "text"] as const) {
      const value = data[key]
      if (typeof value === "string" && value.trim()) {
        return value.trim()
      }
    }
  } catch {
    // Not JSON — keep original markdown/text.
  }
  return trimmed
}

export type ParsedSocChatMessage = {
  body: string
  isFallback: boolean
  fallbackLabel: string | null
}

/** Normalize assistant chat text before markdown rendering. */
export function parseSocChatMessageContent(content: string): ParsedSocChatMessage {
  const withoutThinking = stripThinkingBlocks(content)
  const unwrapped = unwrapJsonAnswer(withoutThinking)
  const parsed = parseSaiaAnswerText(unwrapped)
  return {
    body: parsed.body,
    isFallback: parsed.isFallback,
    fallbackLabel: parsed.fallbackLabel,
  }
}
