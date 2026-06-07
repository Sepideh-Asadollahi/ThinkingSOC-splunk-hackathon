"use client"

import { useState } from "react"
import { DownloadIcon, Loader2Icon } from "lucide-react"

import { NeonActionButton, type NeonAccent } from "@/components/neon-glass"
import {
  downloadInvestigationExport,
  type InvestigationExportTrack,
} from "@/lib/investigation-export"
import type { StoredEventRecord } from "@/lib/api/types"

export function InvestigationExportButton({
  event,
  track,
  accent,
  disabled,
}: {
  event: StoredEventRecord | null
  track: InvestigationExportTrack
  accent: NeonAccent
  disabled?: boolean
}) {
  const [exporting, setExporting] = useState(false)

  return (
    <NeonActionButton
      accent={accent}
      type="button"
      disabled={disabled || !event || exporting}
      title="Download investigation as JSON (includes timeline and analyst gate for Security)"
      aria-label="Export investigation"
      data-testid="investigation-export-button"
      onClick={() => {
        if (!event || exporting) return
        setExporting(true)
        void downloadInvestigationExport(event, track).finally(() => setExporting(false))
      }}
    >
      {exporting ? (
        <Loader2Icon className="size-4 animate-spin" aria-hidden />
      ) : (
        <DownloadIcon className="size-4" aria-hidden />
      )}
      {exporting ? "Exporting…" : "Export"}
    </NeonActionButton>
  )
}
