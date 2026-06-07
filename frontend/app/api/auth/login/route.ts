import { NextResponse } from "next/server"

import { authLogServer } from "@/lib/auth/auth-log"
import { validateDemoCredentials } from "@/lib/auth/demo-credentials"
import { createSession, SESSION_COOKIE } from "@/lib/auth/session"

function cookieSecure(request: Request): boolean {
  if (process.env.NODE_ENV !== "production") return false
  try {
    return new URL(request.url).protocol === "https:"
  } catch {
    return false
  }
}

export async function POST(request: Request) {
  const reqId = crypto.randomUUID().slice(0, 8)
  authLogServer("login.request", {
    reqId,
    contentType: request.headers.get("content-type"),
    host: request.headers.get("host"),
    origin: request.headers.get("origin"),
  })

  let username = ""
  let password = ""

  try {
    const contentType = request.headers.get("content-type") || ""
    if (contentType.includes("application/json")) {
      const body = (await request.json()) as {
        username?: string
        email?: string
        password?: string
      }
      username = (body.username ?? body.email ?? "").trim()
      password = body.password ?? ""
    } else {
      const form = await request.formData()
      username = String(form.get("username") ?? form.get("email") ?? "").trim()
      password = String(form.get("password") ?? "")
    }
  } catch (err) {
    authLogServer(
      "login.parse_failed",
      { reqId, error: err instanceof Error ? err.message : String(err) },
      "error"
    )
    return NextResponse.json({ detail: "Invalid request body" }, { status: 400 })
  }

  authLogServer("login.parsed", {
    reqId,
    username,
    passwordLen: password.length,
  })

  if (!username || !password) {
    authLogServer("login.missing_fields", { reqId }, "warn")
    return NextResponse.json({ detail: "Username and password are required" }, { status: 400 })
  }

  if (!validateDemoCredentials(username, password)) {
    authLogServer("login.invalid_credentials", { reqId, username }, "warn")
    return NextResponse.json({ detail: "Invalid username or password" }, { status: 401 })
  }

  let token: string
  try {
    token = await createSession(username)
  } catch (err) {
    authLogServer(
      "login.session_create_failed",
      { reqId, error: err instanceof Error ? err.message : String(err) },
      "error"
    )
    return NextResponse.json({ detail: "Could not create session" }, { status: 500 })
  }

  const secure = cookieSecure(request)
  authLogServer("login.success", {
    reqId,
    username,
    cookieSecure: secure,
    nodeEnv: process.env.NODE_ENV,
  })

  const response = NextResponse.json({ ok: true, username })
  response.cookies.set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure,
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  })
  return response
}
