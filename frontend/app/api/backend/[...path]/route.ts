import { NextRequest, NextResponse } from "next/server"

import { SESSION_COOKIE, verifySession } from "@/lib/auth/session"
import { proxyLog } from "@/lib/api/proxy-log"
import {
  fetchUpstream,
  isUpstreamTimeoutError,
  upstreamTimeoutMs,
} from "@/lib/api/upstream-fetch"

const BACKEND_URL = process.env.TSOC_BACKEND_URL || "http://127.0.0.1:9876"

/** Allow long SOC chat (multiple LLM calls) on self-hosted / compatible platforms. */
export const maxDuration = 600

function isConnectionRefused(err: unknown): boolean {
  if (!err || typeof err !== "object") return false
  const cause = "cause" in err ? (err as { cause?: unknown }).cause : undefined
  if (!cause || typeof cause !== "object") return false
  return "code" in cause && (cause as { code?: unknown }).code === "ECONNREFUSED"
}

async function proxy(request: NextRequest, pathSegments: string[]) {
  const t0 = performance.now()
  const session = await verifySession(request.cookies.get(SESSION_COOKIE)?.value)
  if (!session) {
    proxyLog("proxy.unauthorized", { path: pathSegments.join("/") }, "warn")
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 })
  }

  const rawPath = pathSegments.join("/").replace(/^\/+/, "")
  const path = rawPath.startsWith("api/v1/") ? rawPath.slice("api/v1/".length) : rawPath
  const url = new URL(`/api/v1/${path}`, BACKEND_URL)
  request.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value)
  })

  const headers = new Headers()
  const contentType = request.headers.get("content-type")
  if (contentType) headers.set("content-type", contentType)

  const token = process.env.TSOC_INGEST_TOKEN
  if (token) {
    headers.set("Authorization", `Bearer ${token}`)
  }

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
  }

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.text()
  }

  const timeoutMs = upstreamTimeoutMs(path, request.method)
  proxyLog("proxy.start", {
    method: request.method,
    path,
    backend: BACKEND_URL,
    timeoutMs,
    user: session.username,
  })

  try {
    const upstream = await fetchUpstream(url.toString(), init, timeoutMs, { path })
    const elapsedMs = Math.round(performance.now() - t0)
    const bodyBytes = new TextEncoder().encode(upstream.bodyText).length

    if (!upstream.status || upstream.status >= 400) {
      proxyLog(
        "proxy.upstream_error",
        {
          path,
          status: upstream.status,
          bodyBytes,
          elapsedMs,
          bodyPreview: upstream.bodyText.slice(0, 240),
        },
        "warn"
      )
    } else {
      proxyLog("proxy.done", { path, status: upstream.status, bodyBytes, elapsedMs })
    }

    return new NextResponse(upstream.bodyText, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") || "application/json",
      },
    })
  } catch (err) {
    const elapsedMs = Math.round(performance.now() - t0)
    const errMeta =
      err instanceof Error
        ? { name: err.name, message: err.message, code: (err as { code?: string }).code }
        : { message: String(err) }

    if (isConnectionRefused(err)) {
      proxyLog("proxy.backend_unreachable", { path, elapsedMs, backend: BACKEND_URL }, "error")
      return NextResponse.json(
        {
          detail: `Backend is unreachable at ${BACKEND_URL}. Start backend service and retry.`,
        },
        { status: 503 },
      )
    }
    if (isUpstreamTimeoutError(err)) {
      proxyLog("proxy.timeout", { path, elapsedMs, timeoutMs, ...errMeta }, "error")
      return NextResponse.json(
        {
          detail:
            "Backend request timed out waiting for SOC chat. This can take several minutes when using Text-to-SQL or a slow LLM provider — retry, or verify LiteLLM model and API base in Splunk Connection.",
        },
        { status: 504 },
      )
    }

    proxyLog("proxy.failed", { path, elapsedMs, ...errMeta }, "error")
    return NextResponse.json(
      {
        detail: "Proxy failed while calling backend. See server logs tagged [tsoc/proxy].",
        path,
        error: errMeta.message,
      },
      { status: 500 },
    )
  }
}

type RouteContext = { params: Promise<{ path: string[] }> }

export async function GET(request: NextRequest, context: RouteContext) {
  const { path } = await context.params
  return proxy(request, path)
}

export async function POST(request: NextRequest, context: RouteContext) {
  const { path } = await context.params
  return proxy(request, path)
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  const { path } = await context.params
  return proxy(request, path)
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  const { path } = await context.params
  return proxy(request, path)
}

export async function PUT(request: NextRequest, context: RouteContext) {
  const { path } = await context.params
  return proxy(request, path)
}
