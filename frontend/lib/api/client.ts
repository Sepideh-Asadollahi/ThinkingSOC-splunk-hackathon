import { storageApiLog } from "@/lib/api/investigation-log"

export class ApiError extends Error {
  status: number
  body: unknown

  constructor(status: number, message: string, body?: unknown) {
    super(message)
    this.status = status
    this.body = body
  }
}

function traceStorageEvents(path: string): boolean {
  return /\/storage\/events(\/\d+)?(\?|$)/.test(path)
}

export async function backendFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const url = `/api/backend${path.startsWith("/") ? path : `/${path}`}`
  const trace = traceStorageEvents(path)
  const t0 = typeof performance !== "undefined" ? performance.now() : 0

  if (trace) {
    storageApiLog("fetch.start", { path, method: init?.method ?? "GET" })
  }

  let res: Response
  try {
    res = await fetch(url, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    })
  } catch (err) {
    if (trace) {
      storageApiLog(
        "fetch.network_error",
        {
          path,
          elapsedMs: Math.round(performance.now() - t0),
          error: err instanceof Error ? err.message : String(err),
        },
        "error"
      )
    }
    throw err
  }

  const text = await res.text()
  const bodyBytes = new TextEncoder().encode(text).length
  let data: unknown = null
  let parseError: string | undefined
  if (text) {
    try {
      data = JSON.parse(text)
    } catch (e) {
      parseError = e instanceof Error ? e.message : String(e)
      data = text
    }
  }

  if (trace) {
    storageApiLog(
      res.ok ? "fetch.response" : "fetch.http_error",
      {
        path,
        status: res.status,
        bodyBytes,
        elapsedMs: Math.round(performance.now() - t0),
        parseError,
        isHtml: text.trimStart().startsWith("<!"),
        preview: text.slice(0, 120),
      },
      res.ok ? "log" : "error"
    )
  }

  if (!res.ok) {
    const detail =
      typeof data === "object" &&
      data !== null &&
      "detail" in data &&
      typeof (data as { detail: unknown }).detail === "string"
        ? (data as { detail: string }).detail
        : res.statusText
    throw new ApiError(res.status, detail, data)
  }

  if (parseError) {
    storageApiLog("fetch.json_parse_failed", { path, parseError, bodyBytes }, "error")
    throw new ApiError(500, "Invalid JSON from API proxy", { parseError, preview: text.slice(0, 200) })
  }

  return data as T
}
