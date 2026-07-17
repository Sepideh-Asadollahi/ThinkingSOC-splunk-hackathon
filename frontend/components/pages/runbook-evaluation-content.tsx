"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import {
  ActivityIcon,
  BadgeDollarSignIcon,
  CheckCircle2Icon,
  Clock3Icon,
  FlaskConicalIcon,
  GaugeIcon,
  HistoryIcon,
  PlayIcon,
  RefreshCwIcon,
  ShieldCheckIcon,
  TriangleAlertIcon,
} from "lucide-react"

import {
  NeonActionButton,
  NeonAlert,
  NeonAlertDescription,
  NeonAlertTitle,
  NeonBadge,
  NeonGlassCard,
  NeonInput,
  getNeonSelectContentClassName,
} from "@/components/neon-glass"
import { MarkdownContent } from "@/components/structured-data/mcp-markdown-content"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ApiError } from "@/lib/api/client"
import {
  fetchCompatibleRunbookTargets,
  fetchRunbookEvaluation,
  fetchRunbookLibrary,
  runShadowReplay,
  type RunbookCompatibleTarget,
  type RunbookEvaluation,
  type RunbookLibraryItem,
  type RunbookShadowRun,
} from "@/lib/api/investigation-workflow"
import { cn } from "@/lib/utils"

const SELECT_CONTENT_CLASS = cn(
  getNeonSelectContentClassName("teal"),
  "border-white/10 bg-[#050505] text-slate-200 shadow-[0_18px_45px_-18px_rgba(0,0,0,0.95)]"
)
const SELECT_ITEM_CLASS =
  "py-2 pl-2 pr-8 text-slate-300 focus:bg-teal-500/10 focus:text-teal-100 data-[state=checked]:bg-teal-500/[0.08] data-[state=checked]:text-teal-200"

function errorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) return error.message
  return "Runbook evaluation operation failed"
}

function seconds(milliseconds: number): string {
  if (milliseconds < 1000) return `${Math.round(milliseconds)} ms`
  return `${(milliseconds / 1000).toFixed(milliseconds >= 10000 ? 0 : 1)} s`
}

function money(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: value < 1 ? 4 : 2,
    maximumFractionDigits: value < 1 ? 6 : 2,
  }).format(value)
}

function MetricCard({
  icon,
  label,
  value,
  detail,
}: {
  icon: React.ReactNode
  label: string
  value: string
  detail: string
}) {
  return (
    <NeonGlassCard accent="teal" className="h-full bg-black">
      <div className="flex h-full gap-3 p-4">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-teal-500/20 bg-teal-500/[0.07] text-teal-300">
          {icon}
        </div>
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-[0.12em] text-slate-500">{label}</p>
          <p className="mt-1 text-2xl font-semibold text-slate-100">{value}</p>
          <p className="mt-1 text-xs leading-5 text-slate-500">{detail}</p>
        </div>
      </div>
    </NeonGlassCard>
  )
}

function QualityBar({ label, value, detail }: { label: string; value: number; detail: string }) {
  const bounded = Math.max(0, Math.min(100, value))
  return (
    <div className="rounded-xl border border-white/[0.08] bg-black/70 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-slate-200">{label}</p>
          <p className="mt-1 text-xs text-slate-500">{detail}</p>
        </div>
        <span className="text-lg font-semibold text-teal-300">{bounded.toFixed(1)}%</span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/[0.06]">
        <div
          className="h-full rounded-full bg-gradient-to-r from-teal-700 to-teal-300 shadow-[0_0_18px_rgba(45,212,191,0.28)] transition-[width] duration-500"
          style={{ width: `${bounded}%` }}
        />
      </div>
    </div>
  )
}

function ShadowStatusBadge({ status }: { status: RunbookShadowRun["status"] }) {
  const classes = status === "EVIDENCE_FOUND"
    ? "border-emerald-500/30 text-emerald-300"
    : status === "FAILED"
      ? "border-rose-500/30 text-rose-300"
      : "border-amber-500/30 text-amber-300"
  return <NeonBadge className={classes}>{status.replaceAll("_", " ")}</NeonBadge>
}

export function RunbookEvaluationContent() {
  const [evaluation, setEvaluation] = useState<RunbookEvaluation | null>(null)
  const [runbooks, setRunbooks] = useState<RunbookLibraryItem[]>([])
  const [selectedRunbookId, setSelectedRunbookId] = useState("")
  const [targets, setTargets] = useState<RunbookCompatibleTarget[]>([])
  const [selectedTargetId, setSelectedTargetId] = useState("")
  const [manualMinutes, setManualMinutes] = useState("25")
  const [lastReplay, setLastReplay] = useState<RunbookShadowRun | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingTargets, setLoadingTargets] = useState(false)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [nextEvaluation, library] = await Promise.all([
        fetchRunbookEvaluation(),
        fetchRunbookLibrary(),
      ])
      const items = library.groups.flatMap((group) => group.runbooks)
      setEvaluation(nextEvaluation)
      setRunbooks(items)
      setSelectedRunbookId((current) => {
        if (current && items.some((item) => item.draft.runbook_id === current)) return current
        return items.find((item) => item.is_latest_for_source)?.draft.runbook_id
          ?? items[0]?.draft.runbook_id
          ?? ""
      })
    } catch (loadError) {
      setError(errorMessage(loadError))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timer)
  }, [load])

  const selectedRunbook = useMemo(
    () => runbooks.find((item) => item.draft.runbook_id === selectedRunbookId) ?? null,
    [runbooks, selectedRunbookId]
  )

  useEffect(() => {
    if (!selectedRunbook?.draft.source_record_id) {
      const timer = window.setTimeout(() => {
        setTargets([])
        setSelectedTargetId("")
      }, 0)
      return () => window.clearTimeout(timer)
    }
    let active = true
    const timer = window.setTimeout(() => {
      setLoadingTargets(true)
      setSelectedTargetId("")
      fetchCompatibleRunbookTargets(selectedRunbook.draft.source_record_id, 50)
        .then((response) => {
          if (!active) return
          setTargets(response.results)
          setSelectedTargetId(response.results[0] ? String(response.results[0].record_id) : "")
        })
        .catch((targetError) => {
          if (active) setError(errorMessage(targetError))
        })
        .finally(() => {
          if (active) setLoadingTargets(false)
        })
    }, 0)
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [selectedRunbook])

  async function executeShadowReplay() {
    if (!selectedRunbook || !selectedTargetId) return
    const minutes = Number(manualMinutes)
    if (!Number.isInteger(minutes) || minutes < 5 || minutes > 120) {
      setError("Manual baseline must be an integer between 5 and 120 minutes.")
      return
    }
    setRunning(true)
    setError(null)
    try {
      const replay = await runShadowReplay(Number(selectedTargetId), {
        source_record_id: selectedRunbook.draft.source_record_id,
        runbook_id: selectedRunbook.draft.runbook_id,
        estimated_manual_minutes: minutes,
      })
      setLastReplay(replay)
      setEvaluation(await fetchRunbookEvaluation())
    } catch (replayError) {
      setError(errorMessage(replayError))
    } finally {
      setRunning(false)
    }
  }

  const cleanExecutionRate = evaluation?.shadow_run_count
    ? Math.max(0, 100 - evaluation.total_execution_errors / evaluation.shadow_run_count * 100)
    : 0

  return (
    <div className="min-h-full space-y-6 bg-black" data-testid="runbook-evaluation-page">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex size-11 items-center justify-center rounded-xl border border-teal-500/20 bg-teal-500/[0.08] shadow-[0_0_24px_-10px_rgba(20,184,166,0.28)]">
            <FlaskConicalIcon className="size-5 text-teal-300" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-slate-100">Shadow Replay & Evaluation</h1>
            <p className="mt-1 text-sm text-slate-400">
              Validate read-only runbooks on historical SIDs before approval
            </p>
          </div>
        </div>
        <NeonActionButton accent="teal" onClick={() => void load()} disabled={loading}>
          <RefreshCwIcon className={cn("size-4", loading && "animate-spin")} /> Refresh metrics
        </NeonActionButton>
      </header>

      {error ? (
        <NeonAlert variant="destructive">
          <TriangleAlertIcon className="size-4" />
          <NeonAlertTitle>Evaluation error</NeonAlertTitle>
          <NeonAlertDescription>{error}</NeonAlertDescription>
        </NeonAlert>
      ) : null}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Runbook evaluation summary">
        <MetricCard icon={<GaugeIcon className="size-4" />} label="Parser quality" value={`${evaluation?.parser_valid_rate.toFixed(1) ?? "0.0"}%`} detail={`${evaluation?.parser_valid_step_count ?? 0} of ${evaluation?.total_step_count ?? 0} stored steps`} />
        <MetricCard icon={<ShieldCheckIcon className="size-4" />} label="Evidence coverage" value={`${evaluation?.evidence_coverage_rate.toFixed(1) ?? "0.0"}%`} detail={`${evaluation?.shadow_evidence_run_count ?? 0} evidence-bearing shadow runs`} />
        <MetricCard icon={<Clock3Icon className="size-4" />} label="Projected time saved" value={`${evaluation?.projected_minutes_saved.toFixed(1) ?? "0.0"} min`} detail={`${evaluation?.shadow_run_count ?? 0} measured read-only replays`} />
        <MetricCard icon={<BadgeDollarSignIcon className="size-4" />} label="Projected labor savings" value={money(evaluation?.projected_labor_savings_usd ?? 0)} detail={`${money(evaluation?.analyst_hourly_cost_usd ?? 0)}/hour loaded analyst baseline`} />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <NeonGlassCard accent="teal" className="bg-black">
          <div className="border-b border-white/[0.07] p-5">
            <div className="flex items-center gap-3">
              <PlayIcon className="size-4 text-teal-300" />
              <div>
                <h2 className="font-semibold text-slate-100">Run a Shadow Replay</h2>
                <p className="mt-1 text-xs text-slate-500">No approval required · read-only SPL · exact Alert Name · different SID</p>
              </div>
            </div>
          </div>
          <div className="space-y-4 p-5">
            <div>
              <label className="mb-2 block text-xs uppercase tracking-wide text-slate-500">Runbook revision</label>
              <Select value={selectedRunbookId} onValueChange={setSelectedRunbookId}>
                <SelectTrigger aria-label="Select runbook revision" className="h-10 w-full border-white/10 bg-black/80 text-slate-200 focus-visible:border-teal-500/40 focus-visible:ring-teal-500/10">
                  <SelectValue placeholder="Select a runbook" />
                </SelectTrigger>
                <SelectContent position="popper" align="start" className={SELECT_CONTENT_CLASS}>
                  {runbooks.map((item) => (
                    <SelectItem key={item.draft.runbook_id} value={item.draft.runbook_id} className={SELECT_ITEM_CLASS}>
                      {item.draft.applicable_search_name} · R{item.draft.revision} · #{item.draft.source_record_id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="mb-2 block text-xs uppercase tracking-wide text-slate-500">Historical target</label>
              <Select value={selectedTargetId} onValueChange={setSelectedTargetId} disabled={!targets.length || loadingTargets}>
                <SelectTrigger aria-label="Select historical target" className="h-10 w-full border-white/10 bg-black/80 text-slate-200 focus-visible:border-teal-500/40 focus-visible:ring-teal-500/10">
                  <SelectValue placeholder={loadingTargets ? "Loading distinct SIDs…" : "Select a different SID"} />
                </SelectTrigger>
                <SelectContent position="popper" align="start" className={SELECT_CONTENT_CLASS}>
                  {targets.map((target) => (
                    <SelectItem key={target.record_id} value={String(target.record_id)} className={SELECT_ITEM_CLASS}>
                      #{target.record_id} · {target.sid || "legacy SID unavailable"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {!loadingTargets && selectedRunbook && targets.length === 0 ? (
                <p className="mt-2 text-xs leading-5 text-amber-300/80">
                  No historical alert with the same name and a different SID is available. Ingest another unique SID first.
                </p>
              ) : null}
            </div>

            <div>
              <label className="mb-2 block text-xs uppercase tracking-wide text-slate-500">Manual baseline (minutes)</label>
              <NeonInput accent="teal" type="number" min={5} max={120} value={manualMinutes} onChange={(event) => setManualMinutes(event.target.value)} />
            </div>

            <NeonActionButton accent="teal" className="w-full justify-center" disabled={running || !selectedRunbook || !selectedTargetId} onClick={() => void executeShadowReplay()}>
              <FlaskConicalIcon className={cn("size-4", running && "animate-pulse")} />
              {running ? "Executing read-only replay…" : "Run Shadow Replay"}
            </NeonActionButton>
          </div>
        </NeonGlassCard>

        <NeonGlassCard accent="teal" className="bg-black">
          <div className="border-b border-white/[0.07] p-5">
            <div className="flex items-center gap-3">
              <ActivityIcon className="size-4 text-teal-300" />
              <div>
                <h2 className="font-semibold text-slate-100">Evaluation signals</h2>
                <p className="mt-1 text-xs text-slate-500">Measured from persisted artifacts</p>
              </div>
            </div>
          </div>
          <div className="space-y-3 p-5">
            <QualityBar label="Parser-valid steps" value={evaluation?.parser_valid_rate ?? 0} detail="Safe SPL accepted by the Splunk parser" />
            <QualityBar label="Evidence coverage" value={evaluation?.evidence_coverage_rate ?? 0} detail="Shadow runs returning source evidence" />
            <QualityBar label="Clean execution" value={cleanExecutionRate} detail={`${evaluation?.total_execution_errors ?? 0} recorded execution errors`} />
            <div className="grid grid-cols-2 gap-3 pt-1 text-sm">
              <div className="rounded-xl border border-white/[0.08] bg-black/70 p-3"><p className="text-xs text-slate-500">Average compile</p><p className="mt-1 font-medium text-slate-200">{seconds(evaluation?.average_compile_duration_ms ?? 0)}</p></div>
              <div className="rounded-xl border border-white/[0.08] bg-black/70 p-3"><p className="text-xs text-slate-500">Average replay</p><p className="mt-1 font-medium text-slate-200">{seconds(evaluation?.average_shadow_duration_ms ?? 0)}</p></div>
              <div className="rounded-xl border border-white/[0.08] bg-black/70 p-3"><p className="text-xs text-slate-500">Compiler tokens</p><p className="mt-1 font-medium text-slate-200">{((evaluation?.total_prompt_tokens ?? 0) + (evaluation?.total_completion_tokens ?? 0)).toLocaleString()}</p></div>
              <div className="rounded-xl border border-white/[0.08] bg-black/70 p-3"><p className="text-xs text-slate-500">Compile LLM cost</p><p className="mt-1 font-medium text-slate-200">{money(evaluation?.estimated_compile_llm_cost_usd ?? 0)}</p></div>
            </div>
          </div>
        </NeonGlassCard>
      </section>

      {lastReplay ? (
        <NeonGlassCard accent="teal" className="bg-black" data-testid="shadow-replay-result">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.07] p-5">
            <div>
              <p className="text-xs uppercase tracking-[0.14em] text-teal-400/70">Latest Shadow Replay</p>
              <h2 className="mt-1 font-semibold text-slate-100">Target #{lastReplay.target_record_id}</h2>
              <p className="mt-1 break-all text-xs text-slate-500">SID: {lastReplay.target_sid || "unavailable"}</p>
            </div>
            <ShadowStatusBadge status={lastReplay.status} />
          </div>
          <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-5">
            <div><p className="text-xs text-slate-500">Parser valid</p><p className="mt-1 text-sm font-medium text-slate-200">{lastReplay.parser_valid_step_count}/{lastReplay.results.length}</p></div>
            <div><p className="text-xs text-slate-500">Evidence rows</p><p className="mt-1 text-sm font-medium text-slate-200">{lastReplay.total_evidence_rows}</p></div>
            <div><p className="text-xs text-slate-500">Duration</p><p className="mt-1 text-sm font-medium text-slate-200">{seconds(lastReplay.duration_ms)}</p></div>
            <div><p className="text-xs text-slate-500">Projected saved</p><p className="mt-1 text-sm font-medium text-slate-200">{lastReplay.projected_minutes_saved.toFixed(1)} min</p></div>
            <div><p className="text-xs text-slate-500">Projected value</p><p className="mt-1 text-sm font-medium text-emerald-300">{money(lastReplay.projected_labor_savings_usd)}</p></div>
          </div>
          {lastReplay.failure_reason ? <div className="px-5 pb-5 text-sm text-rose-300">{lastReplay.failure_reason}</div> : null}
          {lastReplay.results.length ? (
            <div className="space-y-3 px-5 pb-5">
              {lastReplay.results.map((result, index) => (
                <div key={`${result.question}-${index}`} className="rounded-xl border border-white/[0.08] bg-black/70 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-medium text-slate-200">Step {index + 1}: <MarkdownContent content={result.question} compact /></p>
                    <NeonBadge className={result.spl_results?.error ? "border-rose-500/30 text-rose-300" : result.validation?.valid ? "border-teal-500/30 text-teal-300" : "border-amber-500/30 text-amber-300"}>
                      {result.spl_results?.error ? "EXECUTION ERROR" : result.validation?.valid ? `${result.spl_results?.row_count ?? 0} ROWS` : "PARSER REVIEW"}
                    </NeonBadge>
                  </div>
                  {result.explanation ? <MarkdownContent content={result.explanation} className="mt-3 text-sm leading-6 text-slate-400" /> : null}
                  {result.spl_results?.error ? <p className="mt-3 text-xs text-rose-300">{result.spl_results.error}</p> : null}
                </div>
              ))}
            </div>
          ) : null}
        </NeonGlassCard>
      ) : null}

      <NeonGlassCard accent="teal" className="overflow-hidden bg-black">
        <div className="flex items-center gap-3 border-b border-white/[0.07] p-5">
          <HistoryIcon className="size-4 text-teal-300" />
          <div>
            <h2 className="font-semibold text-slate-100">Recent Shadow Replays</h2>
            <p className="mt-1 text-xs text-slate-500">Append-only evidence, newest first</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-b border-white/[0.07] bg-white/[0.02] text-xs uppercase tracking-wide text-slate-500">
              <tr><th className="px-5 py-3">Target</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Evidence</th><th className="px-5 py-3">Duration</th><th className="px-5 py-3">Projected value</th><th className="px-5 py-3">Created</th></tr>
            </thead>
            <tbody>
              {(evaluation?.recent_shadow_runs ?? []).map((shadow) => (
                <tr key={shadow.shadow_run_id} className="border-b border-white/[0.05] text-slate-300 last:border-0">
                  <td className="px-5 py-4"><p className="font-medium">#{shadow.target_record_id}</p><p className="mt-1 max-w-[240px] truncate text-xs text-slate-600">{shadow.target_sid || "SID unavailable"}</p></td>
                  <td className="px-5 py-4"><ShadowStatusBadge status={shadow.status} /></td>
                  <td className="px-5 py-4">{shadow.total_evidence_rows} rows</td>
                  <td className="px-5 py-4">{seconds(shadow.duration_ms)}</td>
                  <td className="px-5 py-4 text-emerald-300">{money(shadow.projected_labor_savings_usd)}</td>
                  <td className="px-5 py-4 text-xs text-slate-500">{new Date(shadow.created_at).toLocaleString()}</td>
                </tr>
              ))}
              {!loading && !evaluation?.recent_shadow_runs.length ? (
                <tr><td colSpan={6} className="px-5 py-12 text-center text-sm text-slate-600">No Shadow Replay has been recorded yet.</td></tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </NeonGlassCard>

      <div className="flex flex-wrap gap-3 text-xs text-slate-500">
        <span className="inline-flex items-center gap-1.5"><CheckCircle2Icon className="size-3.5 text-teal-400" /> {evaluation?.revision_count ?? 0} revisions measured</span>
        <span>·</span><span>{evaluation?.approved_runbook_count ?? 0} approved</span>
        <span>·</span><span>{evaluation?.production_run_count ?? 0} production reuses</span>
        <span>·</span><span>{evaluation?.realized_minutes_saved.toFixed(1) ?? "0.0"} realized minutes saved</span>
      </div>
    </div>
  )
}
