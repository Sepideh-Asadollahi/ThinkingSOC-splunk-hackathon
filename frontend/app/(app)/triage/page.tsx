import { redirect } from "next/navigation"

/** Triage queue is integrated into Analysis — keep URL for bookmarks. */
export default function TriageRedirectPage() {
  redirect("/analysis")
}
