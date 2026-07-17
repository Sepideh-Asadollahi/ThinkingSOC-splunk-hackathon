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

export type RunbookStep = {
  step_id: string
  title: string
  intent: string
  expected_evidence: string
  stop_condition: string
}

export type RunbookSplResult = {
  row_count: number
  rows: Record<string, unknown>[]
  truncated: boolean
  error: string | null
  execution_transport?: "mcp" | "rest" | null
}

export type RunbookSourceResult = {
  question: string
  spl: string
  explanation: string
  time_window: string
  pivots: string[]
  notes: string[]
  validation: {
    method: "splunk_parser" | "skipped"
    valid: boolean | null
    message: string | null
  } | null
  spl_results: RunbookSplResult | null
  spl_results_analysis?: Record<string, unknown> | null
}

export type VerifiedRunbookDraft = {
  runbook_id: string
  source_record_id: number
  title: string
  summary: string
  applicable_search_name: string
  source_verdict: string
  steps: RunbookStep[]
  decision_rule: string
  limitations: string[]
  source_results: RunbookSourceResult[]
  status: "DRAFT" | "PARSER_VALID" | "SOURCE_VERIFIED" | "FAILED"
  configured_model: string | null
  model: string
  prompt_tokens: number | null
  completion_tokens: number | null
  generation_duration_ms: number
  verification_duration_ms: number
  compile_duration_ms: number
  parser_valid_step_count: number
  successful_step_count: number
  total_evidence_rows: number
  revision: number
  parent_runbook_id: string | null
  origin: "compiled" | "edited" | "imported"
  revision_note: string | null
  edited_by: string | null
  imported_from_runbook_id: string | null
  created_at: string
}

export type RunbookApproval = {
  runbook_id: string
  source_record_id: number
  decision: "approve" | "reject"
  analyst: string
  note: string | null
  created_at: string
}

export type RunbookRun = {
  runbook_id: string
  source_record_id: number
  target_record_id: number
  status: "REUSED" | "NO_EVIDENCE" | "FAILED"
  results: RunbookSourceResult[]
  duration_ms: number
  estimated_manual_minutes: number
  estimated_minutes_saved: number
  savings_percent: number
  successful_step_count: number
  total_evidence_rows: number
  created_at: string
}

export type RunbookShadowRun = {
  shadow_run_id: string
  runbook_id: string
  source_record_id: number
  target_record_id: number
  source_sid: string | null
  target_sid: string | null
  search_name: string
  status: "EVIDENCE_FOUND" | "NO_EVIDENCE" | "FAILED"
  results: RunbookSourceResult[]
  duration_ms: number
  estimated_manual_minutes: number
  projected_minutes_saved: number
  projected_labor_savings_usd: number
  parser_valid_step_count: number
  successful_step_count: number
  total_evidence_rows: number
  execution_error_count: number
  failure_reason: string | null
  created_at: string
}

export type RunbookShadowRunSummary = Omit<RunbookShadowRun, "results" | "source_sid" | "estimated_manual_minutes">

export type SafeResponseAction = {
  action_id: string
  action_type:
    | "ISOLATE_ENDPOINT"
    | "DISABLE_ACCOUNT"
    | "REVOKE_SESSIONS"
    | "BLOCK_INDICATOR"
    | "QUARANTINE_FILE"
    | "COLLECT_FORENSICS"
    | "ESCALATE_INCIDENT"
    | "MONITOR_ONLY"
  title: string
  target_type: "endpoint" | "identity" | "ip" | "domain" | "file" | "incident"
  target: string
  risk_level: "low" | "medium" | "high" | "critical"
  rationale: string
  prerequisites: string[]
  expected_effect: string
  rollback_plan: string
  verification_steps: string[]
  requires_human_approval: true
  execution_mode: "PREVIEW_ONLY"
}

export type SafeResponsePreview = {
  preview_id: string
  runbook_id: string
  source_record_id: number
  source_verdict: string
  status: "READY_FOR_REVIEW"
  evidence_basis: "SOURCE_EVIDENCE" | "ANALYSIS_ONLY"
  actions: SafeResponseAction[]
  decision_summary: string
  limitations: string[]
  configured_model: string | null
  model: string
  prompt_tokens: number | null
  completion_tokens: number | null
  generation_duration_ms: number
  execution_supported: false
  created_at: string
}

export type SafeResponseDecision = {
  preview_id: string
  runbook_id: string
  source_record_id: number
  decision: "approve_for_manual_action" | "reject"
  analyst: string
  note: string | null
  automatic_execution_performed: false
  created_at: string
}

export type RunbookAutopilotEvent = {
  event_id: string
  sequence: number
  agent: "SUPERVISOR" | "EVIDENCE_SCOUT" | "RUNBOOK_ENGINEER" | "POLICY_GUARD" | "RESPONSE_ADVISOR"
  kind: "AGENT_STARTED" | "HANDOFF" | "TOOL_CALL" | "TOOL_RESULT" | "POLICY_DECISION" | "AGENT_COMPLETED"
  status: "RUNNING" | "SUCCEEDED" | "BLOCKED" | "FAILED"
  summary: string
  tool_name: string | null
  duration_ms: number
  metadata: Record<string, unknown>
  created_at: string
}

export type RunbookAutopilotSession = {
  session_id: string
  source_record_id: number
  objective: string
  mode: "ASSESS" | "ADVANCE"
  status: "COMPLETED" | "AWAITING_HUMAN_APPROVAL" | "BLOCKED" | "FAILED"
  agents: string[]
  tools_used: string[]
  trace: RunbookAutopilotEvent[]
  runbook_id: string | null
  runbook_status: string | null
  response_preview_id: string | null
  next_recommended_action: string
  human_approval_required: true
  automatic_execution_performed: false
  started_at: string
  completed_at: string
  duration_ms: number
}

export type RunbookEvaluation = {
  generated_at: string
  revision_count: number
  alert_count: number
  latest_runbook_count: number
  approved_runbook_count: number
  production_run_count: number
  shadow_run_count: number
  source_verified_revision_count: number
  parser_valid_revision_count: number
  failed_revision_count: number
  total_step_count: number
  parser_valid_step_count: number
  parser_valid_rate: number
  shadow_evidence_run_count: number
  evidence_coverage_rate: number
  total_shadow_evidence_rows: number
  total_execution_errors: number
  average_compile_duration_ms: number
  average_shadow_duration_ms: number
  projected_minutes_saved: number
  projected_labor_savings_usd: number
  realized_minutes_saved: number
  total_prompt_tokens: number
  total_completion_tokens: number
  estimated_compile_llm_cost_usd: number
  analyst_hourly_cost_usd: number
  shadow_status_breakdown: Record<string, number>
  recent_shadow_runs: RunbookShadowRunSummary[]
}

export type RunbookRuntimeStatus = {
  enabled: boolean
  autopilot_enabled: boolean
  ready: boolean
  configured_model: string
  max_steps: number
  default_manual_minutes: number
  artifact_scan_limit: number
  postgres_configured: boolean
  llm_configured: boolean
  splunk_configured: boolean
  mcp_configured: boolean
  rest_api_configured: boolean
  execution_transport_policy: "mcp_then_rest"
  execution_enabled: boolean
  acknowledgment_required: true
  exact_search_name_required: true
  source_evidence_required: true
}

export type VerifiedRunbookState = {
  record_id: number
  draft: VerifiedRunbookDraft | null
  latest_approval: RunbookApproval | null
  latest_run: RunbookRun | null
  latest_response_preview: SafeResponsePreview | null
  latest_response_decision: SafeResponseDecision | null
}

export type RunbookCompatibleTarget = {
  record_id: number
  created_at: string | null
  sid: string | null
  search_name: string
  row_index: number | null
  summary: string | null
  review_verdict: string | null
}

export type RunbookCompatibleTargets = {
  source_record_id: number
  search_name: string
  count: number
  results: RunbookCompatibleTarget[]
}

export type RunbookLibraryItem = {
  draft: VerifiedRunbookDraft
  latest_approval: RunbookApproval | null
  latest_run: RunbookRun | null
  is_latest_for_source: boolean
}

export type RunbookLibraryGroup = {
  alert_name: string
  count: number
  runbooks: RunbookLibraryItem[]
}

export type RunbookLibraryResponse = {
  count: number
  alert_count: number
  groups: RunbookLibraryGroup[]
}

export type PortableRunbook = Pick<
  VerifiedRunbookDraft,
  | "title"
  | "summary"
  | "applicable_search_name"
  | "steps"
  | "decision_rule"
  | "limitations"
  | "source_verdict"
  | "revision"
  | "created_at"
> & {
  original_runbook_id: string | null
  original_source_record_id: number | null
}

export type RunbookExportBundle = {
  schema_version: "thinking-soc.runbook-library/v1"
  exported_at: string
  runbooks: PortableRunbook[]
}

export type RunbookImportResponse = {
  imported_count: number
  runbooks: VerifiedRunbookDraft[]
}

export type RunbookRevisionInput = {
  title: string
  summary: string
  applicable_search_name: string
  steps: RunbookStep[]
  decision_rule: string
  limitations: string[]
  source_record_id?: number
  verify_on_source: boolean
  revision_note?: string
  editor?: string
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
  verified_runbook: VerifiedRunbookState | null
  fetch_errors: string[]
}

/** Load timeline, analyst gate, and Forge state for a best-effort JSON export. */
export async function fetchInvestigationWorkflowForExport(
  recordId: string | number
): Promise<InvestigationWorkflowExport> {
  const fetch_errors: string[] = []
  let event_timeline: InvestigationTimelineResponse | null = null
  let analyst_actions: AnalystActionsResponse | null = null
  let verified_runbook: VerifiedRunbookState | null = null

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
    fetchVerifiedRunbook(recordId)
      .then((data) => {
        verified_runbook = data
      })
      .catch((e) => {
        fetch_errors.push(
          e instanceof Error ? e.message : "Failed to load verified runbook for export"
        )
      }),
  ])

  return { event_timeline, analyst_actions, verified_runbook, fetch_errors }
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

export async function fetchVerifiedRunbook(
  recordId: string | number
): Promise<VerifiedRunbookState> {
  return backendFetch<VerifiedRunbookState>(
    `/investigation/records/${encodeURIComponent(String(recordId))}/runbook`
  )
}

export async function fetchRunbookAutopilot(
  recordId: string | number
): Promise<{ record_id: number; latest_session: RunbookAutopilotSession | null }> {
  return backendFetch(
    `/investigation/records/${encodeURIComponent(String(recordId))}/runbook/autopilot`
  )
}

export async function runRunbookAutopilot(
  recordId: string | number,
  body: {
    objective?: string
    mode?: "ASSESS" | "ADVANCE"
    generate_response_preview?: boolean
  } = {}
): Promise<RunbookAutopilotSession> {
  return backendFetch<RunbookAutopilotSession>(
    `/investigation/records/${encodeURIComponent(String(recordId))}/runbook/autopilot`,
    { method: "POST", body: JSON.stringify(body) }
  )
}

export async function fetchRunbookRuntimeStatus(): Promise<RunbookRuntimeStatus> {
  return backendFetch<RunbookRuntimeStatus>("/investigation/runbook-settings")
}

export async function fetchCompatibleRunbookTargets(
  sourceRecordId: string | number,
  limit = 12
): Promise<RunbookCompatibleTargets> {
  const recordId = encodeURIComponent(String(sourceRecordId))
  return backendFetch<RunbookCompatibleTargets>(
    `/investigation/records/${recordId}/runbook/compatible-targets?limit=${encodeURIComponent(String(limit))}`
  )
}

export async function buildVerifiedRunbook(
  recordId: string | number,
  options: { rebuild?: boolean } = {}
): Promise<VerifiedRunbookDraft> {
  const query = options.rebuild === false ? "?rebuild=false" : ""
  return backendFetch<VerifiedRunbookDraft>(
    `/investigation/records/${encodeURIComponent(String(recordId))}/runbook${query}`,
    { method: "POST" }
  )
}

export async function decideVerifiedRunbook(
  recordId: string | number,
  body: {
    runbook_id: string
    decision: "approve" | "reject"
    note?: string
    analyst?: string
  }
): Promise<RunbookApproval> {
  return backendFetch<RunbookApproval>(
    `/investigation/records/${encodeURIComponent(String(recordId))}/runbook/approval`,
    { method: "POST", body: JSON.stringify(body) }
  )
}

export async function buildSafeResponsePreview(
  recordId: string | number,
  body: { runbook_id: string }
): Promise<SafeResponsePreview> {
  return backendFetch<SafeResponsePreview>(
    `/investigation/records/${encodeURIComponent(String(recordId))}/runbook/response-preview`,
    { method: "POST", body: JSON.stringify(body) }
  )
}

export async function decideSafeResponsePreview(
  recordId: string | number,
  body: {
    preview_id: string
    decision: "approve_for_manual_action" | "reject"
    note?: string
    analyst?: string
  }
): Promise<SafeResponseDecision> {
  return backendFetch<SafeResponseDecision>(
    `/investigation/records/${encodeURIComponent(String(recordId))}/runbook/response-preview/decision`,
    { method: "POST", body: JSON.stringify(body) }
  )
}

export async function runVerifiedRunbook(
  targetRecordId: string | number,
  body: {
    source_record_id: number
    runbook_id: string
    estimated_manual_minutes: number
  }
): Promise<RunbookRun> {
  return backendFetch<RunbookRun>(
    `/investigation/records/${encodeURIComponent(String(targetRecordId))}/runbook-runs`,
    { method: "POST", body: JSON.stringify(body) }
  )
}

export async function runShadowReplay(
  targetRecordId: string | number,
  body: {
    source_record_id: number
    runbook_id: string
    estimated_manual_minutes: number
  }
): Promise<RunbookShadowRun> {
  return backendFetch<RunbookShadowRun>(
    `/investigation/records/${encodeURIComponent(String(targetRecordId))}/runbook-shadow-runs`,
    { method: "POST", body: JSON.stringify(body) }
  )
}

export async function fetchRunbookEvaluation(): Promise<RunbookEvaluation> {
  return backendFetch<RunbookEvaluation>("/investigation/runbook-evaluations")
}

export async function fetchRunbookLibrary(
  searchName?: string
): Promise<RunbookLibraryResponse> {
  const query = searchName
    ? `?search_name=${encodeURIComponent(searchName)}`
    : ""
  return backendFetch<RunbookLibraryResponse>(`/investigation/runbooks${query}`)
}

export async function exportRunbooks(filters?: {
  runbookId?: string
  searchName?: string
}): Promise<RunbookExportBundle> {
  const params = new URLSearchParams()
  if (filters?.runbookId) params.set("runbook_id", filters.runbookId)
  if (filters?.searchName) params.set("search_name", filters.searchName)
  const query = params.toString()
  return backendFetch<RunbookExportBundle>(
    `/investigation/runbooks/export${query ? `?${query}` : ""}`
  )
}

export async function importRunbooks(body: {
  document: RunbookExportBundle
  source_record_id?: number
  verify_on_source?: boolean
  imported_by?: string
  note?: string
}): Promise<RunbookImportResponse> {
  return backendFetch<RunbookImportResponse>("/investigation/runbooks/import", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export async function reviseRunbook(
  runbookId: string,
  body: RunbookRevisionInput
): Promise<VerifiedRunbookDraft> {
  return backendFetch<VerifiedRunbookDraft>(
    `/investigation/runbooks/${encodeURIComponent(runbookId)}`,
    { method: "PATCH", body: JSON.stringify(body) }
  )
}
