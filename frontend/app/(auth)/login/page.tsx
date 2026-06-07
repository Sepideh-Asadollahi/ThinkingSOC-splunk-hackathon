import { Suspense } from "react"

import { LoginForm } from "@/components/login-form"
import { StarsBackground } from "@/components/animate-ui/components/backgrounds/stars"

export default function LoginPage() {
  return (
    <div className="relative flex min-h-svh w-full items-center justify-center p-6 md:p-10">
      <StarsBackground className="absolute inset-0" starColor="#5eead4" />
      <div className="relative z-10 w-full max-w-md">
        <Suspense fallback={<div className="h-64 animate-pulse rounded-xl bg-white/5" />}>
          <LoginForm />
        </Suspense>
      </div>
    </div>
  )
}
