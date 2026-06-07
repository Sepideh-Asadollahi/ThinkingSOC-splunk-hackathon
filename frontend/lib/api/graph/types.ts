export type TicketStatus =
  | "open"
  | "in_progress"
  | "closed"
  | "closed_false_positive"

export interface GraphFindingSummary {
  id: string
  display_id: string
  finding_type: string
  title: string
  summary: string
  risk_score: number
  created_at: string
  ticket_status: TicketStatus
  owner: string
  updated_at: string
  agent_validation_status?: string | null
}

export interface PaginatedGraphFindingsResponse {
  items: GraphFindingSummary[]
  total: number
  limit: number
  offset: number
}

export interface AttackAnalysisStep {
  phase_label: string
  description: string
  mitre_tactic_name?: string
  mitre_technique_id?: string
  mitre_technique_name?: string
}

export interface ContributingAlert {
  alert_row_id: string
  alert_name: string
  sid?: string | null
  search_name?: string | null
  timestamp: string
  threat_status: string
  risk_score: number
}

export interface GraphFindingDetailsObject {
  incident_id: string
  incident_title: string
  executive_summary: string
  attack_analysis_steps?: AttackAnalysisStep[]
  contributing_alerts: ContributingAlert[]
  historical_related_incidents?: {
    incident_id: string
    shared_entity_count: number
  }[]
  key_entities: { identities: string[]; assets: string[]; iocs: string[] }
  attack_timeline_trees?: unknown[]
  framework_mappings?: unknown[]
  recommended_next_steps: string[]
  smart_hunt_queries: unknown[]
  aggregated_mitre_techniques: unknown[]
  raw_analysis: object
  raw_paths: unknown[]
}

export interface GraphFindingDetails extends GraphFindingSummary {
  details: GraphFindingDetailsObject
  notes?: string | null
  status?: string | null
}

export interface OperationStatusResponse {
  operation_id: string
  operation_type: string
  status: "running" | "completed" | "failed" | string
  message: string
  detailed_logs: Array<{
    timestamp?: string
    level?: string
    message: string
  }>
  result_payload?: {
    findings_created?: number
    finding_ids?: string[]
    smart_analysis_summary?: Record<string, unknown>
  } | null
  created_at?: string
  last_updated?: string
}

export type AnalysisType =
  | "smart"
  | "attack_path"
  | "pagerank"
  | "betweenness"
  | "community"

export interface AttackDiscoveryPayload {
  analysis_types: AnalysisType[]
  limit_to_latest_alerts?: number
  start_time?: string
  end_time?: string
  force_reanalysis?: boolean
}

export interface DiscoverAttackPathsResponse {
  message: string
  operation_id: string
}

export interface GraphNode {
  id: string
  label: string
  group: string[]
  properties: Record<string, unknown>
}

export interface GraphEdge {
  id: string
  from: string
  to: string
  label: string
  properties?: Record<string, unknown>
}

export interface GraphResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
  highlight_info?: { node_ids: string[]; edge_ids: string[] }
  message?: string
  notifications?: string[] | null
}

export interface GraphTreeNode {
  step: string
  node_id: string
  name: string
  type: string
  timestamp?: string
  risk_score?: number
  edge_context?: string
  expandable?: boolean
  children?: GraphTreeNode[]
}

export interface AttackTreeResponse {
  attack_trees: GraphTreeNode[]
  message?: string
  notifications?: string[] | null
}

export interface GraphFindingsFilters {
  finding_type?: string
  exclude_finding_type?: string
  ticket_status?: TicketStatus
  owner?: string
}

export interface PatchFindingTicketBody {
  ticket_status?: TicketStatus
  assigned_to_user_id?: string | null
  new_note?: string
}
