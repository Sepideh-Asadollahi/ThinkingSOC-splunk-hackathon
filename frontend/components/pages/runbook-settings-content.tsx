"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import {
  BookOpenCheckIcon,
  CheckCircle2Icon,
  DatabaseIcon,
  RefreshCwIcon,
  SaveIcon,
  ShieldCheckIcon,
  SparklesIcon,
  TriangleAlertIcon,
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
} from "@/components/neon-glass"
import { ApiError, backendFetch } from "@/lib/api/client"
import {
  fetchRunbookRuntimeStatus,
  type RunbookRuntimeStatus,
} from "@/lib/api/investigation-workflow"
import type { IntegrationSettingRecord } from "@/lib/api/types"
import { cn } from "@/lib/utils"

type RunbookForm = {
  enabled: boolean
  autopilotEnabled: boolean
  maxSteps: string
  defaultManualMinutes: string
  artifactScanLimit: string
  analystHourlyCost: string
  inputTokenCost: string
  outputTokenCost: string
}

const EMPTY_FORM: RunbookForm = {
  enabled: true,
  autopilotEnabled: true,
  maxSteps: "3",
  defaultManualMinutes: "25",
  artifactScanLimit: "500",
  analystHourlyCost: "65",
  inputTokenCost: "0",
  outputTokenCost: "0",
}

const SETTING_IDS = {
  enabled: "tsoc_runbook_enabled",
  autopilotEnabled: "tsoc_runbook_autopilot_enabled",
  maxSteps: "tsoc_runbook_max_steps",
  defaultManualMinutes: "tsoc_runbook_default_manual_minutes",
  artifactScanLimit: "tsoc_runbook_artifact_scan_limit",
  analystHourlyCost: "tsoc_runbook_analyst_hourly_cost_usd",
  inputTokenCost: "tsoc_runbook_input_cost_per_1m_tokens",
  outputTokenCost: "tsoc_runbook_output_cost_per_1m_tokens",
} as const

function errorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) return error.message
  return "Runbook settings operation failed"
}

function formFromSettings(rows: IntegrationSettingRecord[]): RunbookForm {
  const byId = new Map(rows.map((row) => [row.id, row.value]))
  return {
    enabled: byId.get(SETTING_IDS.enabled) !== "false",
    autopilotEnabled: byId.get(SETTING_IDS.autopilotEnabled) !== "false",
    maxSteps: byId.get(SETTING_IDS.maxSteps) || "3",
    defaultManualMinutes: byId.get(SETTING_IDS.defaultManualMinutes) || "25",
    artifactScanLimit: byId.get(SETTING_IDS.artifactScanLimit) || "500",
    analystHourlyCost: byId.get(SETTING_IDS.analystHourlyCost) || "65",
    inputTokenCost: byId.get(SETTING_IDS.inputTokenCost) || "0",
    outputTokenCost: byId.get(SETTING_IDS.outputTokenCost) || "0",
  }
}

function ReadinessCard({
  icon,
  label,
  value,
  ready,
}: {
  icon: React.ReactNode
  label: string
  value: string
  ready: boolean
}) {
  return (
    <NeonGlassCard accent="teal" className="h-full">
      <div className="flex h-full items-center gap-3 p-4">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-teal-500/20 bg-teal-500/[0.08] text-teal-300">
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
          <p className="mt-1 truncate text-sm font-medium text-slate-100">{value}</p>
        </div>
        <span
          className={cn(
            "size-2.5 shrink-0 rounded-full shadow-[0_0_12px_currentColor]",
            ready ? "bg-emerald-400 text-emerald-400" : "bg-amber-400 text-amber-400"
          )}
          aria-label={ready ? `${label} ready` : `${label} not ready`}
        />
      </div>
    </NeonGlassCard>
  )
}

export function RunbookSettingsContent() {
  const [form, setForm] = useState<RunbookForm>(EMPTY_FORM)
  const [savedForm, setSavedForm] = useState<RunbookForm>(EMPTY_FORM)
  const [runtime, setRuntime] = useState<RunbookRuntimeStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [allSettings, runtimeStatus] = await Promise.all([
        backendFetch<IntegrationSettingRecord[]>("/integrations/settings"),
        fetchRunbookRuntimeStatus(),
      ])
      const next = formFromSettings(allSettings.filter((row) => row.category === "runbook"))
      setForm(next)
      setSavedForm(next)
      setRuntime(runtimeStatus)
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

  const isDirty = useMemo(() => JSON.stringify(form) !== JSON.stringify(savedForm), [form, savedForm])

  async function save() {
    const maxSteps = Number(form.maxSteps)
    const manualMinutes = Number(form.defaultManualMinutes)
    const scanLimit = Number(form.artifactScanLimit)
    const analystHourlyCost = Number(form.analystHourlyCost)
    const inputTokenCost = Number(form.inputTokenCost)
    const outputTokenCost = Number(form.outputTokenCost)
    if (!Number.isInteger(maxSteps) || maxSteps < 1 || maxSteps > 3) {
      setError("Maximum steps must be an integer between 1 and 3.")
      return
    }
    if (!Number.isInteger(manualMinutes) || manualMinutes < 5 || manualMinutes > 120) {
      setError("Manual baseline must be an integer between 5 and 120 minutes.")
      return
    }
    if (!Number.isInteger(scanLimit) || scanLimit < 50 || scanLimit > 1000) {
      setError("Artifact scan limit must be an integer between 50 and 1000.")
      return
    }
    if (![analystHourlyCost, inputTokenCost, outputTokenCost].every((value) => Number.isFinite(value) && value >= 0 && value <= 1000)) {
      setError("Evaluation costs must be numbers between 0 and 1000 USD.")
      return
    }

    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      await Promise.all([
        [SETTING_IDS.enabled, String(form.enabled)],
        [SETTING_IDS.autopilotEnabled, String(form.autopilotEnabled)],
        [SETTING_IDS.maxSteps, String(maxSteps)],
        [SETTING_IDS.defaultManualMinutes, String(manualMinutes)],
        [SETTING_IDS.artifactScanLimit, String(scanLimit)],
        [SETTING_IDS.analystHourlyCost, String(analystHourlyCost)],
        [SETTING_IDS.inputTokenCost, String(inputTokenCost)],
        [SETTING_IDS.outputTokenCost, String(outputTokenCost)],
      ].map(([id, value]) =>
        backendFetch(`/integrations/settings/${encodeURIComponent(id)}`, {
          method: "PATCH",
          body: JSON.stringify({ value }),
        })
      ))
      setNotice("Forge settings saved and applied to new operations.")
      await load()
    } catch (saveError) {
      setError(errorMessage(saveError))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6" data-testid="runbook-settings-page">
      <section className="flex flex-wrap items-center justify-between gap-4" aria-labelledby="runbook-page-title">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex size-11 shrink-0 items-center justify-center rounded-xl border border-teal-500/20 bg-teal-500/[0.08] shadow-[0_0_24px_-10px_rgba(20,184,166,0.28)]">
            <BookOpenCheckIcon className="size-5 text-teal-300" />
          </div>
          <div className="min-w-0">
            <h1 id="runbook-page-title" className="bg-gradient-to-r from-white via-slate-200 to-teal-400/90 bg-clip-text text-2xl font-semibold text-transparent">
              ThinkingSOC Forge
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              Verified runbook policy, runtime readiness, and measurable productivity defaults
            </p>
          </div>
        </div>
        <NeonBadge className={runtime?.ready ? "border-emerald-500/30 text-emerald-300" : "border-amber-500/30 text-amber-300"}>
          {runtime?.ready ? "READY" : "ACTION REQUIRED"}
        </NeonBadge>
      </section>

      <section className="grid gap-4 md:grid-cols-3" aria-label="Forge readiness">
        <ReadinessCard
          icon={<DatabaseIcon className="size-4" />}
          label="Persistence"
          value={runtime?.postgres_configured ? "PostgreSQL configured" : "PostgreSQL required"}
          ready={Boolean(runtime?.postgres_configured)}
        />
        <ReadinessCard
          icon={<SparklesIcon className="size-4" />}
          label="Compiler model"
          value={runtime?.configured_model || "Model not configured"}
          ready={Boolean(runtime?.llm_configured)}
        />
        <ReadinessCard
          icon={<ShieldCheckIcon className="size-4" />}
          label="Read-only replay"
          value={runtime?.splunk_configured && runtime.execution_enabled
            ? runtime.mcp_configured
              ? "MCP preferred · REST API fallback"
              : "REST API fallback ready"
            : "Splunk REST API setup required"}
          ready={Boolean(runtime?.splunk_configured && runtime.execution_enabled)}
        />
      </section>

      {error ? (
        <NeonAlert variant="destructive">
          <TriangleAlertIcon className="size-4" />
          <NeonAlertTitle>Unable to apply Runbook settings</NeonAlertTitle>
          <NeonAlertDescription>{error}</NeonAlertDescription>
        </NeonAlert>
      ) : null}
      {notice ? (
        <NeonAlert>
          <CheckCircle2Icon className="size-4 text-emerald-400" />
          <NeonAlertTitle>Settings updated</NeonAlertTitle>
          <NeonAlertDescription>{notice}</NeonAlertDescription>
        </NeonAlert>
      ) : null}

      <NeonGlassCard accent="teal" animatePreset="page">
        <NeonCardHeader
          accent="teal"
          icon={<BookOpenCheckIcon className="size-5 text-teal-300" />}
          title="Forge settings"
          description="Operational controls are configurable; verification and human-gate safety invariants remain fixed."
          actions={
            <>
              <NeonActionButton accent="teal" onClick={() => void load()} disabled={loading || saving}>
                <RefreshCwIcon className="size-4" />
                Refresh
              </NeonActionButton>
              <NeonActionButton accent="teal" onClick={() => void save()} disabled={!isDirty || loading || saving}>
                <SaveIcon className="size-4" />
                {saving ? "Saving…" : "Save changes"}
              </NeonActionButton>
            </>
          }
        />

        <div className="space-y-6 px-6 pb-6">
          {loading ? <p className="pt-2 text-sm text-slate-500" aria-busy="true">Loading Forge settings…</p> : null}
          {!loading ? (
            <>
              <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-teal-500/15 bg-teal-500/[0.04] p-4">
                <div>
                  <p className="text-sm font-medium text-slate-100">Enable ThinkingSOC Forge</p>
                  <p className="mt-1 text-xs text-slate-400">Disabling blocks compile, approval, and reuse while preserving read-only access to existing artifacts.</p>
                </div>
                <label className="inline-flex cursor-pointer items-center gap-3 text-sm text-slate-300">
                  <input
                    type="checkbox"
                    className="size-4 accent-teal-500"
                    checked={form.enabled}
                    onChange={(event) => setForm((current) => ({ ...current, enabled: event.target.checked }))}
                  />
                  {form.enabled ? "Enabled" : "Disabled"}
                </label>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-violet-400/15 bg-violet-400/[0.03] p-4">
                <div>
                  <p className="text-sm font-medium text-slate-100">Enable Runbook Autopilot Agents</p>
                  <p className="mt-1 text-xs text-slate-400">
                    Allows bounded evidence, library, compile/verify, and response-preview orchestration.
                    Approval and execution remain fixed human-only gates.
                  </p>
                </div>
                <label className="inline-flex cursor-pointer items-center gap-3 text-sm text-slate-300">
                  <input
                    type="checkbox"
                    className="size-4 accent-violet-400"
                    checked={form.autopilotEnabled}
                    onChange={(event) => setForm((current) => ({ ...current, autopilotEnabled: event.target.checked }))}
                  />
                  {form.autopilotEnabled ? "Enabled" : "Disabled"}
                </label>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <NeonField>
                  <NeonFieldLabel htmlFor="runbook-max-steps">Maximum steps</NeonFieldLabel>
                  <NeonInput id="runbook-max-steps" accent="teal" type="number" min={1} max={3} value={form.maxSteps} onChange={(event) => setForm((current) => ({ ...current, maxSteps: event.target.value }))} />
                  <p className="text-xs text-slate-500">Strict compiler limit: 1–3 ordered intents.</p>
                </NeonField>
                <NeonField>
                  <NeonFieldLabel htmlFor="runbook-manual-baseline">Default manual baseline</NeonFieldLabel>
                  <NeonInput id="runbook-manual-baseline" accent="teal" type="number" min={5} max={120} value={form.defaultManualMinutes} onChange={(event) => setForm((current) => ({ ...current, defaultManualMinutes: event.target.value }))} />
                  <p className="text-xs text-slate-500">Editable demo baseline in minutes; never estimated by the model.</p>
                </NeonField>
                <NeonField>
                  <NeonFieldLabel htmlFor="runbook-scan-limit">Artifact scan limit</NeonFieldLabel>
                  <NeonInput id="runbook-scan-limit" accent="teal" type="number" min={50} max={1000} step={50} value={form.artifactScanLimit} onChange={(event) => setForm((current) => ({ ...current, artifactScanLimit: event.target.value }))} />
                  <p className="text-xs text-slate-500">Bounded lookup per append-only artifact type.</p>
                </NeonField>
              </div>
              <div className="grid gap-4 border-t border-white/[0.07] pt-5 md:grid-cols-3">
                <NeonField>
                  <NeonFieldLabel htmlFor="runbook-analyst-cost">Analyst hourly cost (USD)</NeonFieldLabel>
                  <NeonInput id="runbook-analyst-cost" accent="teal" type="number" min={0} max={1000} step="0.01" value={form.analystHourlyCost} onChange={(event) => setForm((current) => ({ ...current, analystHourlyCost: event.target.value }))} />
                  <p className="text-xs text-slate-500">Loaded labor rate used for projected replay value.</p>
                </NeonField>
                <NeonField>
                  <NeonFieldLabel htmlFor="runbook-input-token-cost">Input cost / 1M tokens</NeonFieldLabel>
                  <NeonInput id="runbook-input-token-cost" accent="teal" type="number" min={0} max={1000} step="0.0001" value={form.inputTokenCost} onChange={(event) => setForm((current) => ({ ...current, inputTokenCost: event.target.value }))} />
                  <p className="text-xs text-slate-500">Keep zero for free compiler models.</p>
                </NeonField>
                <NeonField>
                  <NeonFieldLabel htmlFor="runbook-output-token-cost">Output cost / 1M tokens</NeonFieldLabel>
                  <NeonInput id="runbook-output-token-cost" accent="teal" type="number" min={0} max={1000} step="0.0001" value={form.outputTokenCost} onChange={(event) => setForm((current) => ({ ...current, outputTokenCost: event.target.value }))} />
                  <p className="text-xs text-slate-500">Applied only to measured compiler completion tokens.</p>
                </NeonField>
              </div>
            </>
          ) : null}
        </div>
      </NeonGlassCard>

      <NeonGlassCard accent="teal">
        <NeonCardHeader
          accent="teal"
          icon={<ShieldCheckIcon className="size-5 text-teal-300" />}
          title="Fixed trust policy"
          description="These controls are deliberately not configurable in the MVP."
        />
        <div className="grid gap-3 px-6 pb-6 md:grid-cols-3">
          {[
            ["Analyst acknowledgment", "A source investigation must be acknowledged before compilation."],
            ["Source evidence", "Every step must parse, execute safely, and return evidence before approval."],
            ["Exact detection match", "Replay and reuse require the same search_name and a different Splunk SID."],
          ].map(([title, description]) => (
            <div key={title} className="rounded-xl border border-white/10 bg-black/30 p-4">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-100">
                <CheckCircle2Icon className="size-4 text-emerald-400" />
                {title}
              </div>
              <p className="mt-2 text-xs leading-5 text-slate-400">{description}</p>
            </div>
          ))}
        </div>
      </NeonGlassCard>
    </div>
  )
}
