import { FrameworkSummaryStrip } from "@/components/correlation/explorer/framework-badges"

export function GraphCanvasToolbar({
  killChainPhases,
  mitreTechniques,
  analysisLinksLoading,
  analysisLinksError,
}: {
  killChainPhases: string[]
  mitreTechniques: string[]
  analysisLinksLoading: boolean
  analysisLinksError: string | null
}) {
  return (
    <>
      <FrameworkSummaryStrip
        killChainPhases={killChainPhases}
        mitreTechniques={mitreTechniques}
      />
      {analysisLinksError ? (
        <p className="text-xs text-amber-300/90">
          Analysis links unavailable: {analysisLinksError}
        </p>
      ) : analysisLinksLoading ? (
        <p className="text-xs text-slate-500">Loading analysis links…</p>
      ) : null}
      <p className="text-xs text-slate-500">
        Drag nodes to rearrange · click to inspect · open Analysis in a new tab from each alert
      </p>
    </>
  )
}
