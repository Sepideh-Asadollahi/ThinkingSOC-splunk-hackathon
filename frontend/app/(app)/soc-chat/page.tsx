import { SocChatContent } from "@/components/pages/soc-chat-content"

export default async function SocChatPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}) {
  const params = await searchParams
  const recordId = typeof params.record_id === "string" ? params.record_id : null
  const runbookId = typeof params.runbook_id === "string" ? params.runbook_id : null
  const initialPrompt = params.context === "runbook"
    ? `Explain the latest Runbook, evidence status, Autopilot agent/tool trace, and next safe action for source record ${recordId ?? "unknown"}${runbookId && runbookId !== "latest" ? ` and Runbook ${runbookId}` : ""}. Cite the Runbook artifacts you use.`
    : ""
  return <SocChatContent initialPrompt={initialPrompt} />
}
