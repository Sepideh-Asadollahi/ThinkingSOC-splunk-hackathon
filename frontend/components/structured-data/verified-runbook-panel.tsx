"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import {
  ArrowRightIcon,
  BotIcon,
  CheckCircle2Icon,
  FileSearchIcon,
  Loader2Icon,
  LockKeyholeIcon,
  RefreshCwIcon,
  RouteIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
} from "lucide-react"

import {
  NeonActionButton,
  NeonAlert,
  NeonAlertDescription,
  NeonAlertTitle,
  NeonBadge,
  NeonCardHeader,
  NeonField,
  NeonFieldLabel,
  NeonGlassCard,
  NeonInput,
  getNeonSelectContentClassName,
} from "@/components/neon-glass"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ApiError } from "@/lib/api/client"
import {
  buildVerifiedRunbook,
  buildSafeResponsePreview,
  decideSafeResponsePreview,
  decideVerifiedRunbook,
  fetchAnalystActions,
  fetchCompatibleRunbookTargets,
  fetchRunbookAutopilot,
  fetchRunbookRuntimeStatus,
  fetchVerifiedRunbook,
  runVerifiedRunbook,
  runRunbookAutopilot,
  type RunbookAutopilotSession,
  type RunbookCompatibleTarget,
  type RunbookSourceResult,
  type RunbookStep,
  type RunbookRuntimeStatus,
  type SafeResponseAction,
  type VerifiedRunbookState,
} from "@/lib/api/investigation-workflow"
import { formatEventCreatedAt } from "@/lib/storage-events"
import { getRunbookDraftStatusPresentation } from "@/lib/runbook-status"
import { cn } from "@/lib/utils"
import { MarkdownContent } from "./mcp-markdown-content"
import { RunbookFlowGraph } from "./runbook-flow-graph"

type BusyAction =
  | "build"
  | "approve"
  | "reject"
  | "run"
  | "response-preview"
  | "response-approve"
  | "response-reject"
  | "autopilot"
  | null

const EMPTY_STATE: VerifiedRunbookState = {
  record_id: 0,
  draft: null,
  latest_approval: null,
  latest_run: null,
  latest_response_preview: null,
  latest_response_decision: null,
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) return error.message
  return "Runbook operation failed"
}

function StatusBadge({
  status,
  draft,
}: {
  status: string
  draft?: VerifiedRunbookState["draft"]
}) {
  const draftStatus = draft && status === draft.status
    ? getRunbookDraftStatusPresentation(draft)
    : null
  const active = status === "BUILDING" || status === "REBUILDING"
  const good = status === "SOURCE_VERIFIED" || status === "APPROVED" || status === "REUSED"
  const bad = !draftStatus && (status === "FAILED" || status === "NO_EVIDENCE")
  return (
    <NeonBadge
      title={draftStatus?.detail}
      className={cn(
        active && "border-amber-400/40 bg-amber-400/5 text-amber-200",
        good && "border-emerald-500/40 text-emerald-300",
        bad && "border-rose-500/40 text-rose-300",
        draftStatus?.tone === "danger" && "border-rose-500/40 text-rose-300",
        draftStatus?.tone === "warning" && "border-amber-500/40 text-amber-300",
        draftStatus?.tone === "info" && "border-sky-500/40 text-sky-300",
        draftStatus?.tone === "neutral" && "border-slate-500/40 text-slate-300",
        !draftStatus && !active && !good && !bad && "border-amber-500/40 text-amber-300"
      )}
    >
      {draftStatus?.label ?? status.replaceAll("_", " ")}
    </NeonBadge>
  )
}

function ResultDetails({ result }: { result: RunbookSourceResult | undefined }) {
  if (!result) {
    return <p className="text-xs text-slate-500">No executable result was produced.</p>
  }
  const validation = result.validation
  const execution = result.spl_results
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 text-xs">
        <NeonBadge
          className={cn(
            validation?.valid === true
              ? "border-emerald-500/30 text-emerald-300"
              : "border-amber-500/30 text-amber-300"
          )}
        >
          Parser {validation?.valid === true ? "valid" : validation?.method ?? "not validated"}
        </NeonBadge>
        <NeonBadge className="border-white/15 text-slate-300">
          {execution?.row_count ?? 0} evidence row(s)
        </NeonBadge>
        {execution?.execution_transport ? (
          <NeonBadge className="border-sky-500/30 text-sky-300">
            Splunk {execution.execution_transport.toUpperCase()}
          </NeonBadge>
        ) : null}
        {execution?.truncated ? (
          <NeonBadge className="border-amber-500/30 text-amber-300">truncated</NeonBadge>
        ) : null}
      </div>
      {validation?.message ? <MarkdownContent content={validation.message} className="text-xs text-slate-400" /> : null}
      {execution?.error ? <MarkdownContent content={execution.error} className="text-xs text-rose-300" /> : null}
      <div>
        <div className="mb-1 flex items-center justify-between gap-2">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Generated SPL</p>
          <button
            type="button"
            className="text-xs text-teal-300 hover:text-teal-200"
            onClick={() => void navigator.clipboard?.writeText(result.spl)}
          >
            Copy
          </button>
        </div>
        <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded-lg border border-white/10 bg-black/50 p-3 text-xs text-teal-100">
          <code>{result.spl}</code>
        </pre>
      </div>
      {result.explanation ? (
        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">Explanation</p>
          <MarkdownContent content={result.explanation} className="text-xs text-slate-300" />
        </div>
      ) : null}
      {result.spl_results_analysis ? (
        <p className="text-xs text-slate-300">
          Result analysis: {JSON.stringify(result.spl_results_analysis)}
        </p>
      ) : null}
      {result.notes.length > 0 ? (
        <div className="text-xs text-slate-500">
          <span>Provenance: </span>
          {result.notes.map((note, index) => (
            <span key={`${note}-${index}`}>
              <MarkdownContent content={note} compact />
              {index < result.notes.length - 1 ? " · " : null}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  )
}

function StepCard({
  step,
  result,
  index,
}: {
  step: RunbookStep
  result: RunbookSourceResult | undefined
  index: number
}) {
  return (
    <details className="rounded-lg border border-white/10 bg-black/30 p-4" open={index === 0}>
      <summary className="cursor-pointer list-none text-sm font-medium text-slate-100">
        <span className="mr-2 text-teal-300">{index + 1}.</span>
        <MarkdownContent content={step.title} compact />
      </summary>
      <div className="mt-4 space-y-4 border-t border-white/10 pt-4">
        <div className="grid gap-3 md:grid-cols-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Intent</p>
            <MarkdownContent content={step.intent} className="mt-1 text-sm text-slate-300" />
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Expected evidence</p>
            <MarkdownContent content={step.expected_evidence} className="mt-1 text-sm text-slate-300" />
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Stop condition</p>
            <MarkdownContent content={step.stop_condition} className="mt-1 text-sm text-slate-300" />
          </div>
        </div>
        <ResultDetails result={result} />
      </div>
    </details>
  )
}

function ResponseActionCard({
  action,
  index,
}: {
  action: SafeResponseAction
  index: number
}) {
  const disruptive = ["high", "critical"].includes(action.risk_level)
  return (
    <article className="rounded-xl border border-white/10 bg-black/35 p-4 shadow-[0_12px_35px_rgba(0,0,0,0.22)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">
            Option {index + 1} · {action.action_type.replaceAll("_", " ")}
          </p>
          <h5 className="mt-1 text-sm font-semibold text-slate-100">
            <MarkdownContent content={action.title} compact />
          </h5>
        </div>
        <div className="flex flex-wrap gap-2">
          <NeonBadge
            className={cn(
              disruptive
                ? "border-amber-400/35 bg-amber-400/5 text-amber-200"
                : "border-slate-500/35 text-slate-300"
            )}
          >
            {action.risk_level} risk
          </NeonBadge>
          <NeonBadge className="border-violet-400/30 text-violet-200">Preview only</NeonBadge>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <div className="rounded-lg border border-white/10 bg-black/25 p-3">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">Target</p>
          <p className="mt-1 break-words text-sm text-slate-200">
            {action.target_type}: {action.target}
          </p>
        </div>
        <div className="rounded-lg border border-white/10 bg-black/25 p-3 md:col-span-1 xl:col-span-2">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">Rationale</p>
          <MarkdownContent content={action.rationale} className="mt-1 text-sm text-slate-300" />
        </div>
        <div className="rounded-lg border border-white/10 bg-black/25 p-3">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">Expected effect</p>
          <MarkdownContent content={action.expected_effect} className="mt-1 text-sm text-slate-300" />
        </div>
        <div className="rounded-lg border border-white/10 bg-black/25 p-3">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">Rollback</p>
          <MarkdownContent content={action.rollback_plan} className="mt-1 text-sm text-slate-300" />
        </div>
        <div className="rounded-lg border border-white/10 bg-black/25 p-3">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">Prerequisites</p>
          <ul className="mt-1 list-disc space-y-1 pl-4 text-sm text-slate-300">
            {action.prerequisites.map((item) => (
              <li key={item}><MarkdownContent content={item} compact /></li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-3 rounded-lg border border-emerald-500/15 bg-emerald-500/[0.03] p-3">
        <p className="text-[10px] uppercase tracking-wide text-emerald-300/70">Manual verification</p>
        <ol className="mt-1 list-decimal space-y-1 pl-4 text-sm text-slate-300">
          {action.verification_steps.map((item) => (
            <li key={item}><MarkdownContent content={item} compact /></li>
          ))}
        </ol>
      </div>
    </article>
  )
}

function AutopilotTrace({ session }: { session: RunbookAutopilotSession }) {
  return (
    <div className="space-y-3" data-testid="runbook-autopilot-trace">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-lg border border-white/10 bg-black/30 p-3">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">Status</p>
          <p className="mt-1 text-sm font-medium text-slate-100">
            {session.status.replaceAll("_", " ")}
          </p>
        </div>
        <div className="rounded-lg border border-white/10 bg-black/30 p-3">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">Agents</p>
          <p className="mt-1 text-sm font-medium text-slate-100">{session.agents.length}</p>
        </div>
        <div className="rounded-lg border border-white/10 bg-black/30 p-3">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">Tools</p>
          <p className="mt-1 text-sm font-medium text-slate-100">{session.tools_used.length}</p>
        </div>
        <div className="rounded-lg border border-white/10 bg-black/30 p-3">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">Duration</p>
          <p className="mt-1 text-sm font-medium text-slate-100">
            {(session.duration_ms / 1000).toFixed(1)}s
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {session.agents.map((agent) => (
          <NeonBadge key={agent} className="border-violet-400/25 text-violet-200">
            {agent.replaceAll("_", " ")}
          </NeonBadge>
        ))}
      </div>
      <div className="max-h-[32rem] space-y-2 overflow-y-auto pr-1">
        {session.trace.map((event) => (
          <article
            key={event.event_id}
            className={cn(
              "grid gap-3 rounded-lg border bg-black/30 p-3 md:grid-cols-[2.75rem_minmax(0,1fr)_auto]",
              event.status === "FAILED" && "border-rose-500/30",
              event.status === "BLOCKED" && "border-amber-500/30",
              event.status === "SUCCEEDED" && "border-white/10",
              event.status === "RUNNING" && "border-sky-500/25"
            )}
          >
            <div className="flex size-9 items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] text-xs font-semibold text-teal-200">
              {event.sequence}
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold text-slate-200">
                  {event.agent.replaceAll("_", " ")}
                </span>
                <span className="text-[10px] uppercase tracking-wide text-slate-500">
                  {event.kind.replaceAll("_", " ")}
                </span>
                {event.tool_name ? (
                  <code className="rounded border border-teal-400/15 bg-teal-400/[0.03] px-1.5 py-0.5 text-[10px] text-teal-200">
                    {event.tool_name}
                  </code>
                ) : null}
              </div>
              <MarkdownContent content={event.summary} className="mt-1 text-xs text-slate-400" />
            </div>
            <span className="text-[10px] text-slate-500">
              {event.duration_ms > 0 ? `${event.duration_ms} ms` : event.status}
            </span>
          </article>
        ))}
      </div>
      <NeonAlert className="border-teal-400/20 bg-teal-400/[0.03]">
        <RouteIcon className="size-4 text-teal-300" />
        <NeonAlertTitle>Next recommended action</NeonAlertTitle>
        <NeonAlertDescription>{session.next_recommended_action}</NeonAlertDescription>
      </NeonAlert>
    </div>
  )
}

export function VerifiedRunbookPanel({
  recordId,
  refreshKey = 0,
  autoBuildRequestKey = 0,
  onWorkflowChanged,
}: {
  recordId: string
  refreshKey?: number
  autoBuildRequestKey?: number
  onWorkflowChanged?: () => void
}) {
  const [state, setState] = useState<VerifiedRunbookState>(EMPTY_STATE)
  const [runtime, setRuntime] = useState<RunbookRuntimeStatus | null>(null)
  const [acknowledged, setAcknowledged] = useState(false)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<BusyAction>(null)
  const [error, setError] = useState<string | null>(null)
  const [approvalNote, setApprovalNote] = useState("")
  const [responseDecisionNote, setResponseDecisionNote] = useState("")
  const [autopilot, setAutopilot] = useState<RunbookAutopilotSession | null>(null)
  const [autopilotObjective, setAutopilotObjective] = useState(
    "Assess this investigation and advance its reusable runbook safely."
  )
  const [targetRecordId, setTargetRecordId] = useState("")
  const [compatibleTargets, setCompatibleTargets] = useState<RunbookCompatibleTarget[]>([])
  const [targetsLoading, setTargetsLoading] = useState(false)
  const [targetDiscoveryError, setTargetDiscoveryError] = useState<string | null>(null)
  const [manualMinutes, setManualMinutes] = useState("")
  const handledAutoBuildRequest = useRef(0)

  const load = useCallback(async () => {
    if (!recordId) return
    setLoading(true)
    setError(null)
    try {
      const [runbook, actions, runtimeStatus, autopilotState] = await Promise.all([
        fetchVerifiedRunbook(recordId),
        fetchAnalystActions(recordId),
        fetchRunbookRuntimeStatus(),
        fetchRunbookAutopilot(recordId),
      ])
      setState(runbook)
      setAcknowledged(actions.results?.[0]?.action === "acknowledge")
      setRuntime(runtimeStatus)
      setAutopilot(autopilotState.latest_session)
      setManualMinutes((current) => current || String(runtimeStatus.default_manual_minutes))
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setLoading(false)
    }
  }, [recordId])

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timer)
  }, [load, refreshKey])

  const draft = state.draft
  const draftStatus = draft ? getRunbookDraftStatusPresentation(draft) : null
  const approved = Boolean(
    draft &&
      state.latest_approval?.runbook_id === draft.runbook_id &&
      state.latest_approval.decision === "approve"
  )
  const displayStatus =
    busy === "build" ? (draft ? "REBUILDING" : "BUILDING") : approved ? "APPROVED" : draft?.status
  const canApprove = draft?.status === "SOURCE_VERIFIED" && runtime?.enabled !== false

  const loadCompatibleTargets = useCallback(async () => {
    if (!recordId || !approved) return
    setTargetsLoading(true)
    setTargetDiscoveryError(null)
    try {
      const response = await fetchCompatibleRunbookTargets(recordId)
      setCompatibleTargets(response.results)
      setTargetRecordId((current) =>
        current || (response.results[0] ? String(response.results[0].record_id) : "")
      )
    } catch (targetError) {
      setCompatibleTargets([])
      setTargetDiscoveryError(errorMessage(targetError))
    } finally {
      setTargetsLoading(false)
    }
  }, [approved, recordId])

  useEffect(() => {
    if (!approved) return
    const timer = window.setTimeout(() => void loadCompatibleTargets(), 0)
    return () => window.clearTimeout(timer)
  }, [approved, loadCompatibleTargets])
  const totals = useMemo(() => {
    const results = state.latest_run?.results ?? draft?.source_results ?? []
    return results.reduce(
      (acc, item) => {
        acc.rows += item.spl_results?.row_count ?? 0
        if (item.validation?.valid === true) acc.parserValid += 1
        if ((item.spl_results?.row_count ?? 0) > 0 && !item.spl_results?.error) acc.success += 1
        return acc
      },
      { rows: 0, parserValid: 0, success: 0 }
    )
  }, [draft?.source_results, state.latest_run])

  const perform = async (action: Exclude<BusyAction, null>, fn: () => Promise<void>) => {
    setBusy(action)
    setError(null)
    try {
      await fn()
      onWorkflowChanged?.()
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(null)
    }
  }

  const build = (options: { rebuild?: boolean } = {}) =>
    perform("build", async () => {
      const nextDraft = await buildVerifiedRunbook(recordId, options)
      setState({
        record_id: Number(recordId),
        draft: nextDraft,
        latest_approval: null,
        latest_run: null,
        latest_response_preview: null,
        latest_response_decision: null,
      })
    })

  useEffect(() => {
    if (
      autoBuildRequestKey <= 0 ||
      autoBuildRequestKey <= handledAutoBuildRequest.current ||
      loading ||
      !acknowledged ||
      !runtime?.ready
    ) {
      return
    }
    handledAutoBuildRequest.current = autoBuildRequestKey
    // Acknowledge is a create-if-missing trigger, not a rebuild command. Tabs may
    // unmount their content; when this panel mounts again the parent event key is
    // still non-zero, so consume it without rebuilding an existing revision.
    if (draft) return
    const timer = window.setTimeout(() => void build({ rebuild: false }), 0)
    return () => window.clearTimeout(timer)
    // The monotonically increasing request key is the event trigger. Depending on
    // `build` would retrigger the effect on every transient state render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [acknowledged, autoBuildRequestKey, draft, loading, runtime?.ready])

  const decide = (decision: "approve" | "reject") => {
    if (!draft) return Promise.resolve()
    return perform(decision, async () => {
      const approval = await decideVerifiedRunbook(recordId, {
        runbook_id: draft.runbook_id,
        decision,
        note: approvalNote.trim() || undefined,
      })
      setState((current) => ({ ...current, latest_approval: approval }))
      setApprovalNote("")
    })
  }

  const run = () => {
    if (!draft || !targetRecordId.trim()) return Promise.resolve()
    return perform("run", async () => {
      const result = await runVerifiedRunbook(targetRecordId.trim(), {
        source_record_id: Number(recordId),
        runbook_id: draft.runbook_id,
        estimated_manual_minutes: Number(manualMinutes),
      })
      setState((current) => ({ ...current, latest_run: result }))
    })
  }

  const buildResponsePreview = () => {
    if (!draft) return Promise.resolve()
    return perform("response-preview", async () => {
      const preview = await buildSafeResponsePreview(recordId, {
        runbook_id: draft.runbook_id,
      })
      setState((current) => ({
        ...current,
        latest_response_preview: preview,
        latest_response_decision: null,
      }))
      setResponseDecisionNote("")
    })
  }

  const decideResponsePreview = (
    decision: "approve_for_manual_action" | "reject"
  ) => {
    const preview = state.latest_response_preview
    if (!preview) return Promise.resolve()
    const busyAction = decision === "approve_for_manual_action"
      ? "response-approve"
      : "response-reject"
    return perform(busyAction, async () => {
      const responseDecision = await decideSafeResponsePreview(recordId, {
        preview_id: preview.preview_id,
        decision,
        note: responseDecisionNote.trim() || undefined,
      })
      setState((current) => ({
        ...current,
        latest_response_decision: responseDecision,
      }))
      setResponseDecisionNote("")
    })
  }

  const startAutopilot = () =>
    perform("autopilot", async () => {
      const session = await runRunbookAutopilot(recordId, {
        objective: autopilotObjective.trim(),
        mode: "ADVANCE",
        generate_response_preview: true,
      })
      setAutopilot(session)
      setState(await fetchVerifiedRunbook(recordId))
    })

  return (
    <NeonGlassCard accent="teal" data-testid="verified-runbook-panel">
      <NeonCardHeader
        accent="teal"
        icon={<FileSearchIcon className="size-5 text-teal-400" />}
        title="ThinkingSOC Forge"
        description="Compile accepted evidence into a reusable, read-only investigation runbook"
        actions={displayStatus ? <StatusBadge status={displayStatus} draft={draft} /> : null}
      />
      <div className="space-y-5 px-6 pb-6">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-slate-400" aria-busy="true">
            <Loader2Icon className="size-4 animate-spin" />
            Loading runbook state…
          </div>
        ) : null}

        {!loading && runtime && (!runtime.enabled || !runtime.ready) ? (
          <NeonAlert variant={!runtime.enabled ? "destructive" : "default"}>
            <ShieldAlertIcon className="size-4" />
            <NeonAlertTitle>
              {!runtime.enabled ? "ThinkingSOC Forge is disabled" : "Forge dependencies are incomplete"}
            </NeonAlertTitle>
            <NeonAlertDescription>
              {!runtime.enabled
                ? "Enable Runbooks from the Forge Settings page. Existing artifacts remain readable."
                : "Configure PostgreSQL, the LLM, Splunk credentials, and read-only investigation execution before building or reusing a runbook."}
              {" "}
              <Link href="/runbooks" className="font-medium text-teal-300 underline-offset-4 hover:underline">
                Open Forge Settings
              </Link>
            </NeonAlertDescription>
          </NeonAlert>
        ) : null}

        {!loading ? (
          <section className="overflow-hidden rounded-xl border border-violet-400/20 bg-black/35 shadow-[0_18px_55px_rgba(0,0,0,0.28)]">
            <div className="flex flex-wrap items-start justify-between gap-4 border-b border-white/10 bg-white/[0.02] p-4">
              <div className="flex items-start gap-3">
                <div className="rounded-lg border border-violet-400/25 bg-violet-400/5 p-2">
                  <BotIcon className="size-5 text-violet-200" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-100">Runbook Autopilot Agents</h3>
                  <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-400">
                    Evidence Scout, Runbook Engineer, Policy Guard, and Response Advisor collaborate
                    through bounded tools while Supervisor records every handoff and result.
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Link
                  href={{
                    pathname: "/soc-chat",
                    query: {
                      context: "runbook",
                      record_id: recordId,
                      runbook_id: draft?.runbook_id ?? "latest",
                    },
                  }}
                  className="inline-flex h-9 items-center gap-2 rounded-md border border-teal-400/30 px-3 text-xs font-medium text-teal-200 transition-colors hover:bg-teal-400/10"
                >
                  Ask about this Runbook in Chat
                </Link>
                <NeonActionButton
                  size="sm"
                  accent="teal"
                  disabled={
                    !acknowledged ||
                    !runtime?.ready ||
                    runtime?.autopilot_enabled === false ||
                    busy !== null
                  }
                  onClick={() => void startAutopilot()}
                >
                  {busy === "autopilot" ? (
                    <Loader2Icon className="size-4 animate-spin" />
                  ) : (
                    <BotIcon className="size-4" />
                  )}
                  {busy === "autopilot" ? "Agents are working…" : "Run Autopilot"}
                </NeonActionButton>
              </div>
            </div>
            <div className="space-y-4 p-4">
              <NeonAlert className="border-violet-400/20 bg-violet-400/[0.03]">
                <LockKeyholeIcon className="size-4 text-violet-300" />
                <NeonAlertTitle>Bounded autonomy with a hard human gate</NeonAlertTitle>
                <NeonAlertDescription>
                  Autopilot may read stored evidence, search the library, compile and verify read-only
                  investigations, and prepare a Safe Response Preview. It cannot approve a Runbook,
                  run production reuse, or execute containment.
                </NeonAlertDescription>
              </NeonAlert>
              <NeonField>
                <NeonFieldLabel htmlFor="runbook-autopilot-objective">Autopilot objective</NeonFieldLabel>
                <NeonInput
                  id="runbook-autopilot-objective"
                  value={autopilotObjective}
                  onChange={(event) => setAutopilotObjective(event.target.value)}
                  maxLength={1000}
                  disabled={busy !== null}
                />
              </NeonField>
              {busy === "autopilot" ? (
                <div className="flex items-center gap-2 rounded-lg border border-amber-400/20 bg-amber-400/[0.03] p-3 text-xs text-amber-100" aria-live="polite">
                  <Loader2Icon className="size-4 animate-spin" />
                  Agents are reading evidence and may call the configured LLM and Splunk read-only verification tools.
                </div>
              ) : null}
              {autopilot ? (
                <AutopilotTrace session={autopilot} />
              ) : (
                <p className="rounded-lg border border-dashed border-white/10 p-5 text-center text-sm text-slate-500">
                  No Autopilot trace exists for this investigation yet.
                </p>
              )}
            </div>
          </section>
        ) : null}

        {!loading && !draft ? (
          <div className="rounded-lg border border-white/10 bg-black/30 p-4">
            <p className="text-sm text-slate-300">
              {busy === "build"
                ? "Acknowledgement saved. The LLM is compiling and source-verifying this runbook; slow providers can take several minutes."
                : "Build a runbook from this investigation's verdict, evidence chain, and questions."}
            </p>
            {!acknowledged ? (
              <p className="mt-2 text-xs text-amber-300">Acknowledge this investigation first.</p>
            ) : null}
            <NeonActionButton
              className="mt-4"
              accent="teal"
              disabled={!acknowledged || !runtime?.ready || busy !== null}
              onClick={() => void build()}
            >
              {busy === "build" ? (
                <Loader2Icon className="size-4 animate-spin" />
              ) : (
                <FileSearchIcon className="size-4" />
              )}
              {busy === "build" ? "Building verified runbook…" : "Build verified runbook"}
            </NeonActionButton>
          </div>
        ) : null}

        {draft ? (
          <>
            <div className="space-y-2">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-base font-semibold text-slate-100"><MarkdownContent content={draft.title} compact /></h3>
                  <MarkdownContent content={draft.summary} className="mt-1 text-sm text-slate-400" />
                </div>
                <NeonActionButton
                  size="sm"
                  accent="teal"
                  disabled={!acknowledged || !runtime?.ready || busy !== null}
                  onClick={() => void build()}
                >
                  <RefreshCwIcon className={cn("size-3.5", busy === "build" && "animate-spin")} />
                  Rebuild
                </NeonActionButton>
              </div>
              <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                <span>{draft.steps.length} step(s)</span>
                <span>·</span>
                <span>{totals.parserValid} parser-valid</span>
                <span>·</span>
                <span>{totals.rows} evidence row(s)</span>
                <span>·</span>
                <span>{draft.compile_duration_ms} ms</span>
                <span>·</span>
                <span>{draft.generation_duration_ms} ms generation</span>
                <span>·</span>
                <span>{draft.verification_duration_ms} ms verification</span>
                <span>·</span>
                <span>{draft.model}</span>
              </div>
            </div>

            {busy === "build" ? (
              <NeonAlert
                className="border-amber-400/25 bg-amber-400/[0.06] text-amber-100"
                aria-live="polite"
              >
                <Loader2Icon className="size-4 animate-spin text-amber-300" />
                <NeonAlertTitle>Runbook rebuild in progress</NeonAlertTitle>
                <NeonAlertDescription>
                  The graph below shows the previous revision while the LLM and Splunk verification
                  pipeline build a new one. Its prior status is not the result of the active rebuild.
                </NeonAlertDescription>
              </NeonAlert>
            ) : draft.status === "SOURCE_VERIFIED" ? (
              <NeonAlert>
                <CheckCircle2Icon className="size-4 text-emerald-400" />
                <NeonAlertTitle>Verified on the source investigation</NeonAlertTitle>
                <NeonAlertDescription>
                  Human approval is still required before reuse. Source verification does not prove universal correctness.
                </NeonAlertDescription>
              </NeonAlert>
            ) : (
              <NeonAlert variant={draftStatus?.tone === "danger" ? "destructive" : "default"}>
                <ShieldAlertIcon className="size-4" />
                <NeonAlertTitle>{draftStatus?.label ?? draft.status.replaceAll("_", " ")}</NeonAlertTitle>
                <NeonAlertDescription>
                  {draft.status === "FAILED"
                    ? draftStatus?.detail
                    : "Approval stays disabled until every step is parser-valid and returns source evidence."}
                </NeonAlertDescription>
              </NeonAlert>
            )}

            <RunbookFlowGraph
              draft={draft}
              approval={state.latest_approval}
              latestRun={state.latest_run}
            />

            <div className="space-y-3">
              {draft.steps.map((step, index) => (
                <StepCard
                  key={step.step_id}
                  step={step}
                  result={draft.source_results[index]}
                  index={index}
                />
              ))}
            </div>

            <div className="rounded-lg border border-white/10 bg-black/30 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Decision rule</p>
              <MarkdownContent content={draft.decision_rule} className="mt-1 text-sm text-slate-300" />
              {draft.limitations.length > 0 ? (
                <div className="mt-3">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Limitations</p>
                  <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-400">
                    {draft.limitations.map((item) => <li key={item}><MarkdownContent content={item} compact /></li>)}
                  </ul>
                </div>
              ) : null}
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-lg border border-violet-500/20 bg-violet-500/5 p-4">
                <h4 className="text-sm font-medium text-slate-100">Human decision</h4>
                {state.latest_approval ? (
                  <p className="mt-1 text-xs text-slate-400">
                    {state.latest_approval.decision === "approve" ? "Approved" : "Rejected"} by {state.latest_approval.analyst} · {formatEventCreatedAt(state.latest_approval.created_at)}
                  </p>
                ) : null}
                <NeonField className="mt-3">
                  <NeonFieldLabel htmlFor="runbook-approval-note">Review note</NeonFieldLabel>
                  <NeonInput
                    id="runbook-approval-note"
                    value={approvalNote}
                    onChange={(event) => setApprovalNote(event.target.value)}
                    placeholder="Queries and stop conditions reviewed"
                    disabled={busy !== null}
                  />
                </NeonField>
                <div className="mt-3 flex flex-wrap gap-2">
                  <NeonActionButton
                    disabled={!canApprove || busy !== null}
                    onClick={() => void decide("approve")}
                  >
                    {busy === "approve" ? <Loader2Icon className="size-4 animate-spin" /> : <CheckCircle2Icon className="size-4" />}
                    Approve
                  </NeonActionButton>
                  <NeonActionButton
                    className="border-rose-500/40 text-rose-300 hover:bg-rose-500/10"
                    disabled={!canApprove || busy !== null}
                    onClick={() => void decide("reject")}
                  >
                    Reject
                  </NeonActionButton>
                </div>
              </div>

              <div className="rounded-lg border border-teal-500/20 bg-teal-500/5 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-medium text-slate-100">Run on another alert</h4>
                    <p className="mt-1 text-xs text-slate-400">
                      Target must be a different stored alert with exact search name: {draft.applicable_search_name}
                    </p>
                  </div>
                  <NeonActionButton
                    size="sm"
                    accent="teal"
                    aria-label="Refresh compatible alerts"
                    disabled={!approved || !runtime?.ready || targetsLoading || busy !== null}
                    onClick={() => void loadCompatibleTargets()}
                  >
                    <RefreshCwIcon className={cn("size-3.5", targetsLoading && "animate-spin")} />
                  </NeonActionButton>
                </div>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <NeonField>
                    <NeonFieldLabel htmlFor="runbook-compatible-target">Compatible target alert</NeonFieldLabel>
                    {compatibleTargets.length > 0 ? (
                      <Select
                        value={targetRecordId}
                        onValueChange={setTargetRecordId}
                        disabled={!approved || !runtime?.ready || targetsLoading || busy !== null}
                      >
                        <SelectTrigger
                          id="runbook-compatible-target"
                          aria-label="Compatible target alert"
                          className="w-full border-white/10 bg-slate-900/60"
                        >
                          <SelectValue placeholder="Select a compatible alert" />
                        </SelectTrigger>
                        <SelectContent className={getNeonSelectContentClassName("teal")}>
                          {compatibleTargets.map((target) => (
                            <SelectItem key={target.record_id} value={String(target.record_id)}>
                              #{target.record_id} · {target.review_verdict ?? "unreviewed"}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <NeonInput
                        id="runbook-compatible-target"
                        inputMode="numeric"
                        aria-label="Compatible target alert"
                        value={targetRecordId}
                        onChange={(event) => setTargetRecordId(event.target.value.replace(/\D/g, ""))}
                        placeholder={targetsLoading ? "Finding compatible alerts…" : "Enter target record ID"}
                        disabled={!approved || !runtime?.ready || targetsLoading || busy !== null}
                      />
                    )}
                    <p className="text-xs text-slate-500">
                      {targetDiscoveryError
                        ? `Automatic discovery unavailable: ${targetDiscoveryError}. Enter an eligible record ID.`
                        : targetsLoading
                        ? "Scanning recent stored investigations…"
                        : compatibleTargets.length > 0
                          ? `${compatibleTargets.length} exact-match candidate(s) found; no alert payload is exposed.`
                          : "No recent candidate found. You can still enter an eligible stored record ID."}
                    </p>
                  </NeonField>
                  <NeonField>
                    <NeonFieldLabel htmlFor="runbook-manual-minutes">Manual baseline (minutes)</NeonFieldLabel>
                    <NeonInput
                      id="runbook-manual-minutes"
                      type="number"
                      min={5}
                      max={120}
                      value={manualMinutes}
                      onChange={(event) => setManualMinutes(event.target.value)}
                      disabled={!approved || !runtime?.ready || busy !== null}
                    />
                  </NeonField>
                </div>
                <NeonActionButton
                  className="mt-3"
                  accent="teal"
                  disabled={!approved || !runtime?.ready || !targetRecordId || Number(manualMinutes) < 5 || Number(manualMinutes) > 120 || busy !== null}
                  onClick={() => void run()}
                >
                  {busy === "run" ? <Loader2Icon className="size-4 animate-spin" /> : <ArrowRightIcon className="size-4" />}
                  Run approved runbook
                </NeonActionButton>
              </div>
            </div>

            <section
              className="overflow-hidden rounded-xl border border-violet-400/20 bg-black/35 shadow-[0_18px_55px_rgba(0,0,0,0.3)]"
              data-testid="safe-response-preview"
            >
              <div className="flex flex-wrap items-start justify-between gap-4 border-b border-white/10 bg-white/[0.02] p-4">
                <div className="flex items-start gap-3">
                  <div className="rounded-lg border border-violet-400/25 bg-violet-400/5 p-2">
                    <ShieldCheckIcon className="size-5 text-violet-300" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-100">Safe Response Preview</h4>
                    <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-400">
                      Review evidence-grounded containment options before following your organization&apos;s
                      manual change and incident-response process.
                    </p>
                  </div>
                </div>
                <NeonActionButton
                  size="sm"
                  accent="teal"
                  disabled={
                    !["PARSER_VALID", "SOURCE_VERIFIED"].includes(draft.status) ||
                    !runtime?.llm_configured ||
                    busy !== null
                  }
                  onClick={() => void buildResponsePreview()}
                >
                  {busy === "response-preview" ? (
                    <Loader2Icon className="size-4 animate-spin" />
                  ) : (
                    <ShieldCheckIcon className="size-4" />
                  )}
                  {state.latest_response_preview ? "Rebuild preview" : "Generate preview"}
                </NeonActionButton>
              </div>

              <div className="space-y-4 p-4">
                <NeonAlert className="border-violet-400/25 bg-violet-400/[0.04] text-slate-200">
                  <LockKeyholeIcon className="size-4 text-violet-300" />
                  <NeonAlertTitle>Preview only — automatic execution is impossible</NeonAlertTitle>
                  <NeonAlertDescription>
                    No command, SPL, script, or response-execution endpoint is generated. Approval records
                    permission for a trained analyst to continue manually; it does not change any endpoint,
                    identity, firewall, or Splunk state.
                  </NeonAlertDescription>
                </NeonAlert>

                {state.latest_response_preview ? (
                  <>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                      <NeonBadge className="border-violet-400/30 text-violet-200">
                        {state.latest_response_preview.status.replaceAll("_", " ")}
                      </NeonBadge>
                      <NeonBadge
                        className={cn(
                          state.latest_response_preview.evidence_basis === "SOURCE_EVIDENCE"
                            ? "border-emerald-400/30 text-emerald-200"
                            : "border-amber-400/30 text-amber-200"
                        )}
                      >
                        {state.latest_response_preview.evidence_basis.replaceAll("_", " ")}
                      </NeonBadge>
                      <span>{state.latest_response_preview.actions.length} option(s)</span>
                      <span>·</span>
                      <span>{state.latest_response_preview.generation_duration_ms} ms</span>
                      <span>·</span>
                      <span>{state.latest_response_preview.model}</span>
                    </div>

                    {state.latest_response_preview.evidence_basis === "ANALYSIS_ONLY" ? (
                      <NeonAlert className="border-amber-400/20 bg-amber-400/[0.03] text-amber-100">
                        <ShieldAlertIcon className="size-4" />
                        <NeonAlertTitle>Disruptive containment is policy-blocked</NeonAlertTitle>
                        <NeonAlertDescription>
                          Source evidence is incomplete, so this preview can only recommend monitoring,
                          evidence collection, or escalation.
                        </NeonAlertDescription>
                      </NeonAlert>
                    ) : null}

                    <div className="space-y-3">
                      {state.latest_response_preview.actions.map((action, index) => (
                        <ResponseActionCard key={action.action_id} action={action} index={index} />
                      ))}
                    </div>

                    <div className="rounded-lg border border-white/10 bg-black/25 p-4">
                      <p className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Decision summary</p>
                      <MarkdownContent
                        content={state.latest_response_preview.decision_summary}
                        className="mt-1 text-sm text-slate-300"
                      />
                      {state.latest_response_preview.limitations.length > 0 ? (
                        <div className="mt-3">
                          <p className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Limitations</p>
                          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-400">
                            {state.latest_response_preview.limitations.map((item) => (
                              <li key={item}><MarkdownContent content={item} compact /></li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </div>

                    <div className="rounded-lg border border-white/10 bg-black/25 p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <h5 className="text-sm font-medium text-slate-100">Human response decision</h5>
                          <p className="mt-1 text-xs text-slate-400">
                            Approval authorizes manual handling only and requires a review note.
                          </p>
                        </div>
                        {state.latest_response_decision ? (
                          <NeonBadge
                            className={cn(
                              state.latest_response_decision.decision === "approve_for_manual_action"
                                ? "border-emerald-400/30 text-emerald-200"
                                : "border-rose-400/30 text-rose-200"
                            )}
                          >
                            {state.latest_response_decision.decision === "approve_for_manual_action"
                              ? "Approved for manual action"
                              : "Rejected"}
                          </NeonBadge>
                        ) : null}
                      </div>
                      {state.latest_response_decision ? (
                        <p className="mt-2 text-xs text-slate-500">
                          {state.latest_response_decision.analyst} · {formatEventCreatedAt(state.latest_response_decision.created_at)}
                          {state.latest_response_decision.note ? ` · ${state.latest_response_decision.note}` : ""}
                        </p>
                      ) : null}
                      <NeonField className="mt-3">
                        <NeonFieldLabel htmlFor="safe-response-decision-note">Required approval note</NeonFieldLabel>
                        <NeonInput
                          id="safe-response-decision-note"
                          value={responseDecisionNote}
                          onChange={(event) => setResponseDecisionNote(event.target.value)}
                          placeholder="Evidence, target, impact, rollback, and change process reviewed"
                          disabled={busy !== null}
                        />
                      </NeonField>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <NeonActionButton
                          disabled={!responseDecisionNote.trim() || busy !== null}
                          onClick={() => void decideResponsePreview("approve_for_manual_action")}
                        >
                          {busy === "response-approve" ? (
                            <Loader2Icon className="size-4 animate-spin" />
                          ) : (
                            <CheckCircle2Icon className="size-4" />
                          )}
                          Approve for manual action
                        </NeonActionButton>
                        <NeonActionButton
                          className="border-rose-500/40 text-rose-300 hover:bg-rose-500/10"
                          disabled={busy !== null}
                          onClick={() => void decideResponsePreview("reject")}
                        >
                          Reject preview
                        </NeonActionButton>
                      </div>
                    </div>
                  </>
                ) : (
                  <p className="rounded-lg border border-dashed border-white/10 p-6 text-center text-sm text-slate-500">
                    No response option has been generated. Build a preview to inspect targets, risk,
                    prerequisites, rollback, and verification before any manual decision.
                  </p>
                )}
              </div>
            </section>

            {state.latest_run ? (
              <div className="space-y-4">
                <div className="grid gap-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4 sm:grid-cols-2 xl:grid-cols-5">
                  <div><p className="text-xs text-slate-500">Target</p><Link className="text-lg font-semibold text-teal-300 hover:underline" href={`/analysis/investigation/${state.latest_run.target_record_id}`}>#{state.latest_run.target_record_id}</Link></div>
                  <div><p className="text-xs text-slate-500">Status</p><div className="mt-1"><StatusBadge status={state.latest_run.status} /></div></div>
                  <div><p className="text-xs text-slate-500">Runtime</p><p className="text-lg font-semibold text-slate-100">{(state.latest_run.duration_ms / 1000).toFixed(1)}s</p></div>
                  <div><p className="text-xs text-slate-500">Estimated time saved</p><p className="text-lg font-semibold text-emerald-300">{state.latest_run.estimated_minutes_saved.toFixed(1)} min</p></div>
                  <div><p className="text-xs text-slate-500">Savings</p><p className="text-lg font-semibold text-emerald-300">{state.latest_run.savings_percent.toFixed(1)}%</p></div>
                </div>
                <div>
                  <h4 className="mb-3 text-sm font-medium text-slate-100">Target-specific evidence</h4>
                  <div className="space-y-3">
                    {draft.steps.map((step, index) => (
                      <StepCard
                        key={`target-${step.step_id}`}
                        step={step}
                        result={state.latest_run?.results[index]}
                        index={index}
                      />
                    ))}
                  </div>
                </div>
              </div>
            ) : null}
          </>
        ) : null}

        {error ? (
          <NeonAlert variant="destructive">
            <NeonAlertTitle>Runbook unavailable</NeonAlertTitle>
            <NeonAlertDescription>{error}</NeonAlertDescription>
          </NeonAlert>
        ) : null}
      </div>
    </NeonGlassCard>
  )
}
