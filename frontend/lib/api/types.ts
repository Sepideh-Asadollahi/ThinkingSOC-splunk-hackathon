export type UserRecord = {
  user_id: string
  display_name?: string | null
  email?: string | null
  department?: string | null
  risk_score: number
  description?: string | null
}

export type AssetRecord = {
  asset_id: string
  asset_type: string
  hostname?: string | null
  fqdn?: string | null
  ip?: string | null
  owner?: string | null
  criticality: "low" | "medium" | "high" | "critical"
  risk_score: number
  description?: string | null
}

export type RelationshipRecord = {
  relationship_id: string
  user_id: string
  asset_id: string
  description?: string | null
}

export type EnrichmentResult = {
  resolved_user_id?: string | null
  resolved_asset_id?: string | null
  confidence: "high" | "medium" | "low"
  notes: string
  matched_relationship_ids?: string[]
}

export type StorageEventsResponse = {
  postgres_configured: boolean
  count: number
  results: Record<string, unknown>[]
}

export type TriageFactor = {
  title: string
  explanation: string
  score_impact?: number | null
}

export type TriageReport = {
  headline: string
  why_verdict: string
  why_priority: string
  recommended_action: string
  factors?: TriageFactor[]
  signal_notes?: string[]
}

export type TriageOutcome = {
  review_verdict: "TRUE_POSITIVE" | "FALSE_POSITIVE" | "NEEDS_HUMAN_REVIEW"
  investigation_priority: "critical" | "high" | "medium" | "low"
  triage_score: number
  confidence_score: number
  priority_rationale: string
  signals: string[]
  needs_human_review: boolean
  source_track: "security" | "observability"
  mapped_from?: Record<string, string>
  report?: TriageReport | null
}

export type TriageQueueItem = {
  id?: number | string
  stored_at?: string | null
  tsoc_record_type?: string
  sid?: string | null
  search_name?: string | null
  row_index?: number | null
  source_track?: string
  triage_score?: number
  investigation_priority?: string
  review_verdict?: string
  needs_human_review?: boolean
  triage?: TriageOutcome
}

export type TriageQueueResponse = {
  postgres_configured: boolean
  track: string
  count: number
  results: TriageQueueItem[]
}

export type StoredEventRecord = {
  id: number
  created_at?: string | null
  tsoc_record_type?: string | null
  sid?: string | null
  search_name?: string | null
  row_index?: number | null
  payload: Record<string, unknown>
}

export type AnalysisRouteRequest = {
  normalized?: Record<string, unknown>
  search_name?: string
  sid?: string
  splunk_results?: Record<string, unknown>[]
}

export type LlmStatus = {
  litellm_model?: string | null
  litellm_api_key_configured: boolean
  litellm_api_base_configured: boolean
}

export type McpStatusResponse = {
  configured: boolean
  connected?: boolean
  url?: string | null
  server_info?: Record<string, unknown>
  tools?: string[]
  saia_available?: boolean
  message?: string | null
}

/** @deprecated Use McpStatusResponse */
export type McpStatus = McpStatusResponse

export type DashboardKpis = {
  total_records: number
  analyses_24h: number
  needs_human_review: number
  avg_triage_score: number
  users: number
  assets: number
}

export type ActivityTimelinePoint = {
  date: string
  security: number
  observability: number
  correlation: number
  other: number
}

export type CountByType = {
  type: string
  count: number
}

export type CountByVerdict = {
  verdict: string
  count: number
}

export type CountByPriority = {
  priority: string
  count: number
}

export type TrackSplit = {
  security: number
  observability: number
}

export type DashboardIntegrations = {
  postgres: boolean
  llm: boolean
  mcp: boolean
  neo4j: boolean
}

export type TopPriorityItem = {
  id?: number | null
  stored_at?: string | null
  tsoc_record_type?: string | null
  sid?: string | null
  search_name?: string | null
  row_index?: number | null
  source_track?: string | null
  triage_score?: number
  investigation_priority?: string | null
  review_verdict?: string | null
  needs_human_review?: boolean
}

export type SystemResources = {
  hostname: string
  cpu_percent: number
  memory_percent: number
  memory_used_bytes: number
  memory_total_bytes: number
}

export type DashboardOverview = {
  generated_at: string
  postgres_configured: boolean
  system_resources: SystemResources
  kpis: DashboardKpis
  activity_timeline: ActivityTimelinePoint[]
  record_type_counts: CountByType[]
  triage_by_verdict: CountByVerdict[]
  triage_by_priority: CountByPriority[]
  track_split: TrackSplit
  integrations: DashboardIntegrations
  health_score: number
  top_priority: TopPriorityItem[]
}

export type SettingCategory =
  | "splunk_rest"
  | "splunk_mcp"
  | "litellm"
  | "postgres"
  | "virustotal"
  | "ingest"
  | "analysis"
  | "custom"

export type IntegrationSettingRecord = {
  id: string
  category: SettingCategory
  key: string
  value: string
  description?: string | null
  is_secret: boolean
  builtin: boolean
  env_var?: string | null
  configured: boolean
}
