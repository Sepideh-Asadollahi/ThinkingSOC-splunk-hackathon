import { orderAlertChain } from "@/lib/api/graph/alert-centric"
import { groupFrameworkMapping } from "@/lib/framework-mapping"
import type {
  AttackAnalysisStep,
  GraphEdge,
  GraphFindingDetails,
  GraphNode,
} from "@/lib/api/graph/types"

export type AlertFrameworkContext = {
  killChainPhase?: string
  mitreTactic?: string
  mitreTechniqueId?: string
  mitreTechniqueName?: string
  description?: string
}

export function stepToFrameworkContext(step: AttackAnalysisStep): AlertFrameworkContext {
  return {
    killChainPhase: step.phase_label?.trim() || undefined,
    mitreTactic: step.mitre_tactic_name?.trim() || undefined,
    mitreTechniqueId: step.mitre_technique_id?.trim() || undefined,
    mitreTechniqueName: step.mitre_technique_name?.trim() || undefined,
    description: step.description?.trim() || undefined,
  }
}

function alertRowId(node: GraphNode): string | undefined {
  const id = node.properties?.alert_row_id
  return typeof id === "string" && id.trim() ? id.trim() : undefined
}

function chronologicalContributingIndex(
  contributing: NonNullable<GraphFindingDetails["details"]>["contributing_alerts"],
  rowId: string,
): number {
  const sorted = [...contributing].sort((a, b) => {
    const ta = Date.parse(a.timestamp ?? "")
    const tb = Date.parse(b.timestamp ?? "")
    const aTime = Number.isFinite(ta) ? ta : 0
    const bTime = Number.isFinite(tb) ? tb : 0
    return aTime - bTime
  })
  return sorted.findIndex((a) => a.alert_row_id === rowId)
}

function matchStepToNode(
  step: AttackAnalysisStep,
  node: GraphNode,
): boolean {
  const desc = (step.description ?? "").toLowerCase()
  const label = node.label.toLowerCase()
  const name = String(node.properties?.name ?? "").toLowerCase()
  if (!desc) return false
  return desc.includes(label) || label.includes(desc.slice(0, 12)) || (name !== "" && desc.includes(name))
}

/** Align attack_analysis_steps to chronology-ordered alert nodes on the graph. */
export function buildAlertFrameworkByNodeId(
  nodes: GraphNode[],
  edges: GraphEdge[],
  finding: GraphFindingDetails | null,
): Map<string, AlertFrameworkContext> {
  const out = new Map<string, AlertFrameworkContext>()
  const steps = finding?.details?.attack_analysis_steps ?? []
  const alertNodes = nodes.filter((n) => n.group.includes("Alert"))
  if (!alertNodes.length) return out

  const ordered = orderAlertChain(alertNodes, edges)
  const contributing = finding?.details?.contributing_alerts ?? []

  for (let i = 0; i < ordered.length; i += 1) {
    const node = ordered[i]
    let step: AttackAnalysisStep | undefined

    const rowId = alertRowId(node)
    if (rowId && contributing.length) {
      const idx = chronologicalContributingIndex(contributing, rowId)
      if (idx >= 0 && steps[idx]) step = steps[idx]
    }
    if (!step && steps[i]) step = steps[i]
    if (!step && steps.length) {
      step = steps.find((s) => matchStepToNode(s, node))
    }

    if (step) {
      out.set(node.id, stepToFrameworkContext(step))
    }
  }

  const { killChain, mitre } = groupFrameworkMapping(
    finding?.details?.framework_mappings ?? [],
  )
  if (killChain.length || mitre.length) {
    for (const [idx, node] of ordered.entries()) {
      if (out.has(node.id)) continue
      const kc = killChain[idx] ?? killChain[killChain.length - 1]
      const m = mitre[idx] ?? mitre[mitre.length - 1]
      if (!kc && !m) continue
      out.set(node.id, {
        killChainPhase: kc?.name ?? kc?.id,
        mitreTactic: m?.name,
        mitreTechniqueId: m?.id,
        mitreTechniqueName: m?.name,
      })
    }
  }

  return out
}

export function uniqueKillChainPhases(
  map: Map<string, AlertFrameworkContext>,
): string[] {
  const seen = new Set<string>()
  const list: string[] = []
  for (const ctx of map.values()) {
    const p = ctx.killChainPhase
    if (!p || seen.has(p)) continue
    seen.add(p)
    list.push(p)
  }
  return list
}

export function uniqueMitreTechniques(
  map: Map<string, AlertFrameworkContext>,
): string[] {
  const seen = new Set<string>()
  const list: string[] = []
  for (const ctx of map.values()) {
    const id = ctx.mitreTechniqueId
    if (!id || seen.has(id)) continue
    seen.add(id)
    const name = ctx.mitreTechniqueName
    list.push(name ? `${id} · ${name}` : id)
  }
  return list
}
