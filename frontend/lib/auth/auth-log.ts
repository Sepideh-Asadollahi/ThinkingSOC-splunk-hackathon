/** Structured auth debug logs — browser DevTools + Next.js server terminal. */

const PREFIX = "[tsoc/auth]"

export type AuthLogMeta = Record<string, unknown>

function formatMeta(meta?: AuthLogMeta): string {
  if (!meta || Object.keys(meta).length === 0) return ""
  try {
    return ` ${JSON.stringify(meta)}`
  } catch {
    return " [meta unserializable]"
  }
}

export function authLog(
  step: string,
  meta?: AuthLogMeta,
  level: "log" | "warn" | "error" = "log"
): void {
  const msg = `${PREFIX} ${step}${formatMeta(meta)}`
  if (level === "error") console.error(msg)
  else if (level === "warn") console.warn(msg)
  else console.log(msg)
}

export function authLogServer(step: string, meta?: AuthLogMeta, level: "log" | "warn" | "error" = "log"): void {
  authLog(step, { ...meta, side: "server" }, level)
}

export function authLogClient(step: string, meta?: AuthLogMeta, level: "log" | "warn" | "error" = "log"): void {
  if (typeof window === "undefined") return
  authLog(step, { ...meta, side: "client" }, level)
}
