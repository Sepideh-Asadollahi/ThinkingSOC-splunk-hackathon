import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

import { authLogServer } from "@/lib/auth/auth-log"
import { getHomeRedirectPath } from "@/lib/auth/home-redirect"
import { SESSION_COOKIE, verifySession } from "@/lib/auth/session"

const PROTECTED_PREFIXES = [
  "/dashboard",
  "/inventory",
  "/relationships",
  "/analysis",
  "/triage",
  "/runbooks",
  "/splunk-connection",
]

function isProtected(pathname: string) {
  return PROTECTED_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`)
  )
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl
  const cookiePresent = !!request.cookies.get(SESSION_COOKIE)?.value
  const session = await verifySession(request.cookies.get(SESSION_COOKIE)?.value)
  const hasSession = !!session

  const logAuth = pathname === "/login" || pathname.startsWith("/dashboard") || isProtected(pathname)

  if (logAuth) {
    authLogServer("proxy.check", {
      pathname,
      cookiePresent,
      hasSession,
      username: session?.username,
    })
  }

  if (pathname === "/" || pathname === "") {
    const url = request.nextUrl.clone()
    url.pathname = getHomeRedirectPath(hasSession)
    url.search = ""
    authLogServer("proxy.redirect", { from: pathname, to: url.pathname, hasSession })
    return NextResponse.redirect(url)
  }

  if (pathname === "/login" && hasSession) {
    const url = request.nextUrl.clone()
    url.pathname = "/dashboard"
    authLogServer("proxy.redirect", { from: "/login", to: "/dashboard", reason: "already_signed_in" })
    return NextResponse.redirect(url)
  }

  if (isProtected(pathname) && !hasSession) {
    const url = request.nextUrl.clone()
    url.pathname = "/login"
    url.search = ""
    authLogServer(
      "proxy.redirect",
      { from: pathname, to: "/login", reason: "no_session", cookiePresent },
      "warn"
    )
    return NextResponse.redirect(url)
  }

  if (pathname.startsWith("/api/backend") && !hasSession) {
    authLogServer("proxy.block", { pathname, reason: "no_session" }, "warn")
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 })
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    "/",
    "/login",
    "/dashboard",
    "/dashboard/:path*",
    "/inventory",
    "/inventory/:path*",
    "/relationships",
    "/relationships",
    "/relationships/:path*",
    "/analysis",
    "/analysis/:path*",
    "/triage",
    "/triage/:path*",
    "/runbooks",
    "/runbooks/:path*",
    "/splunk-connection",
    "/splunk-connection/:path*",
    "/api/backend/:path*",
  ],
}
