import { isTruncated } from "@/components/correlation/explorer/graph-canvas-tooltip"
import type { AlertFrameworkContext } from "@/lib/api/graph/attack-framework"

import {
  ALERT_LABEL_MAX,
  KC_LABEL_MAX,
  MITRE_ID_MAX,
  MITRE_NAME_TAIL_MAX,
} from "./constants"

export function buildNodeTooltipLines(
  alertLabel: string,
  fw: AlertFrameworkContext | undefined,
  alertRowId?: string,
): string[] {
  const lines: string[] = [alertLabel]
  if (fw?.killChainPhase) lines.push(`Kill chain: ${fw.killChainPhase}`)
  if (fw?.mitreTechniqueId) {
    const mitre = fw.mitreTechniqueName
      ? `${fw.mitreTechniqueId} — ${fw.mitreTechniqueName}`
      : fw.mitreTechniqueId
    lines.push(`MITRE: ${mitre}`)
  } else if (fw?.mitreTactic) {
    lines.push(`MITRE tactic: ${fw.mitreTactic}`)
  }
  if (alertRowId) lines.push(alertRowId)
  return lines
}

export function nodeTooltipWorthShowing(
  alertLabel: string,
  fw: AlertFrameworkContext | undefined,
): boolean {
  if (isTruncated(alertLabel, ALERT_LABEL_MAX)) return true
  if (fw?.killChainPhase && isTruncated(fw.killChainPhase, KC_LABEL_MAX)) return true
  if (fw?.mitreTechniqueId && isTruncated(fw.mitreTechniqueId, MITRE_ID_MAX)) return true
  if (
    fw?.mitreTechniqueName &&
    isTruncated(fw.mitreTechniqueName, MITRE_NAME_TAIL_MAX)
  ) {
    return true
  }
  return false
}
