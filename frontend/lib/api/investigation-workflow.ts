import { backendFetch } from "@/lib/api/client"

export type InvestigationTimelineStep = {
  record_id: number | null
  record_type: string
  title: string
  description: string
  detail: string | null
  created_at: unknown
  is_current_record: boolean
  is_analyst_action: boolean
}

export type InvestigationTimelineResponse = {
  record_id: number
  found: boolean
  sid: string | null
  search_name: string | null
  row_index?: number | null
  postgres_configured?: boolean
  steps: InvestigationTimelineStep[]
}

export type AnalystActionEntry = {
  id: number | null
  created_at: unknown
  action: string | null
  note: string | null
  recommended_step: string | null
  investigation_record_id: number | string | null
}

export type AnalystActionsResponse = {
  record_id: number
  count: number
  results: AnalystActionEntry[]
}

export type PostAnalystActionResponse = {
  record_id: number
  saved: { ok: boolean; event?: Record<string, unknown> }
  latest: AnalystActionEntry | null
  results: AnalystActionEntry[]
}

export async function fetchInvestigationTimeline(
  recordId: string | number
): Promise<InvestigationTimelineResponse> {
  return backendFetch<InvestigationTimelineResponse>(
    `/investigation/records/${encodeURIComponent(String(recordId))}/timeline`
  )
}

export async function fetchAnalystActions(
  recordId: string | number
): Promise<AnalystActionsResponse> {
  return backendFetch<AnalystActionsResponse>(
    `/investigation/records/${encodeURIComponent(String(recordId))}/analyst-actions`
  )
}

export type InvestigationWorkflowExport = {
  event_timeline: InvestigationTimelineResponse | null
  analyst_actions: AnalystActionsResponse | null
  fetch_errors: string[]
}

/** Load timeline + analyst gate for JSON export (best-effort; export still succeeds on partial failure). */
export async function fetchInvestigationWorkflowForExport(
  recordId: string | number
): Promise<InvestigationWorkflowExport> {
  const fetch_errors: string[] = []
  let event_timeline: InvestigationTimelineResponse | null = null
  let analyst_actions: AnalystActionsResponse | null = null

  await Promise.all([
    fetchInvestigationTimeline(recordId)
      .then((data) => {
        event_timeline = data
      })
      .catch((e) => {
        fetch_errors.push(
          e instanceof Error ? e.message : "Failed to load event timeline for export"
        )
      }),
    fetchAnalystActions(recordId)
      .then((data) => {
        analyst_actions = data
      })
      .catch((e) => {
        fetch_errors.push(
          e instanceof Error ? e.message : "Failed to load analyst actions for export"
        )
      }),
  ])

  return { event_timeline, analyst_actions, fetch_errors }
}

export async function postAnalystAction(
  recordId: string | number,
  body: { action: "acknowledge" | "escalate"; note?: string }
): Promise<PostAnalystActionResponse> {
  return backendFetch<PostAnalystActionResponse>(
    `/investigation/records/${encodeURIComponent(String(recordId))}/analyst-actions`,
    {
      method: "POST",
      body: JSON.stringify(body),
    }
  )
}
