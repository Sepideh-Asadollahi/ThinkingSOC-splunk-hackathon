"use client"

import { NeonBadge } from "@/components/neon-glass"

import { DataSection } from "./section"
import { asRecord } from "./utils"

/** Matches backend compact/display IOC row (VT API v3 attribute names). */
export type ThreatIntelFinding = {
  ioc: string
  ioc_type: string
  vt_id?: string
  vt_type?: string
  verdict: string
  error?: string
  last_analysis_stats?: Record<string, number>
  reputation?: number
  total_votes?: Record<string, number>
  last_analysis_date?: number | string
  link?: string
  tags?: string[]
  categories?: Record<string, string>
  md5?: string
  sha1?: string
  sha256?: string
  meaningful_name?: string
  type_description?: string
}

export type CompactThreatIntel = {
  status?: string
  source?: string
  reason?: string
  checked_ioc_count?: number
  note?: string
  findings?: ThreatIntelFinding[]
  /** All VT lookups for this analysis (UI); findings may be a significant subset for LLM. */
  iocs?: ThreatIntelFinding[]
}

const VT_STAT_KEYS = [
  "malicious",
  "suspicious",
  "harmless",
  "undetected",
  "timeout",
  "confirmed-timeout",
  "failure",
  "type-unsupported",
] as const

function statsFromFinding(f: ThreatIntelFinding): Record<string, number> {
  if (f.last_analysis_stats && typeof f.last_analysis_stats === "object") {
    return f.last_analysis_stats
  }
  return {}
}

function legacyIocFromEntry(
  raw: Record<string, unknown>,
  ioc: string,
  iocType: string
): ThreatIntelFinding {
  const summary = asRecord(raw.summary)
  const stats = asRecord(summary?.last_analysis_stats) ?? {}
  const malicious = Number(stats.malicious ?? raw.malicious ?? 0)
  const suspicious = Number(stats.suspicious ?? raw.suspicious ?? 0)
  const harmless = Number(stats.harmless ?? 0)
  const undetected = Number(stats.undetected ?? 0)
  const timeout = Number(stats.timeout ?? 0)
  const err = raw.error != null ? String(raw.error) : undefined

  let verdict = "undetected"
  if (err === "not_found") verdict = "not_found"
  else if (err) verdict = "error"
  else if (malicious > 0) verdict = "malicious"
  else if (suspicious > 0) verdict = "suspicious"
  else if (harmless > 0) verdict = "harmless"

  const votes = asRecord(summary?.total_votes)
  const row: ThreatIntelFinding = {
    ioc,
    ioc_type: iocType,
    verdict,
    vt_id: summary?.id != null ? String(summary.id) : undefined,
    vt_type: summary?.type != null ? String(summary.type) : undefined,
    last_analysis_stats: {
      malicious,
      suspicious,
      harmless,
      undetected,
      timeout,
    },
    reputation: summary?.reputation != null ? Number(summary.reputation) : undefined,
    total_votes:
      votes && (votes.harmless != null || votes.malicious != null)
        ? { harmless: Number(votes.harmless ?? 0), malicious: Number(votes.malicious ?? 0) }
        : undefined,
    last_analysis_date:
      summary?.last_analysis_date != null ? (summary.last_analysis_date as number | string) : undefined,
    link: summary?.link != null ? String(summary.link) : undefined,
    error: err,
  }

  if (Array.isArray(summary?.tags)) {
    row.tags = summary.tags as string[]
  }
  if (summary?.categories && typeof summary.categories === "object") {
    row.categories = summary.categories as Record<string, string>
  }
  for (const key of ["md5", "sha1", "sha256", "meaningful_name", "type_description"] as const) {
    if (summary?.[key] != null) row[key] = String(summary[key])
  }
  return row
}

function iocsFromLegacyVt(vt: Record<string, unknown>): ThreatIntelFinding[] {
  const iocs: ThreatIntelFinding[] = []
  const buckets: [string, string][] = [
    ["file_hash", "files"],
    ["ip", "ips"],
    ["domain", "domains"],
    ["url", "urls"],
  ]
  for (const [iocType, key] of buckets) {
    const bucket = asRecord(vt[key])
    if (!bucket) continue
    for (const [ioc, raw] of Object.entries(bucket)) {
      const entry = asRecord(raw)
      if (!entry) continue
      iocs.push(legacyIocFromEntry(entry, ioc, iocType))
    }
  }
  return iocs
}

export function pickThreatIntel(data: Record<string, unknown>): CompactThreatIntel | null {
  const direct = asRecord(data.threat_intel)
  if (!direct || Object.keys(direct).length === 0) return null

  if (direct.findings != null || direct.status != null || direct.iocs != null) {
    const ti = direct as unknown as CompactThreatIntel
    const iocs = Array.isArray(ti.iocs) ? ti.iocs : []
    const findings = Array.isArray(ti.findings) ? ti.findings : []
    return {
      ...ti,
      iocs: iocs.length > 0 ? iocs : findings,
    }
  }

  const vt = asRecord(direct.virustotal)
  if (!vt) return null

  const iocs = iocsFromLegacyVt(vt)
  const findings = iocs.filter((f) => {
    const v = f.verdict.toLowerCase()
    return v === "malicious" || v === "suspicious" || (f.reputation != null && f.reputation < 0)
  })

  return {
    status: findings.length ? "ok" : "no_significant_hits",
    source: "virustotal",
    checked_ioc_count: iocs.length,
    findings,
    iocs,
    note:
      iocs.length > 0
        ? "VirusTotal enrichment (all checked IOCs)."
        : "No VirusTotal lookups in stored enrichment.",
  }
}

function verdictBadgeClass(verdict: string): string {
  const v = verdict.toLowerCase()
  if (v === "malicious" || v === "error") return "border-red-500/40 text-red-300"
  if (v === "suspicious") return "border-amber-500/40 text-amber-300"
  if (v === "harmless") return "border-emerald-500/30 text-emerald-300"
  if (v === "not_found") return "border-white/15 text-slate-500"
  return "border-white/15 text-slate-400"
}

function formatAnalysisDate(value: number | string | undefined): string | null {
  if (value == null || value === "") return null
  const n = typeof value === "number" ? value : Number(value)
  if (!Number.isFinite(n)) return String(value)
  const ms = n > 1e12 ? n : n * 1000
  try {
    return new Date(ms).toISOString()
  } catch {
    return String(value)
  }
}

function FindingRow({ finding }: { finding: ThreatIntelFinding }) {
  const stats = statsFromFinding(finding)
  const label = finding.vt_type ? `${finding.ioc_type} · ${finding.vt_type}` : finding.ioc_type
  const analysisAt = formatAnalysisDate(finding.last_analysis_date)

  return (
    <li className="rounded-md border border-white/10 bg-black/30 p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <NeonBadge className="border-violet-500/30 font-mono text-violet-200">
          {finding.ioc}
        </NeonBadge>
        <NeonBadge className="border-white/15 text-slate-400">{label}</NeonBadge>
        <NeonBadge className={verdictBadgeClass(finding.verdict)}>{finding.verdict}</NeonBadge>
        {finding.error && finding.verdict !== "not_found" ? (
          <NeonBadge className="border-red-500/30 text-xs text-red-300">{finding.error}</NeonBadge>
        ) : null}
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {VT_STAT_KEYS.map((k) =>
          stats[k] != null ? (
            <NeonBadge
              key={k}
              className={
                k === "malicious"
                  ? "border-red-500/30 text-xs text-red-300"
                  : k === "suspicious"
                    ? "border-amber-500/30 text-xs text-amber-300"
                    : "border-white/10 text-xs text-slate-400"
              }
            >
              {k}: {stats[k]}
            </NeonBadge>
          ) : null
        )}
        {finding.reputation != null ? (
          <NeonBadge className="border-white/10 text-xs text-slate-400">
            reputation: {finding.reputation}
          </NeonBadge>
        ) : null}
        {finding.total_votes?.harmless != null || finding.total_votes?.malicious != null ? (
          <NeonBadge className="border-white/10 text-xs text-slate-400">
            votes: harmless {finding.total_votes?.harmless ?? 0}, malicious{" "}
            {finding.total_votes?.malicious ?? 0}
          </NeonBadge>
        ) : null}
      </div>
      {(finding.md5 || finding.sha1 || finding.sha256 || finding.meaningful_name) && (
        <dl className="mt-2 grid gap-1 text-xs text-slate-400 sm:grid-cols-2">
          {finding.meaningful_name ? (
            <div>
              <dt className="text-slate-500">name</dt>
              <dd className="font-mono text-slate-300">{finding.meaningful_name}</dd>
            </div>
          ) : null}
          {finding.type_description ? (
            <div>
              <dt className="text-slate-500">type</dt>
              <dd>{finding.type_description}</dd>
            </div>
          ) : null}
          {finding.md5 ? (
            <div>
              <dt className="text-slate-500">md5</dt>
              <dd className="break-all font-mono text-slate-300">{finding.md5}</dd>
            </div>
          ) : null}
          {finding.sha1 ? (
            <div>
              <dt className="text-slate-500">sha1</dt>
              <dd className="break-all font-mono text-slate-300">{finding.sha1}</dd>
            </div>
          ) : null}
          {finding.sha256 ? (
            <div className="sm:col-span-2">
              <dt className="text-slate-500">sha256</dt>
              <dd className="break-all font-mono text-slate-300">{finding.sha256}</dd>
            </div>
          ) : null}
        </dl>
      )}
      {analysisAt ? <p className="mt-2 text-xs text-slate-500">last analysis: {analysisAt}</p> : null}
      {finding.link ? (
        <p className="mt-1 text-xs">
          <a
            href={finding.link}
            target="_blank"
            rel="noopener noreferrer"
            className="text-violet-300 underline-offset-2 hover:underline"
          >
            View on VirusTotal
          </a>
        </p>
      ) : null}
      {finding.tags?.length ? (
        <p className="mt-2 text-xs text-slate-500">tags: {finding.tags.join(", ")}</p>
      ) : null}
      {finding.categories && Object.keys(finding.categories).length > 0 ? (
        <p className="mt-1 text-xs text-slate-500">
          categories:{" "}
          {Object.entries(finding.categories)
            .map(([k, v]) => `${k}=${v}`)
            .join("; ")}
        </p>
      ) : null}
    </li>
  )
}

function displayIocs(ti: CompactThreatIntel): ThreatIntelFinding[] {
  const iocs = Array.isArray(ti.iocs) ? ti.iocs : []
  if (iocs.length > 0) return iocs
  return Array.isArray(ti.findings) ? ti.findings : []
}

export function ThreatIntelPanelContent({ ti }: { ti: CompactThreatIntel }) {
  const iocs = displayIocs(ti)
  const status = String(ti.status ?? "")

  if (status === "unavailable") {
    return (
      <p className="text-sm text-slate-500">
        {ti.note ?? "Threat intelligence enrichment was not applied."}
        {ti.reason ? ` (${ti.reason})` : null}
      </p>
    )
  }

  return (
    <div className="space-y-3">
      {ti.note ? <p className="text-sm text-slate-400">{ti.note}</p> : null}
      {ti.checked_ioc_count != null ? (
        <p className="text-xs text-slate-500">IOCs checked: {ti.checked_ioc_count}</p>
      ) : iocs.length > 0 ? (
        <p className="text-xs text-slate-500">IOCs checked: {iocs.length}</p>
      ) : null}
      {iocs.length > 0 ? (
        <ul className="space-y-2">
          {iocs.map((f) => (
            <FindingRow key={`${f.ioc_type}-${f.ioc}`} finding={f} />
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">No VirusTotal lookups for this alert.</p>
      )}
    </div>
  )
}

export function ThreatIntelPanel({ data }: { data: Record<string, unknown> }) {
  const ti = pickThreatIntel(data)
  if (!ti) {
    return <p className="text-sm text-slate-500">No threat intelligence data for this analysis.</p>
  }
  return <ThreatIntelPanelContent ti={ti} />
}

export function ThreatIntelSection({ data }: { data: Record<string, unknown> }) {
  const ti = pickThreatIntel(data)
  if (!ti) return null
  return (
    <DataSection
      title="Threat intelligence"
      description="VirusTotal API v3 — all checked IOCs"
      accent="violet"
      defaultOpen
    >
      <ThreatIntelPanelContent ti={ti} />
    </DataSection>
  )
}
