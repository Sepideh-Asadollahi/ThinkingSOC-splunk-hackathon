"use client"

import Link from "next/link"
import {
  ArrowRightIcon,
  BotIcon,
  BookOpenCheckIcon,
  CheckCircle2Icon,
  Clock3Icon,
  FileSearchIcon,
  MessageSquareTextIcon,
  ShieldCheckIcon,
  WorkflowIcon,
} from "lucide-react"

import { NeonCardHeader, NeonGlassCard } from "@/components/neon-glass"
import type { DashboardRunbookOps } from "@/lib/api/types"
import { cn } from "@/lib/utils"

function pct(value: number, total: number): number {
  if (total <= 0) return 0
  return Math.min(100, Math.max(0, Math.round((value / total) * 100)))
}

function Metric({
  label,
  value,
  hint,
  icon,
}: {
  label: string
  value: string
  hint: string
  icon: React.ReactNode
}) {
  return (
    <div className="rounded-xl border border-white/[0.08] bg-black/35 p-3.5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-slate-500">{label}</p>
          <p className="mt-1.5 text-2xl font-semibold tabular-nums text-slate-100">{value}</p>
        </div>
        <div className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-teal-500/20 bg-teal-500/[0.08] text-teal-300">
          {icon}
        </div>
      </div>
      <p className="mt-1 text-xs text-slate-500">{hint}</p>
    </div>
  )
}

function Outcome({
  label,
  value,
  total,
  tone,
}: {
  label: string
  value: number
  total: number
  tone: "verified" | "abstained" | "failed"
}) {
  const width = pct(value, total)
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3 text-xs">
        <span className="text-slate-400">{label}</span>
        <span className="font-medium tabular-nums text-slate-200">{value.toLocaleString()}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
        <div
          className={cn(
            "h-full rounded-full transition-[width] duration-500",
            tone === "verified" && "bg-teal-400/75",
            tone === "abstained" && "bg-amber-300/70",
            tone === "failed" && "bg-rose-400/65"
          )}
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  )
}

export function DashboardRunbookOperations({ ops }: { ops: DashboardRunbookOps }) {
  const lifecycle = [
    { label: "Latest Runbooks", value: ops.latest_runbooks, icon: BookOpenCheckIcon },
    { label: "Source verified", value: ops.source_verified, icon: FileSearchIcon },
    { label: "Human approved", value: ops.human_approved, icon: ShieldCheckIcon },
    { label: "Reusable alert names", value: ops.reusable_alert_names, icon: CheckCircle2Icon },
  ]
  const approvalRate = pct(ops.human_approved, ops.source_verified)
  const reuseRate = pct(ops.reused, ops.executions)
  const autopilotRate = pct(ops.autopilot_completed, ops.autopilot_sessions)

  return (
    <NeonGlassCard accent="teal" animatePreset="page">
      <NeonCardHeader
        accent="teal"
        icon={<WorkflowIcon className="size-4" />}
        title="Runbook operations"
        description="ThinkingSOC Lite lifecycle, guarded execution, Autopilot, and analyst Chat"
        actions={
          <span className="rounded-full border border-teal-500/20 bg-teal-500/[0.07] px-2.5 py-1 text-[11px] font-medium text-teal-200">
            Human gated
          </span>
        }
      />

      <div className="space-y-5 p-4 sm:p-5">
        <div className="grid gap-2 md:grid-cols-4">
          {lifecycle.map((item, index) => (
            <div key={item.label} className="flex min-w-0 items-stretch gap-2">
              <div className="flex min-h-[94px] min-w-0 flex-1 flex-col justify-between rounded-xl border border-white/[0.08] bg-black/40 p-3.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.025)]">
                <div className="flex items-center justify-between gap-2">
                  <item.icon className="size-4 text-teal-300/85" />
                  <span className="text-[10px] uppercase tracking-[0.15em] text-slate-600">Stage {index + 1}</span>
                </div>
                <div>
                  <p className="text-xl font-semibold tabular-nums text-slate-100">{item.value.toLocaleString()}</p>
                  <p className="truncate text-xs text-slate-400">{item.label}</p>
                </div>
              </div>
              {index < lifecycle.length - 1 ? (
                <ArrowRightIcon className="mt-[39px] hidden size-4 shrink-0 text-teal-500/45 md:block" />
              ) : null}
            </div>
          ))}
        </div>

        <div className="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Metric
              label="Evidence"
              value={ops.evidence_rows.toLocaleString()}
              hint="Rows returned by guarded reuse"
              icon={<FileSearchIcon className="size-4" />}
            />
            <Metric
              label="Time saved"
              value={`${Math.round(ops.estimated_minutes_saved).toLocaleString()}m`}
              hint="Estimated analyst minutes"
              icon={<Clock3Icon className="size-4" />}
            />
            <Metric
              label="Autopilot"
              value={`${ops.autopilot_completed}/${ops.autopilot_sessions}`}
              hint={`${autopilotRate}% sessions completed`}
              icon={<BotIcon className="size-4" />}
            />
            <Metric
              label="SOC Chat"
              value={ops.chat_conversations.toLocaleString()}
              hint={`${ops.chat_messages.toLocaleString()} persisted messages`}
              icon={<MessageSquareTextIcon className="size-4" />}
            />
          </div>

          <div className="rounded-xl border border-white/[0.08] bg-black/35 p-4">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-200">Execution outcomes</p>
                <p className="text-xs text-slate-500">{ops.executions.toLocaleString()} guarded runs</p>
              </div>
              <div className="text-right text-xs text-slate-500">
                <p>{reuseRate}% reused</p>
                <p>{approvalRate}% approval coverage</p>
              </div>
            </div>
            <div className="space-y-3.5">
              <Outcome label="Reused with evidence" value={ops.reused} total={ops.executions} tone="verified" />
              <Outcome label="Safe abstention / no evidence" value={ops.no_evidence} total={ops.executions} tone="abstained" />
              <Outcome label="Failed" value={ops.failed} total={ops.executions} tone="failed" />
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.06] pt-4">
          <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-500">
            <span>{ops.shadow_runs.toLocaleString()} shadow runs</span>
            <span>{ops.response_previews.toLocaleString()} safe-response previews</span>
            <span>Exact Alert Name · read-only SPL · MCP→REST fallback</span>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/runbooks/library" className="rounded-lg border border-white/10 bg-white/[0.025] px-3 py-2 text-xs text-slate-300 transition-colors hover:border-teal-500/30 hover:text-white">
              Runbook Library
            </Link>
            <Link href="/runbooks" className="rounded-lg border border-white/10 bg-white/[0.025] px-3 py-2 text-xs text-slate-300 transition-colors hover:border-teal-500/30 hover:text-white">
              ThinkingSOC Lite
            </Link>
            <Link href="/soc-chat" className="rounded-lg border border-teal-500/20 bg-teal-500/[0.07] px-3 py-2 text-xs text-teal-200 transition-colors hover:bg-teal-500/[0.12]">
              Ask in Chat
            </Link>
          </div>
        </div>
      </div>
    </NeonGlassCard>
  )
}
