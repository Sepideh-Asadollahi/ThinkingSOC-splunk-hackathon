import type { AttackAnalysisStep } from "@/lib/api/graph/types"

export type AttackNarrativeStep = {
  step: number
  phaseLabel: string
  description: string
  mitreLabel?: string
}

export function formatMitreLabel(step: AttackAnalysisStep): string | undefined {
  const id = step.mitre_technique_id?.trim()
  const name = step.mitre_technique_name?.trim()
  if (id && name) return `${id} · ${name}`
  if (id) return id
  if (name) return name
  const tactic = step.mitre_tactic_name?.trim()
  return tactic || undefined
}

/** Numbered attack story steps from finding details (chronological order preserved). */
export function buildAttackNarrativeSteps(
  steps: AttackAnalysisStep[] | undefined | null,
): AttackNarrativeStep[] {
  if (!steps?.length) return []
  return steps
    .filter((s) => (s.description ?? "").trim() || (s.phase_label ?? "").trim())
    .map((s, index) => ({
      step: index + 1,
      phaseLabel: (s.phase_label ?? "Step").trim() || "Step",
      description: (s.description ?? "").trim(),
      mitreLabel: formatMitreLabel(s),
    }))
}
