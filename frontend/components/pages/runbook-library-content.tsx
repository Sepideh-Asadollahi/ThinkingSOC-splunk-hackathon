"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  AlertCircleIcon,
  ArrowUpDownIcon,
  DownloadIcon,
  EyeIcon,
  FileJsonIcon,
  LibraryIcon,
  ListFilterIcon,
  PencilIcon,
  PlusIcon,
  RefreshCwIcon,
  SearchIcon,
  ShieldCheckIcon,
  Trash2Icon,
  UploadIcon,
} from "lucide-react"

import {
  Dialog,
  NeonActionButton,
  NeonAlert,
  NeonAlertDescription,
  NeonAlertTitle,
  NeonBadge,
  NeonDialogContent,
  NeonDialogFooter,
  NeonDialogFooterButton,
  NeonDialogHeaderWithIcon,
  NeonField,
  NeonFieldLabel,
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
import { TsocOverflowScroll } from "@/components/ui/tsoc-scroll"
import { ApiError } from "@/lib/api/client"
import {
  exportRunbooks,
  fetchRunbookLibrary,
  importRunbooks,
  reviseRunbook,
  type RunbookExportBundle,
  type RunbookLibraryItem,
  type RunbookLibraryResponse,
  type RunbookRevisionInput,
  type RunbookStep,
} from "@/lib/api/investigation-workflow"
import {
  getRunbookDraftStatusPresentation,
  type RunbookDraftStatusTone,
} from "@/lib/runbook-status"
import { cn } from "@/lib/utils"

const TEXTAREA_CLASS =
  "min-h-20 w-full rounded-lg border border-white/10 bg-black/70 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-teal-500/40 focus:ring-2 focus:ring-teal-500/10"
const ALL_ALERTS_VALUE = "__all_alert_names__"
const SELECT_CONTENT_CLASS = cn(
  getNeonSelectContentClassName("teal"),
  "border-white/10 bg-[#050505] text-slate-200 shadow-[0_18px_45px_-18px_rgba(0,0,0,0.95)]"
)
const SELECT_ITEM_CLASS =
  "py-2 pl-2 pr-8 text-slate-300 focus:bg-teal-500/10 focus:text-teal-100 data-[state=checked]:bg-teal-500/[0.08] data-[state=checked]:text-teal-200"

type SortMode = "newest" | "oldest" | "alert_asc" | "alert_desc" | "revision_desc"

function createdAtMs(item: RunbookLibraryItem): number {
  const value = Date.parse(item.draft.created_at)
  return Number.isNaN(value) ? 0 : value
}

function groupCreatedAt(
  group: RunbookLibraryResponse["groups"][number],
  mode: "min" | "max"
): number {
  const values = group.runbooks.map(createdAtMs)
  if (values.length === 0) return 0
  return mode === "min" ? Math.min(...values) : Math.max(...values)
}

function message(error: unknown) {
  if (error instanceof ApiError || error instanceof Error) return error.message
  return "Runbook library operation failed"
}

function emptyStep(index: number): RunbookStep {
  return {
    step_id: `step-${index + 1}`,
    title: `Step ${index + 1}`,
    intent: "",
    expected_evidence: "",
    stop_condition: "",
  }
}

function saveJson(document: RunbookExportBundle, filename: string) {
  const blob = new Blob([JSON.stringify(document, null, 2)], {
    type: "application/json",
  })
  const url = URL.createObjectURL(blob)
  const anchor = window.document.createElement("a")
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

function statusClass(tone: RunbookDraftStatusTone) {
  if (tone === "success") return "border-emerald-500/30 text-emerald-300"
  if (tone === "danger") return "border-red-500/30 text-red-300"
  if (tone === "warning") return "border-amber-500/30 text-amber-300"
  if (tone === "info") return "border-sky-500/30 text-sky-300"
  return "border-slate-500/30 text-slate-300"
}

type EditState = RunbookRevisionInput & {
  runbookId: string
  sourceId: string
  sourceLocked: boolean
}

function stateFromItem(item: RunbookLibraryItem): EditState {
  const draft = item.draft
  return {
    runbookId: draft.runbook_id,
    title: draft.title,
    summary: draft.summary,
    applicable_search_name: draft.applicable_search_name,
    steps: draft.steps.map((step) => ({ ...step })),
    decision_rule: draft.decision_rule,
    limitations: [...draft.limitations],
    sourceId: draft.source_record_id > 0 ? String(draft.source_record_id) : "",
    sourceLocked: draft.source_record_id > 0,
    verify_on_source: false,
    revision_note: "",
    editor: "analyst",
  }
}

function RunbookRevisionCard({
  item,
  onView,
  onEdit,
  onExport,
}: {
  item: RunbookLibraryItem
  onView: (item: RunbookLibraryItem) => void
  onEdit: (item: RunbookLibraryItem) => void
  onExport: (item: RunbookLibraryItem) => void
}) {
  const { draft, latest_approval: approval } = item
  const status = getRunbookDraftStatusPresentation(draft)
  return (
    <article data-testid="runbook-revision-card" className="rounded-xl border border-white/[0.08] bg-black/60 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04),0_12px_35px_-28px_rgba(45,212,191,0.30)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-medium text-slate-100">
              <MarkdownContent content={draft.title} compact />
            </h3>
            <NeonBadge className={statusClass(status.tone)} title={status.detail}>{status.label}</NeonBadge>
            <NeonBadge className="border-slate-600/30 text-slate-400">
              Revision {draft.revision}
            </NeonBadge>
            {item.is_latest_for_source ? (
              <NeonBadge className="border-teal-500/30 text-teal-300">LATEST</NeonBadge>
            ) : (
              <NeonBadge className="border-slate-500/30 text-slate-400">SUPERSEDED</NeonBadge>
            )}
          </div>
          <MarkdownContent
            content={draft.summary}
            className="mt-2 max-w-4xl text-sm leading-6 text-slate-400"
          />
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <NeonActionButton accent="teal" size="sm" onClick={() => onView(item)}>
            <EyeIcon className="size-3.5" /> View details
          </NeonActionButton>
          <NeonActionButton accent="teal" size="sm" onClick={() => onExport(item)}>
            <DownloadIcon className="size-3.5" /> Export
          </NeonActionButton>
          <NeonActionButton accent="teal" size="sm" onClick={() => onEdit(item)}>
            <PencilIcon className="size-3.5" /> Edit
          </NeonActionButton>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_240px]">
        <div className="space-y-2">
          {draft.steps.map((step, index) => (
            <div key={`${draft.runbook_id}-${step.step_id}`} className="rounded-lg border border-white/[0.06] bg-white/[0.025] p-3">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
                <span className="flex size-6 items-center justify-center rounded-md bg-teal-500/10 text-xs text-teal-300">{index + 1}</span>
                <MarkdownContent content={step.title} compact />
              </div>
              <MarkdownContent
                content={step.intent}
                className="mt-2 text-xs leading-5 text-slate-500"
              />
            </div>
          ))}
        </div>
        <dl className="grid content-start gap-2 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 text-xs">
          <div><dt className="text-slate-600">Origin</dt><dd className="mt-1 capitalize text-slate-300">{draft.origin}</dd></div>
          <div><dt className="text-slate-600">Source record</dt><dd className="mt-1 text-slate-300">{draft.source_record_id || "Not attached"}</dd></div>
          <div><dt className="text-slate-600">Human gate</dt><dd className="mt-1 text-slate-300">{approval ? `${approval.decision} by ${approval.analyst}` : "Approval required"}</dd></div>
          <div><dt className="text-slate-600">Created</dt><dd className="mt-1 text-slate-300">{new Date(draft.created_at).toLocaleString()}</dd></div>
        </dl>
      </div>
    </article>
  )
}

function RunbookDetailsDialog({
  item,
  onOpenChange,
}: {
  item: RunbookLibraryItem | null
  onOpenChange: (open: boolean) => void
}) {
  const draft = item?.draft
  const status = draft ? getRunbookDraftStatusPresentation(draft) : null
  return (
    <Dialog open={Boolean(item)} onOpenChange={onOpenChange}>
      <NeonDialogContent
        accent="teal"
        className="w-[calc(100vw-2rem)] max-h-[92vh] sm:max-w-5xl"
      >
        {draft && item ? (
          <div className="flex max-h-[calc(92vh-2rem)] min-h-0 flex-col">
            <NeonDialogHeaderWithIcon
              accent="teal"
              icon={<EyeIcon className="size-5 text-teal-300" />}
              title={<MarkdownContent content={draft.title} compact />}
              description={`${draft.applicable_search_name} · Revision ${draft.revision}`}
            />

            <TsocOverflowScroll
              className="min-h-0 flex-1 space-y-5 overscroll-contain px-6 pb-6 pr-4"
              maxHeight="min(72vh, 760px)"
            >
              <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Runbook metadata">
                {[
                  ["Status", status?.label ?? draft.status.replaceAll("_", " ")],
                  ["Status detail", status?.detail ?? "Not recorded"],
                  ["Alert Name", draft.applicable_search_name],
                  ["Source record", draft.source_record_id || "Not attached"],
                  ["Source verdict", draft.source_verdict],
                  ["Origin", draft.origin],
                  ["Model", draft.model || draft.configured_model || "Not recorded"],
                  ["Created", new Date(draft.created_at).toLocaleString()],
                  ["Runbook ID", draft.runbook_id],
                ].map(([label, value]) => (
                  <div key={label} className="min-w-0 rounded-lg border border-white/[0.08] bg-white/[0.025] p-3">
                    <p className="text-[11px] uppercase tracking-[0.12em] text-slate-600">{label}</p>
                    <p className="mt-1 break-words text-sm text-slate-200">{value}</p>
                  </div>
                ))}
              </section>

              <section className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-xl border border-white/[0.08] bg-black/60 p-4">
                  <h3 className="text-sm font-medium text-slate-100">Summary</h3>
                  <MarkdownContent content={draft.summary} className="mt-2 text-sm leading-6 text-slate-400" />
                </div>
                <div className="rounded-xl border border-white/[0.08] bg-black/60 p-4">
                  <h3 className="text-sm font-medium text-slate-100">Decision rule</h3>
                  <MarkdownContent content={draft.decision_rule} className="mt-2 text-sm leading-6 text-slate-400" />
                </div>
              </section>

              <section className="space-y-3" aria-label="Runbook steps and evidence">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-sm font-medium text-slate-100">Steps and source evidence</h3>
                  <div className="flex flex-wrap gap-2 text-xs">
                    <NeonBadge className="border-teal-500/30 text-teal-300">{draft.steps.length} steps</NeonBadge>
                    <NeonBadge className="border-sky-500/30 text-sky-300">{draft.parser_valid_step_count} parser-valid</NeonBadge>
                    <NeonBadge className="border-white/15 text-slate-300">{draft.total_evidence_rows} evidence rows</NeonBadge>
                  </div>
                </div>
                {draft.steps.map((step, index) => {
                  const result = draft.source_results[index]
                  return (
                    <article key={`${draft.runbook_id}-detail-${step.step_id}`} className="rounded-xl border border-white/[0.08] bg-black/60 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="flex size-7 items-center justify-center rounded-md bg-teal-500/10 text-xs font-semibold text-teal-300">{index + 1}</span>
                          <div><p className="text-sm font-medium text-slate-100"><MarkdownContent content={step.title} compact /></p><p className="text-xs text-slate-600">{step.step_id}</p></div>
                        </div>
                        {result ? (
                          <div className="flex flex-wrap gap-2">
                            <NeonBadge className={result.validation?.valid ? "border-emerald-500/30 text-emerald-300" : "border-amber-500/30 text-amber-300"}>
                              Parser {result.validation?.valid ? "valid" : "not valid"}
                            </NeonBadge>
                            <NeonBadge className="border-white/15 text-slate-300">{result.spl_results?.row_count ?? 0} rows</NeonBadge>
                            {result.spl_results?.execution_transport ? <NeonBadge className="border-sky-500/30 text-sky-300">{result.spl_results.execution_transport.toUpperCase()}</NeonBadge> : null}
                          </div>
                        ) : null}
                      </div>
                      <div className="mt-4 grid gap-3 lg:grid-cols-3">
                        <div><p className="text-xs uppercase tracking-wide text-slate-600">Intent</p><MarkdownContent content={step.intent} className="mt-1 text-sm leading-6 text-slate-400" /></div>
                        <div><p className="text-xs uppercase tracking-wide text-slate-600">Expected evidence</p><MarkdownContent content={step.expected_evidence} className="mt-1 text-sm leading-6 text-slate-400" /></div>
                        <div><p className="text-xs uppercase tracking-wide text-slate-600">Stop condition</p><MarkdownContent content={step.stop_condition} className="mt-1 text-sm leading-6 text-slate-400" /></div>
                      </div>
                      {result ? (
                        <div className="mt-4 space-y-3 border-t border-white/[0.07] pt-4">
                          <div><p className="text-xs uppercase tracking-wide text-slate-600">Generated SPL</p><pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-white/[0.08] bg-black/45 p-3 text-xs leading-5 text-teal-100"><code>{result.spl}</code></pre></div>
                          {result.validation?.message ? <div className="text-xs text-slate-500">Parser: <MarkdownContent content={result.validation.message} compact /></div> : null}
                          {result.spl_results?.error ? <NeonAlert variant="destructive"><NeonAlertTitle>Execution error</NeonAlertTitle><NeonAlertDescription><MarkdownContent content={result.spl_results.error} compact /></NeonAlertDescription></NeonAlert> : null}
                          {result.explanation ? <div><p className="text-xs uppercase tracking-wide text-slate-600">Explanation</p><MarkdownContent content={result.explanation} className="mt-1 text-sm leading-6 text-slate-400" /></div> : null}
                          {result.notes.length ? <div><p className="text-xs uppercase tracking-wide text-slate-600">Notes</p>{result.notes.map((note) => <MarkdownContent key={note} content={note} className="mt-1 text-xs text-slate-500" />)}</div> : null}
                        </div>
                      ) : <p className="mt-4 text-xs text-slate-600">No source result was recorded for this step.</p>}
                    </article>
                  )
                })}
              </section>

              <section className="grid gap-4 lg:grid-cols-3">
                <div className="rounded-xl border border-white/[0.08] bg-black/60 p-4">
                  <h3 className="text-sm font-medium text-slate-100">Limitations</h3>
                  {draft.limitations.length ? <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-400">{draft.limitations.map((value) => <li key={value}><MarkdownContent content={value} compact /></li>)}</ul> : <p className="mt-2 text-sm text-slate-600">No limitations recorded.</p>}
                </div>
                <div className="rounded-xl border border-white/[0.08] bg-black/60 p-4">
                  <h3 className="text-sm font-medium text-slate-100">Human approval</h3>
                  <p className="mt-2 text-sm text-slate-400">{item.latest_approval ? `${item.latest_approval.decision} by ${item.latest_approval.analyst}` : "No approval decision recorded."}</p>
                  {item.latest_approval?.note ? <MarkdownContent content={item.latest_approval.note} className="mt-2 text-xs text-slate-500" /> : null}
                </div>
                <div className="rounded-xl border border-white/[0.08] bg-black/60 p-4">
                  <h3 className="text-sm font-medium text-slate-100">Latest reuse</h3>
                  {item.latest_run ? <div className="mt-2 space-y-1 text-sm text-slate-400"><p>Status: {item.latest_run.status}</p><p>Target: #{item.latest_run.target_record_id}</p><p>Evidence rows: {item.latest_run.total_evidence_rows}</p><p>Estimated savings: {item.latest_run.savings_percent.toFixed(1)}%</p></div> : <p className="mt-2 text-sm text-slate-600">This revision has not been reused.</p>}
                </div>
              </section>

              <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Runbook performance">
                {[
                  ["Compile", `${draft.compile_duration_ms} ms`],
                  ["Generation", `${draft.generation_duration_ms} ms`],
                  ["Verification", `${draft.verification_duration_ms} ms`],
                  ["Tokens", `${draft.prompt_tokens ?? 0} in / ${draft.completion_tokens ?? 0} out`],
                ].map(([label, value]) => <div key={label} className="rounded-lg border border-white/[0.08] bg-white/[0.025] p-3"><p className="text-xs text-slate-600">{label}</p><p className="mt-1 text-sm text-slate-300">{value}</p></div>)}
              </section>
            </TsocOverflowScroll>

            <NeonDialogFooter className="shrink-0 border-t border-white/[0.07] px-6 pb-2 pt-4">
              <NeonDialogFooterButton type="button" footerVariant="secondary" onClick={() => onOpenChange(false)}>Close</NeonDialogFooterButton>
            </NeonDialogFooter>
          </div>
        ) : null}
      </NeonDialogContent>
    </Dialog>
  )
}

export function RunbookLibraryContent() {
  const [library, setLibrary] = useState<RunbookLibraryResponse | null>(null)
  const [filter, setFilter] = useState("")
  const [selectedAlert, setSelectedAlert] = useState("")
  const [sortMode, setSortMode] = useState<SortMode>("newest")
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [view, setView] = useState<RunbookLibraryItem | null>(null)
  const [edit, setEdit] = useState<EditState | null>(null)
  const [importDoc, setImportDoc] = useState<RunbookExportBundle | null>(null)
  const [importSourceId, setImportSourceId] = useState("")
  const [verifyImport, setVerifyImport] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setLibrary(await fetchRunbookLibrary())
    } catch (loadError) {
      setError(message(loadError))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timer)
  }, [load])

  const alertOptions = useMemo(
    () => [...(library?.groups ?? [])].sort((left, right) =>
      left.alert_name.localeCompare(right.alert_name, undefined, {
        numeric: true,
        sensitivity: "base",
      })
    ),
    [library]
  )

  const visibleGroups = useMemo(() => {
    const query = filter.trim().toLowerCase()
    const groups = (library?.groups ?? [])
      .filter((group) =>
        (!selectedAlert || group.alert_name === selectedAlert) &&
        group.alert_name.toLowerCase().includes(query)
      )
      .map((group) => ({
        ...group,
        runbooks: [...group.runbooks].sort((left, right) => {
          if (sortMode === "oldest") return createdAtMs(left) - createdAtMs(right)
          if (sortMode === "revision_desc") return right.draft.revision - left.draft.revision
          return createdAtMs(right) - createdAtMs(left)
        }),
      }))

    return groups.sort((left, right) => {
      const byName = left.alert_name.localeCompare(right.alert_name, undefined, {
        numeric: true,
        sensitivity: "base",
      })
      if (sortMode === "alert_asc") return byName
      if (sortMode === "alert_desc") return -byName
      if (sortMode === "oldest") {
        return groupCreatedAt(left, "min") - groupCreatedAt(right, "min") || byName
      }
      if (sortMode === "revision_desc") {
        const leftRevision = Math.max(0, ...left.runbooks.map((item) => item.draft.revision))
        const rightRevision = Math.max(0, ...right.runbooks.map((item) => item.draft.revision))
        return rightRevision - leftRevision || byName
      }
      return groupCreatedAt(right, "max") - groupCreatedAt(left, "max") || byName
    })
  }, [filter, library, selectedAlert, sortMode])

  async function download(filters: { runbookId?: string; searchName?: string }, filename: string) {
    setBusy(true)
    setError(null)
    try {
      saveJson(await exportRunbooks(filters), filename)
      setNotice("Portable JSON exported without evidence or approval state.")
    } catch (exportError) {
      setError(message(exportError))
    } finally {
      setBusy(false)
    }
  }

  async function chooseFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ""
    if (!file) return
    setError(null)
    try {
      const parsed = JSON.parse(await file.text()) as RunbookExportBundle
      if (parsed.schema_version !== "thinking-soc.runbook-library/v1" || !Array.isArray(parsed.runbooks) || parsed.runbooks.length === 0) {
        throw new Error("Select a valid ThinkingSOC runbook-library/v1 JSON file.")
      }
      setImportDoc(parsed)
      setImportSourceId("")
      setVerifyImport(false)
    } catch (fileError) {
      setError(message(fileError))
    }
  }

  async function submitImport(event: React.FormEvent) {
    event.preventDefault()
    if (!importDoc) return
    const sourceId = importSourceId.trim() ? Number(importSourceId) : undefined
    if (sourceId !== undefined && (!Number.isInteger(sourceId) || sourceId <= 0)) {
      setError("Source record ID must be a positive integer.")
      return
    }
    setBusy(true)
    setError(null)
    try {
      const result = await importRunbooks({
        document: importDoc,
        source_record_id: sourceId,
        verify_on_source: verifyImport,
      })
      setImportDoc(null)
      setNotice(`${result.imported_count} runbook revision(s) imported.`)
      await load()
    } catch (importError) {
      setError(message(importError))
    } finally {
      setBusy(false)
    }
  }

  function updateStep(index: number, field: keyof RunbookStep, value: string) {
    if (!edit) return
    const steps = edit.steps.map((step, stepIndex) =>
      stepIndex === index ? { ...step, [field]: value } : step
    )
    setEdit({ ...edit, steps })
  }

  async function submitEdit(event: React.FormEvent) {
    event.preventDefault()
    if (!edit) return
    const sourceId = edit.sourceId.trim() ? Number(edit.sourceId) : undefined
    if (sourceId !== undefined && (!Number.isInteger(sourceId) || sourceId <= 0)) {
      setError("Source record ID must be a positive integer.")
      return
    }
    setBusy(true)
    setError(null)
    try {
      await reviseRunbook(edit.runbookId, {
        title: edit.title,
        summary: edit.summary,
        applicable_search_name: edit.applicable_search_name,
        steps: edit.steps,
        decision_rule: edit.decision_rule,
        limitations: edit.limitations,
        source_record_id: sourceId,
        verify_on_source: edit.verify_on_source,
        revision_note: edit.revision_note,
        editor: edit.editor,
      })
      setEdit(null)
      setNotice("A new immutable revision was saved. Previous approval was not carried forward.")
      await load()
    } catch (editError) {
      setError(message(editError))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-full space-y-6 bg-black" data-testid="runbook-library-page">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex size-11 items-center justify-center rounded-xl border border-teal-500/20 bg-teal-500/[0.08] shadow-[0_0_24px_-10px_rgba(20,184,166,0.28)]">
            <LibraryIcon className="size-5 text-teal-300" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-slate-100">Runbook Library</h1>
            <p className="mt-1 text-sm text-slate-400">Every revision grouped by exact Alert Name</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <input ref={fileInput} type="file" accept="application/json,.json" className="hidden" onChange={chooseFile} />
          <NeonActionButton accent="teal" onClick={() => fileInput.current?.click()} disabled={busy}>
            <UploadIcon className="size-4" /> Import JSON
          </NeonActionButton>
          <NeonActionButton accent="teal" onClick={() => void download({}, "thinking-soc-runbooks.json")} disabled={busy || !library?.count}>
            <DownloadIcon className="size-4" /> Export all
          </NeonActionButton>
          <NeonActionButton accent="teal" onClick={() => void load()} disabled={loading} aria-label="Refresh library">
            <RefreshCwIcon className={cn("size-4", loading && "animate-spin")} />
          </NeonActionButton>
        </div>
      </header>

      {error ? <NeonAlert variant="destructive"><NeonAlertTitle>Runbook library error</NeonAlertTitle><NeonAlertDescription>{error}</NeonAlertDescription></NeonAlert> : null}
      {notice ? <NeonAlert><ShieldCheckIcon className="size-4" /><NeonAlertTitle>Completed</NeonAlertTitle><NeonAlertDescription>{notice}</NeonAlertDescription></NeonAlert> : null}

      <NeonGlassCard accent="teal">
        <div className="flex flex-wrap items-center gap-4 bg-black/70 p-4">
          <div className="relative min-w-[240px] flex-1">
            <SearchIcon className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-500" />
            <NeonInput accent="teal" className="pl-9" value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Filter by exact Alert Name..." aria-label="Filter by Alert Name" />
          </div>
          <div className="relative flex min-w-[230px] items-center">
            <ListFilterIcon className="pointer-events-none absolute left-3 z-10 size-4 text-slate-500" />
            <Select
              value={selectedAlert || ALL_ALERTS_VALUE}
              onValueChange={(value) => setSelectedAlert(value === ALL_ALERTS_VALUE ? "" : value)}
            >
              <SelectTrigger
                aria-label="Select Alert Name"
                className="w-full border-white/10 bg-black/80 pl-9 text-slate-200 data-[size=default]:h-9 focus-visible:border-teal-500/40 focus-visible:ring-teal-500/10"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent position="popper" align="start" className={SELECT_CONTENT_CLASS}>
                <SelectItem value={ALL_ALERTS_VALUE} className={SELECT_ITEM_CLASS}>
                  All Alert Names ({alertOptions.length})
                </SelectItem>
                {alertOptions.map((group) => (
                  <SelectItem key={group.alert_name} value={group.alert_name} className={SELECT_ITEM_CLASS}>
                    {group.alert_name} ({group.count} revision{group.count === 1 ? "" : "s"})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="relative flex min-w-[210px] items-center">
            <ArrowUpDownIcon className="pointer-events-none absolute left-3 z-10 size-4 text-slate-500" />
            <Select
              value={sortMode}
              onValueChange={(value) => setSortMode(value as SortMode)}
            >
              <SelectTrigger
                aria-label="Sort runbooks"
                className="w-full border-white/10 bg-black/80 pl-9 text-slate-200 data-[size=default]:h-9 focus-visible:border-teal-500/40 focus-visible:ring-teal-500/10"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent position="popper" align="start" className={SELECT_CONTENT_CLASS}>
                <SelectItem value="newest" className={SELECT_ITEM_CLASS}>Newest first</SelectItem>
                <SelectItem value="oldest" className={SELECT_ITEM_CLASS}>Oldest first</SelectItem>
                <SelectItem value="alert_asc" className={SELECT_ITEM_CLASS}>Alert Name A–Z</SelectItem>
                <SelectItem value="alert_desc" className={SELECT_ITEM_CLASS}>Alert Name Z–A</SelectItem>
                <SelectItem value="revision_desc" className={SELECT_ITEM_CLASS}>Highest revision first</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex gap-5 text-sm text-slate-400">
            <span><strong className="text-slate-100">{library?.alert_count ?? 0}</strong> alert names</span>
            <span><strong className="text-slate-100">{library?.count ?? 0}</strong> revisions</span>
          </div>
        </div>
      </NeonGlassCard>

      <section className="space-y-4" aria-label="Runbooks grouped by Alert Name">
        {loading ? <p className="py-12 text-center text-sm text-slate-500">Loading runbook library…</p> : null}
        {!loading && visibleGroups.length === 0 ? (
          <NeonGlassCard accent="teal"><div className="flex flex-col items-center gap-3 px-6 py-14 text-center"><AlertCircleIcon className="size-7 text-slate-600" /><p className="text-sm text-slate-400">No runbooks match this Alert Name.</p></div></NeonGlassCard>
        ) : null}
        {visibleGroups.map((group) => (
          <NeonGlassCard key={group.alert_name} accent="teal" className="overflow-hidden">
            <div className="border-b border-white/[0.07] bg-gradient-to-r from-white/[0.025] via-black to-black px-5 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div><p className="text-xs uppercase tracking-[0.16em] text-teal-400/70">Alert Name</p><h2 className="mt-1 break-all text-lg font-semibold text-slate-100">{group.alert_name}</h2><p className="mt-1 text-xs text-slate-500">Exact-match scope · {group.count} stored revision{group.count === 1 ? "" : "s"}</p></div>
                <NeonActionButton accent="teal" size="sm" onClick={() => void download({ searchName: group.alert_name }, `${group.alert_name.replace(/[^a-z0-9_-]+/gi, "-")}-runbooks.json`)} disabled={busy}><FileJsonIcon className="size-4" /> Export alert</NeonActionButton>
              </div>
            </div>
            <div className="space-y-3 p-4">
              {group.runbooks.map((item) => <RunbookRevisionCard key={item.draft.runbook_id} item={item} onView={setView} onEdit={(selected) => setEdit(stateFromItem(selected))} onExport={(selected) => void download({ runbookId: selected.draft.runbook_id }, `${selected.draft.applicable_search_name.replace(/[^a-z0-9_-]+/gi, "-")}-r${selected.draft.revision}.json`)} />)}
            </div>
          </NeonGlassCard>
        ))}
      </section>

      <RunbookDetailsDialog item={view} onOpenChange={(open) => !open && setView(null)} />

      <Dialog open={Boolean(importDoc)} onOpenChange={(open) => !open && setImportDoc(null)}>
        <NeonDialogContent accent="teal">
          <form onSubmit={submitImport} className="space-y-4">
            <NeonDialogHeaderWithIcon accent="teal" icon={<UploadIcon className="size-5 text-teal-300" />} title="Import portable runbooks" description={`${importDoc?.runbooks.length ?? 0} runbook(s) found. Leave the source empty to import inert DRAFT artifacts.`} />
            <div className="space-y-4 px-6">
              <NeonField><NeonFieldLabel>Source record ID (optional)</NeonFieldLabel><NeonInput accent="teal" inputMode="numeric" value={importSourceId} onChange={(event) => setImportSourceId(event.target.value)} placeholder="Attach one imported runbook to a source" /></NeonField>
              <label className="flex items-start gap-3 rounded-lg border border-white/10 bg-black/60 p-3 text-sm text-slate-300"><input type="checkbox" className="mt-0.5 accent-teal-500" checked={verifyImport} onChange={(event) => setVerifyImport(event.target.checked)} /><span>Run fresh source verification after import. This requires one runbook, an acknowledged matching source, and Splunk runtime.</span></label>
            </div>
            <NeonDialogFooter className="px-6 pb-6"><NeonDialogFooterButton type="button" footerVariant="secondary" onClick={() => setImportDoc(null)}>Cancel</NeonDialogFooterButton><NeonDialogFooterButton type="submit" disabled={busy}>Import</NeonDialogFooterButton></NeonDialogFooter>
          </form>
        </NeonDialogContent>
      </Dialog>

      <Dialog open={Boolean(edit)} onOpenChange={(open) => !open && setEdit(null)}>
        <NeonDialogContent accent="teal" className="flex max-h-[92vh] flex-col sm:max-w-3xl">
          {edit ? <form onSubmit={submitEdit} className="flex max-h-[calc(92vh-3rem)] min-h-0 flex-col">
            <NeonDialogHeaderWithIcon accent="teal" icon={<PencilIcon className="size-5 text-teal-300" />} title="Create a new runbook revision" description="The existing revision remains immutable. Approval never carries to edited content." />
            <TsocOverflowScroll
              className="min-h-0 flex-1 space-y-4 overscroll-contain px-6 py-2 pr-4"
              maxHeight="min(68vh, 700px)"
            >
              <div className="grid gap-3 md:grid-cols-2"><NeonField><NeonFieldLabel>Title</NeonFieldLabel><NeonInput required accent="teal" value={edit.title} onChange={(event) => setEdit({ ...edit, title: event.target.value })} /></NeonField><NeonField><NeonFieldLabel>Exact Alert Name</NeonFieldLabel><NeonInput required accent="teal" value={edit.applicable_search_name} onChange={(event) => setEdit({ ...edit, applicable_search_name: event.target.value })} /></NeonField></div>
              <NeonField><NeonFieldLabel>Summary</NeonFieldLabel><textarea required className={TEXTAREA_CLASS} value={edit.summary} onChange={(event) => setEdit({ ...edit, summary: event.target.value })} /></NeonField>
              <div className="space-y-3"><div className="flex items-center justify-between"><NeonFieldLabel>Steps (maximum 3)</NeonFieldLabel><NeonActionButton type="button" size="sm" accent="teal" disabled={edit.steps.length >= 3} onClick={() => setEdit({ ...edit, steps: [...edit.steps, emptyStep(edit.steps.length)] })}><PlusIcon className="size-3.5" /> Add step</NeonActionButton></div>{edit.steps.map((step, index) => <div key={`${step.step_id}-${index}`} className="space-y-3 rounded-xl border border-white/10 bg-black/60 p-3"><div className="flex items-center justify-between text-sm font-medium text-slate-300">Step {index + 1}<button type="button" aria-label={`Remove step ${index + 1}`} disabled={edit.steps.length === 1} className="text-slate-600 hover:text-red-300 disabled:opacity-30" onClick={() => setEdit({ ...edit, steps: edit.steps.filter((_, itemIndex) => itemIndex !== index) })}><Trash2Icon className="size-4" /></button></div><div className="grid gap-3 md:grid-cols-2"><NeonInput required accent="teal" placeholder="Step ID" value={step.step_id} onChange={(event) => updateStep(index, "step_id", event.target.value)} /><NeonInput required accent="teal" placeholder="Step title" value={step.title} onChange={(event) => updateStep(index, "title", event.target.value)} /></div><textarea required className={TEXTAREA_CLASS} placeholder="Investigation intent" value={step.intent} onChange={(event) => updateStep(index, "intent", event.target.value)} /><div className="grid gap-3 md:grid-cols-2"><textarea required className={TEXTAREA_CLASS} placeholder="Expected evidence" value={step.expected_evidence} onChange={(event) => updateStep(index, "expected_evidence", event.target.value)} /><textarea required className={TEXTAREA_CLASS} placeholder="Stop condition" value={step.stop_condition} onChange={(event) => updateStep(index, "stop_condition", event.target.value)} /></div></div>)}</div>
              <NeonField><NeonFieldLabel>Decision rule</NeonFieldLabel><textarea required className={TEXTAREA_CLASS} value={edit.decision_rule} onChange={(event) => setEdit({ ...edit, decision_rule: event.target.value })} /></NeonField>
              <NeonField><NeonFieldLabel>Limitations (one per line)</NeonFieldLabel><textarea className={TEXTAREA_CLASS} value={edit.limitations.join("\n")} onChange={(event) => setEdit({ ...edit, limitations: event.target.value.split("\n").map((value) => value.trim()).filter(Boolean).slice(0, 10) })} /></NeonField>
              <div className="grid gap-3 md:grid-cols-2"><NeonField><NeonFieldLabel>Source record ID</NeonFieldLabel><NeonInput accent="teal" inputMode="numeric" disabled={edit.sourceLocked} value={edit.sourceId} onChange={(event) => setEdit({ ...edit, sourceId: event.target.value })} placeholder="Required for verification" /></NeonField><NeonField><NeonFieldLabel>Revision note</NeonFieldLabel><NeonInput accent="teal" value={edit.revision_note ?? ""} onChange={(event) => setEdit({ ...edit, revision_note: event.target.value })} /></NeonField></div>
              <label className="flex items-start gap-3 rounded-lg border border-white/10 bg-black/60 p-3 text-sm text-slate-300"><input type="checkbox" className="mt-0.5 accent-teal-500" checked={edit.verify_on_source} onChange={(event) => setEdit({ ...edit, verify_on_source: event.target.checked })} /><span>Run fresh source verification. Without this, the new revision is saved as DRAFT and requires verification before approval.</span></label>
            </TsocOverflowScroll>
            <NeonDialogFooter className="shrink-0 px-6 pb-6 pt-3"><NeonDialogFooterButton type="button" footerVariant="secondary" onClick={() => setEdit(null)}>Cancel</NeonDialogFooterButton><NeonDialogFooterButton type="submit" disabled={busy}>Save new revision</NeonDialogFooterButton></NeonDialogFooter>
          </form> : null}
        </NeonDialogContent>
      </Dialog>
    </div>
  )
}
