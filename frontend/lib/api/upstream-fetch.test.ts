/**
 * @vitest-environment node
 */
import { afterEach, describe, expect, it } from "vitest"

import { upstreamTimeoutMs } from "./upstream-fetch"

describe("upstreamTimeoutMs", () => {
  afterEach(() => {
    delete process.env.TSOC_PROXY_LLM_TIMEOUT_MS
    delete process.env.TSOC_PROXY_CHAT_TIMEOUT_MS
    delete process.env.TSOC_PROXY_TIMEOUT_MS
  })

  it("allows slow LLM-backed endpoints up to fifteen minutes", () => {
    expect(upstreamTimeoutMs("llm/chat", "POST")).toBe(900_000)
    expect(upstreamTimeoutMs("analysis/run", "POST")).toBe(900_000)
    expect(upstreamTimeoutMs("investigation/records/record-1/runbook", "POST")).toBe(900_000)
  })

  it("keeps the normal timeout for non-LLM and read requests", () => {
    expect(upstreamTimeoutMs("health", "GET")).toBe(300_000)
    expect(upstreamTimeoutMs("llm/chat", "GET")).toBe(300_000)
  })

  it("supports the new setting and the legacy chat timeout setting", () => {
    process.env.TSOC_PROXY_LLM_TIMEOUT_MS = "1200000"
    expect(upstreamTimeoutMs("soc/chat", "POST")).toBe(1_200_000)

    delete process.env.TSOC_PROXY_LLM_TIMEOUT_MS
    process.env.TSOC_PROXY_CHAT_TIMEOUT_MS = "700000"
    expect(upstreamTimeoutMs("soc/chat", "POST")).toBe(700_000)
  })
})
