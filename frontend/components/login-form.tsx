"use client"

import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import { ShieldIcon } from "lucide-react"

import { authLogClient } from "@/lib/auth/auth-log"
import {
  DEFAULT_DEMO_PASSWORD,
  DEFAULT_DEMO_USERNAME,
} from "@/lib/auth/demo-credentials"
import {
  NeonActionButton,
  NeonField,
  NeonFieldGroup,
  NeonFieldLabel,
  NeonGlassCard,
  NeonCardHeader,
  NeonInput,
} from "@/components/neon-glass"
import { cn } from "@/lib/utils"

export function LoginForm({
  className,
  ...props
}: React.ComponentProps<"div">) {
  const searchParams = useSearchParams()
  const [username, setUsername] = useState(DEFAULT_DEMO_USERNAME)
  const [password, setPassword] = useState(DEFAULT_DEMO_PASSWORD)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [debugHint, setDebugHint] = useState<string | null>(null)

  useEffect(() => {
    authLogClient("login.mount", {
      href: typeof window !== "undefined" ? window.location.href : "",
      from: searchParams.get("from"),
    })
  }, [searchParams])

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    authLogClient("form.submit", {
      usernameLen: username.length,
      passwordLen: password.length,
      from: searchParams.get("from"),
    })
    setLoading(true)
    setError(null)
    setDebugHint(null)
    const started = Date.now()
    try {
      authLogClient("fetch.start", { url: "/api/auth/login" })
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ username, password }),
      })
      authLogClient("fetch.done", {
        status: res.status,
        ok: res.ok,
        durationMs: Date.now() - started,
        setCookie: res.headers.get("set-cookie") ? "present" : "missing",
      })
      if (!res.ok) {
        const data = (await res.json().catch((parseErr) => {
          authLogClient("fetch.json_parse_failed", { message: String(parseErr) }, "warn")
          return {}
        })) as { detail?: string }
        const msg = data.detail || `Login failed (HTTP ${res.status})`
        authLogClient("login.rejected", { status: res.status, detail: msg }, "warn")
        setError(msg)
        setDebugHint(`Server returned ${res.status}. Check terminal running npm run dev.`)
        return
      }
      const data = (await res.json().catch(() => ({}))) as { ok?: boolean; username?: string }
      authLogClient("login.ok", { username: data.username })
      const target = "/dashboard"
      authLogClient("navigate.start", { target })
      setDebugHint(`Signed in — redirecting to ${target}…`)
      window.location.assign(target)
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      authLogClient("fetch.error", { message }, "error")
      setError("Network error")
      setDebugHint(message || "Request failed before reaching the server.")
    } finally {
      setLoading(false)
    }
  }

  function onSignInClick() {
    authLogClient("button.click", { loading, type: "submit" })
  }

  return (
    <div className={cn("flex w-full max-w-md flex-col gap-6", className)} {...props}>
      <NeonGlassCard accent="teal" animatePreset="page">
        <NeonCardHeader
          accent="teal"
          icon={<ShieldIcon className="size-5 text-teal-400" />}
          title="ThinkingSOC"
          description="Splunk Hackathon — analyst console"
        />
        <form onSubmit={onSubmit} className="space-y-4 px-6 pb-6" noValidate>
          <NeonFieldGroup>
            <NeonField>
              <NeonFieldLabel htmlFor="username">Username</NeonFieldLabel>
              <NeonInput
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </NeonField>
            <NeonField>
              <NeonFieldLabel htmlFor="password">Password</NeonFieldLabel>
              <NeonInput
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </NeonField>
            {error ? (
              <p className="text-sm text-red-400" role="alert">
                {error}
              </p>
            ) : null}
            {debugHint ? (
              <p className="text-xs text-amber-400/90" data-testid="login-debug-hint">
                {debugHint}
              </p>
            ) : null}
            <NeonActionButton
              accent="teal"
              type="submit"
              className="w-full"
              disabled={loading}
              onClick={onSignInClick}
            >
              {loading ? "Signing in…" : "Sign in"}
            </NeonActionButton>
          </NeonFieldGroup>
        </form>
      </NeonGlassCard>
      <p className="text-center text-xs text-slate-500">
        Default: {DEFAULT_DEMO_USERNAME} / {DEFAULT_DEMO_PASSWORD}
      </p>
    </div>
  )
}
