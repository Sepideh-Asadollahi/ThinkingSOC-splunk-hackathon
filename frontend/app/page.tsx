import { cookies } from "next/headers"
import { redirect } from "next/navigation"

import { getHomeRedirectPath } from "@/lib/auth/home-redirect"
import { SESSION_COOKIE, verifySession } from "@/lib/auth/session"

export const dynamic = "force-dynamic"

export default async function Home() {
  const cookieStore = await cookies()
  const session = await verifySession(cookieStore.get(SESSION_COOKIE)?.value)
  redirect(getHomeRedirectPath(!!session))
}
