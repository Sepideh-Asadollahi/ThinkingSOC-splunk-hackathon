import { Agent } from "undici"

import { proxyLog } from "@/lib/api/proxy-log"

const DEFAULT_TIMEOUT_MS = 300_000
const CHAT_TIMEOUT_MS = 600_000

function parseTimeoutMs(env: string | undefined, fallback: number): number {
  const n = Number(env)
  return Number.isFinite(n) && n > 0 ? n : fallback
}

/** Upstream fetch timeout for Next.js → FastAPI proxy (undici headers/body). */
export function upstreamTimeoutMs(path: string, method: string): number {
  const normalized = path.replace(/^\/+|\/+$/g, "")
  if (method === "POST" && normalized === "soc/chat") {
    return parseTimeoutMs(process.env.TSOC_PROXY_CHAT_TIMEOUT_MS, CHAT_TIMEOUT_MS)
  }
  return parseTimeoutMs(process.env.TSOC_PROXY_TIMEOUT_MS, DEFAULT_TIMEOUT_MS)
}

export function isUpstreamTimeoutError(err: unknown): boolean {
  const cause = err instanceof Error ? err.cause : undefined
  if (!cause || typeof cause !== "object" || !("code" in cause)) return false
  const code = (cause as { code?: string }).code
  return code === "UND_ERR_HEADERS_TIMEOUT" || code === "UND_ERR_BODY_TIMEOUT"
}

export type UpstreamFetchResult = {
  status: number
  headers: Headers
  bodyText: string
}

/**
 * Fetch FastAPI and read the full body before closing the undici Agent.
 * Closing the agent immediately after `fetch()` resolves can abort large response
 * bodies (e.g. investigation records with SPL result rows) mid-stream.
 */
export async function fetchUpstream(
  url: string,
  init: RequestInit,
  timeoutMs: number,
  debug?: { path?: string },
): Promise<UpstreamFetchResult> {
  const t0 = performance.now()
  const agent = new Agent({
    connectTimeout: 30_000,
    headersTimeout: timeoutMs,
    bodyTimeout: timeoutMs,
  })
  try {
    proxyLog("upstream.fetch_start", {
      path: debug?.path,
      method: init.method ?? "GET",
      timeoutMs,
      target: url.split("?")[0],
    })
    const response = await fetch(url, {
      ...init,
      dispatcher: agent,
    } as RequestInit & { dispatcher: Agent })
    const headersMs = Math.round(performance.now() - t0)
    proxyLog("upstream.headers", {
      path: debug?.path,
      status: response.status,
      headersMs,
      contentLength: response.headers.get("content-length"),
    })
    const bodyText = await response.text()
    const bodyBytes = new TextEncoder().encode(bodyText).length
    proxyLog("upstream.body_read", {
      path: debug?.path,
      status: response.status,
      bodyBytes,
      totalMs: Math.round(performance.now() - t0),
      isHtml: bodyText.trimStart().startsWith("<!"),
    })
    return {
      status: response.status,
      headers: response.headers,
      bodyText,
    }
  } catch (err) {
    const errMeta =
      err instanceof Error
        ? {
            name: err.name,
            message: err.message,
            code: (err as { code?: string }).code,
            cause: (err as { cause?: unknown }).cause,
          }
        : { message: String(err) }
    proxyLog(
      "upstream.fetch_failed",
      { path: debug?.path, elapsedMs: Math.round(performance.now() - t0), ...errMeta },
      "error"
    )
    throw err
  } finally {
    await agent.close().catch(() => {})
  }
}
