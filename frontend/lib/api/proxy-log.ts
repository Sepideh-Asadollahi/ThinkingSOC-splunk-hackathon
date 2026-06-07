/** Structured logs for Next.js → FastAPI proxy (server terminal). */

const PREFIX = "[tsoc/proxy]"

export type ProxyLogMeta = Record<string, unknown>

function formatMeta(meta?: ProxyLogMeta): string {
  if (!meta || Object.keys(meta).length === 0) return ""
  try {
    return ` ${JSON.stringify(meta)}`
  } catch {
    return " [meta unserializable]"
  }
}

export function proxyLog(
  step: string,
  meta?: ProxyLogMeta,
  level: "log" | "warn" | "error" = "log"
): void {
  const msg = `${PREFIX} ${step}${formatMeta(meta)}`
  if (level === "error") console.error(msg)
  else if (level === "warn") console.warn(msg)
  else console.log(msg)
}
