"use client"

import { Fragment, useCallback, useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import {
  ArrowDownIcon,
  ArrowUpDownIcon,
  ArrowUpIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ExternalLinkIcon,
  RefreshCwIcon,
} from "lucide-react"

import { AttackNarrative } from "@/components/correlation/attack-narrative"
import { RiskScoreBadge } from "@/components/correlation/risk-score-badge"
import { getGraphFindingDetails } from "@/lib/api/graph/graphAnalysis"
import type { GraphFindingDetails } from "@/lib/api/graph/types"
import {
  NeonActionButton,
  NeonBadge,
  NeonGlassCard,
  NeonTable,
  NeonTableBody,
  NeonTableCell,
  NeonTableHead,
  NeonTableHeader,
  NeonTableRow,
} from "@/components/neon-glass"
import { TsocTablePagination } from "@/components/tables"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { getGraphFindings } from "@/lib/api/graph/graphCorrelation"
import type { GraphFindingSummary, TicketStatus } from "@/lib/api/graph/types"
import {
  compareValues,
  paginateSlice,
  type SortDirection,
} from "@/lib/tsoc-table"
import { cn } from "@/lib/utils"

const PAGE_SIZE = 20
const FETCH_LIMIT = 100

type SortColumn = "display_id" | "title" | "risk_score" | "ticket_status" | "created_at"

const DEFAULT_SORT_COLUMN: SortColumn = "created_at"
const DEFAULT_SORT_DIRECTION: SortDirection = "desc"

const SORT_ACCESSORS: Record<
  SortColumn,
  (row: GraphFindingSummary) => string | number
> = {
  display_id: (row) => row.display_id,
  title: (row) => row.title,
  risk_score: (row) => row.risk_score,
  ticket_status: (row) => row.ticket_status,
  created_at: (row) => {
    const t = Date.parse(row.created_at)
    return Number.isFinite(t) ? t : 0
  },
}

function defaultDirectionForColumn(column: SortColumn): SortDirection {
  return column === "created_at" ? "desc" : "asc"
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

function ticketStatusClass(status: string): string {
  switch (status) {
    case "in_progress":
      return "border-amber-500/30 bg-amber-500/10 text-amber-300"
    case "closed":
      return "border-slate-500/30 bg-slate-500/10 text-slate-300"
    case "closed_false_positive":
      return "border-slate-500/30 bg-slate-500/10 text-slate-400"
    default:
      return "border-teal-500/30 bg-teal-500/10 text-teal-300"
  }
}

function FindingFiltersBar({
  statusFilter,
  onStatusFilter,
  onRefresh,
  loading,
}: {
  statusFilter: TicketStatus | "all"
  onStatusFilter: (v: TicketStatus | "all") => void
  onRefresh: () => void
  loading: boolean
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/5 px-4 py-3">
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-400">Ticket status</span>
        <Select
          value={statusFilter}
          onValueChange={(v) => onStatusFilter(v as TicketStatus | "all")}
        >
          <SelectTrigger className="h-8 w-[140px] border-white/10 bg-black/40 text-white">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="border-white/10 bg-[#0a0a0f] text-white">
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="open">Open</SelectItem>
            <SelectItem value="in_progress">In progress</SelectItem>
            <SelectItem value="closed">Closed</SelectItem>
            <SelectItem value="closed_false_positive">False positive</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <NeonActionButton
        accent="teal"
        size="sm"
        className="border-white/15 text-slate-300"
        onClick={onRefresh}
        disabled={loading}
      >
        <RefreshCwIcon className={cn("size-4", loading && "animate-spin")} />
        Refresh
      </NeonActionButton>
    </div>
  )
}

function SortableTableHead({
  label,
  column,
  activeColumn,
  direction,
  onSort,
}: {
  label: string
  column: SortColumn
  activeColumn: SortColumn
  direction: SortDirection
  onSort: (column: SortColumn) => void
}) {
  const active = activeColumn === column
  const icon = !active ? (
    <ArrowUpDownIcon className="size-3.5 opacity-50" />
  ) : direction === "asc" ? (
    <ArrowUpIcon className="size-3.5" />
  ) : (
    <ArrowDownIcon className="size-3.5" />
  )

  return (
    <NeonTableHead className="border-0">
      <button
        type="button"
        className="header-sort-btn inline-flex items-center gap-1 border-0 bg-transparent p-0 text-left font-medium text-slate-400 shadow-none ring-0 hover:bg-white/5 focus-visible:ring-0"
        onClick={() => onSort(column)}
      >
        {label}
        {icon}
      </button>
    </NeonTableHead>
  )
}

export function FindingsTable({ refreshKey }: { refreshKey: number }) {
  const router = useRouter()
  const [allRows, setAllRows] = useState<GraphFindingSummary[]>([])
  const [pageIndex, setPageIndex] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [expandedDetails, setExpandedDetails] = useState<
    Record<string, GraphFindingDetails>
  >({})
  const [detailsLoadingId, setDetailsLoadingId] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<TicketStatus | "all">("all")
  const [sortColumn, setSortColumn] = useState<SortColumn>(DEFAULT_SORT_COLUMN)
  const [sortDirection, setSortDirection] =
    useState<SortDirection>(DEFAULT_SORT_DIRECTION)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getGraphFindings(FETCH_LIMIT, 0, {
        finding_type: "smart_attack_discovery",
      })
      setAllRows(res.items)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setAllRows([])
    } finally {
      setLoading(false)
    }
  }, [])

  const filteredRows = useMemo(() => {
    if (statusFilter === "all") return allRows
    return allRows.filter((row) => row.ticket_status === statusFilter)
  }, [allRows, statusFilter])

  const sortedRows = useMemo(() => {
    const accessor = SORT_ACCESSORS[sortColumn]
    const sorted = [...filteredRows]
    sorted.sort((a, b) => {
      const cmp = compareValues(accessor(a), accessor(b))
      return sortDirection === "asc" ? cmp : -cmp
    })
    return sorted
  }, [filteredRows, sortColumn, sortDirection])

  const rows = useMemo(
    () => paginateSlice(sortedRows, pageIndex, PAGE_SIZE),
    [sortedRows, pageIndex],
  )
  const total = sortedRows.length

  const toggleSort = (column: SortColumn) => {
    if (sortColumn !== column) {
      setSortColumn(column)
      setSortDirection(defaultDirectionForColumn(column))
      setPageIndex(0)
      return
    }
    setSortDirection((current) => (current === "asc" ? "desc" : "asc"))
    setPageIndex(0)
  }

  useEffect(() => {
    void load()
  }, [load, refreshKey])

  const openExplorer = (row: GraphFindingSummary) => {
    router.push(
      `/correlation/explorer?finding_id=${row.id}&identifier=${row.id}`,
    )
  }

  const toggleExpanded = (row: GraphFindingSummary) => {
    const nextId = expandedId === row.id ? null : row.id
    setExpandedId(nextId)
    if (!nextId || expandedDetails[row.id]) return
    setDetailsLoadingId(row.id)
    void getGraphFindingDetails(row.id)
      .then((detail) => {
        setExpandedDetails((prev) => ({ ...prev, [row.id]: detail }))
      })
      .catch(() => {
        setExpandedDetails((prev) => ({
          ...prev,
          [row.id]: {
            ...row,
            details: {
              incident_id: "",
              incident_title: row.title,
              executive_summary: row.summary,
              contributing_alerts: [],
              key_entities: { identities: [], assets: [], iocs: [] },
              recommended_next_steps: [],
              smart_hunt_queries: [],
              aggregated_mitre_techniques: [],
              raw_analysis: {},
              raw_paths: [],
            },
          },
        }))
      })
      .finally(() => setDetailsLoadingId(null))
  }

  return (
    <NeonGlassCard className="overflow-hidden">
      <FindingFiltersBar
        statusFilter={statusFilter}
        onStatusFilter={(v) => {
          setStatusFilter(v)
          setPageIndex(0)
        }}
        onRefresh={() => void load()}
        loading={loading}
      />

      {error ? (
        <p className="border-t border-white/5 px-4 py-6 text-sm text-red-400">
          {error}
        </p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <NeonTable>
              <NeonTableHeader>
                <NeonTableRow>
                  <NeonTableHead className="w-8" />
                  <SortableTableHead
                    label="ID"
                    column="display_id"
                    activeColumn={sortColumn}
                    direction={sortDirection}
                    onSort={toggleSort}
                  />
                  <SortableTableHead
                    label="Title"
                    column="title"
                    activeColumn={sortColumn}
                    direction={sortDirection}
                    onSort={toggleSort}
                  />
                  <SortableTableHead
                    label="Risk"
                    column="risk_score"
                    activeColumn={sortColumn}
                    direction={sortDirection}
                    onSort={toggleSort}
                  />
                  <SortableTableHead
                    label="Status"
                    column="ticket_status"
                    activeColumn={sortColumn}
                    direction={sortDirection}
                    onSort={toggleSort}
                  />
                  <SortableTableHead
                    label="Created"
                    column="created_at"
                    activeColumn={sortColumn}
                    direction={sortDirection}
                    onSort={toggleSort}
                  />
                  <NeonTableHead className="text-right">Actions</NeonTableHead>
                </NeonTableRow>
              </NeonTableHeader>
              <NeonTableBody>
                {loading && rows.length === 0 ? (
                  <NeonTableRow>
                    <NeonTableCell
                      colSpan={7}
                      className="py-10 text-center text-slate-400"
                    >
                      Loading findings…
                    </NeonTableCell>
                  </NeonTableRow>
                ) : rows.length === 0 ? (
                  <NeonTableRow>
                    <NeonTableCell
                      colSpan={7}
                      className="py-10 text-center text-slate-400"
                    >
                      No findings match your filters.
                    </NeonTableCell>
                  </NeonTableRow>
                ) : (
                  rows.map((row) => {
                    const expanded = expandedId === row.id
                    return (
                      <Fragment key={row.id}>
                        <NeonTableRow
                          className="cursor-pointer hover:bg-white/5"
                          onClick={() => toggleExpanded(row)}
                        >
                          <NeonTableCell>
                            {expanded ? (
                              <ChevronDownIcon className="size-4 text-slate-400" />
                            ) : (
                              <ChevronRightIcon className="size-4 text-slate-400" />
                            )}
                          </NeonTableCell>
                          <NeonTableCell className="font-mono text-xs text-slate-300">
                            {row.display_id}
                          </NeonTableCell>
                          <NeonTableCell className="max-w-[240px] truncate text-white">
                            {row.title}
                          </NeonTableCell>
                          <NeonTableCell>
                            <RiskScoreBadge score={row.risk_score} />
                          </NeonTableCell>
                          <NeonTableCell>
                            <NeonBadge
                              className={cn(
                                "border capitalize",
                                ticketStatusClass(row.ticket_status),
                              )}
                            >
                              {row.ticket_status.replace(/_/g, " ")}
                            </NeonBadge>
                          </NeonTableCell>
                          <NeonTableCell className="text-xs text-slate-400">
                            {formatDate(row.created_at)}
                          </NeonTableCell>
                          <NeonTableCell className="text-right">
                            <button
                              type="button"
                              className="inline-flex items-center gap-1 rounded-md border border-teal-500/30 bg-teal-500/10 px-2 py-1 text-xs text-teal-300 transition-colors hover:bg-teal-500/20"
                              onClick={(e) => {
                                e.stopPropagation()
                                openExplorer(row)
                              }}
                            >
                              <ExternalLinkIcon className="size-3.5" />
                              Explorer
                            </button>
                          </NeonTableCell>
                        </NeonTableRow>
                        {expanded ? (
                          <NeonTableRow>
                            <NeonTableCell
                              colSpan={7}
                              className="bg-black/20 py-4"
                            >
                              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-teal-400/90">
                                Attack narrative
                              </h4>
                              {detailsLoadingId === row.id ? (
                                <p className="text-xs text-slate-500">
                                  Loading attack story…
                                </p>
                              ) : (
                                <AttackNarrative
                                  compact
                                  executiveSummary={
                                    expandedDetails[row.id]?.details
                                      ?.executive_summary ?? row.summary
                                  }
                                  steps={
                                    expandedDetails[row.id]?.details
                                      ?.attack_analysis_steps
                                  }
                                />
                              )}
                              {row.agent_validation_status ? (
                                <p className="mt-3 text-xs text-slate-500">
                                  Validation: {row.agent_validation_status}
                                </p>
                              ) : null}
                            </NeonTableCell>
                          </NeonTableRow>
                        ) : null}
                      </Fragment>
                    )
                  })
                )}
              </NeonTableBody>
            </NeonTable>
          </div>
          <TsocTablePagination
            totalRows={total}
            pageIndex={pageIndex}
            pageSize={PAGE_SIZE}
            pageSizeOptions={[20]}
            onPageIndexChange={setPageIndex}
            onPageSizeChange={() => {}}
          />
        </>
      )}
    </NeonGlassCard>
  )
}
