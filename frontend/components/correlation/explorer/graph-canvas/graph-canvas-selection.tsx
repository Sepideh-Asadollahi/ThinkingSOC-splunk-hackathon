import { AlertAnalysisLink } from "@/components/correlation/explorer/alert-analysis-link"
import type { AlertDisplayInfo } from "@/lib/api/graph/alert-display"
import type { AlertFrameworkContext } from "@/lib/api/graph/attack-framework"
import type { GraphNode } from "@/lib/api/graph/types"

type GraphCanvasSelectionProps = {
  selected: GraphNode
  display?: AlertDisplayInfo
  framework?: AlertFrameworkContext
}

export function GraphCanvasSelection({
  selected,
  display,
  framework,
}: GraphCanvasSelectionProps) {
  return (
    <div className="space-y-1 text-xs text-slate-400">
      <p>
        Selected:{" "}
        <span className="text-white">{display?.displayName ?? selected.label}</span>
        <AlertAnalysisLink info={display} className="ml-2" />
        {selected.properties?.alert_row_id ? (
          <span className="text-slate-500">
            {" "}
            · {String(selected.properties.alert_row_id)}
          </span>
        ) : null}
      </p>
      {framework ? (
        <p className="text-slate-500">
          {framework.killChainPhase ? (
            <span className="text-amber-300/90">
              Kill chain: {framework.killChainPhase}
              {" · "}
            </span>
          ) : null}
          {framework.mitreTechniqueId ? (
            <span className="text-violet-300/90">
              MITRE {framework.mitreTechniqueId}
              {framework.mitreTechniqueName
                ? ` (${framework.mitreTechniqueName})`
                : ""}
            </span>
          ) : null}
        </p>
      ) : null}
    </div>
  )
}
