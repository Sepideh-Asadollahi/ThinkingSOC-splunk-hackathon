export const SESSION_COOKIE = "tsoc_session"

export type SessionPayload = {
  username: string
  exp: number
}

function getSecret(): string {
  return process.env.AUTH_SECRET || "thinking-soc-hackathon-dev-secret"
}

function toBase64Url(bytes: Uint8Array): string {
  let binary = ""
  for (const b of bytes) binary += String.fromCharCode(b)
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "")
}

function fromBase64Url(value: string): Uint8Array {
  const padded = value.replace(/-/g, "+").replace(/_/g, "/")
  const pad = padded.length % 4 === 0 ? "" : "=".repeat(4 - (padded.length % 4))
  const binary = atob(padded + pad)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes
}

async function hmacSign(data: string): Promise<string> {
  const enc = new TextEncoder()
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(getSecret()),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  )
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(data))
  return toBase64Url(new Uint8Array(sig))
}

async function hmacVerify(data: string, sig: string): Promise<boolean> {
  const enc = new TextEncoder()
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(getSecret()),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["verify"]
  )
  try {
    const sigBytes = new Uint8Array(fromBase64Url(sig))
    return crypto.subtle.verify("HMAC", key, sigBytes, enc.encode(data))
  } catch {
    return false
  }
}

export async function signSession(payload: SessionPayload): Promise<string> {
  const body = toBase64Url(new TextEncoder().encode(JSON.stringify(payload)))
  const sig = await hmacSign(body)
  return `${body}.${sig}`
}

export async function verifySession(
  token: string | undefined
): Promise<SessionPayload | null> {
  if (!token) return null
  const [body, sig] = token.split(".")
  if (!body || !sig) return null
  if (!(await hmacVerify(body, sig))) return null
  try {
    const json = new TextDecoder().decode(fromBase64Url(body))
    const payload = JSON.parse(json) as SessionPayload & { email?: string }
    const username = payload.username ?? payload.email
    if (!username || !payload.exp) return null
    if (Date.now() > payload.exp) return null
    return { username, exp: payload.exp }
  } catch {
    return null
  }
}

export async function createSession(username: string, maxAgeSeconds = 60 * 60 * 24 * 7) {
  return signSession({
    username,
    exp: Date.now() + maxAgeSeconds * 1000,
  })
}
