import { describe, expect, it } from "vitest"

import { LITELLM_FALLBACK_ANSWER_PREFIX } from "@/components/structured-data/mcp-evidence-panel"

import { parseSocChatMessageContent } from "./soc-chat-parse"

describe("parseSocChatMessageContent", () => {
  it("passes through markdown lists and emphasis", () => {
    const parsed = parseSocChatMessageContent(
      "There are **3** alert(s):\n\n1. Suspicious login\n2. Brute force"
    )
    expect(parsed.body).toContain("**3**")
    expect(parsed.body).toContain("Suspicious login")
  })

  it("strips thinking tags before rendering", () => {
    const parsed = parseSocChatMessageContent(
      "<thinking>internal reasoning</thinking>\n\n**Answer:** 5 alerts."
    )
    expect(parsed.body).toBe("**Answer:** 5 alerts.")
  })

  it("unwraps JSON answer payloads", () => {
    const parsed = parseSocChatMessageContent(
      JSON.stringify({ answer: "Count: **12** users." })
    )
    expect(parsed.body).toBe("Count: **12** users.")
  })

  it("splits LiteLLM fallback banner from body", () => {
    const parsed = parseSocChatMessageContent(
      `${LITELLM_FALLBACK_ANSWER_PREFIX}\nTop matches:\n- alert A`
    )
    expect(parsed.isFallback).toBe(true)
    expect(parsed.body).toContain("Top matches")
    expect(parsed.body).not.toContain(LITELLM_FALLBACK_ANSWER_PREFIX)
  })
})
