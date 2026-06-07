"use client"

import { useCallback, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { RadarIcon } from "lucide-react"

import { OperationStatusViewer } from "@/components/correlation/operation-status-viewer"
import {
  Dialog,
  NeonActionButton,
  NeonAlert,
  NeonAlertDescription,
  NeonDialogContent,
  NeonDialogFooter,
  NeonDialogFooterButton,
  NeonDialogHeaderWithIcon,
  NeonField,
  NeonFieldGroup,
  NeonFieldLabel,
  NeonInput,
} from "@/components/neon-glass"
import {
  getOperationStatus,
  initiateAttackDiscovery,
} from "@/lib/api/graph/graphAnalysis"
import type { OperationStatusResponse } from "@/lib/api/graph/types"

type Phase = "form" | "running" | "done"

async function pollOperation(
  opId: string,
  onUpdate: (status: OperationStatusResponse) => void,
): Promise<OperationStatusResponse> {
  let last: OperationStatusResponse | null = null
  for (let i = 0; i < 60; i++) {
    const st = await getOperationStatus(opId)
    last = st
    onUpdate(st)
    if (st.status === "completed" || st.status === "failed") break
    await new Promise((r) => setTimeout(r, 2000))
  }
  return last!
}

export function AttackDiscoveryModal({
  open,
  onOpenChange,
  onComplete,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onComplete: () => void
}) {
  const router = useRouter()
  const [phase, setPhase] = useState<Phase>("form")
  const [lastNAlerts, setLastNAlerts] = useState("50")
  const [status, setStatus] = useState<OperationStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const reset = useCallback(() => {
    setPhase("form")
    setStatus(null)
    setError(null)
    setSubmitting(false)
  }, [])

  const handleOpenChange = (next: boolean) => {
    if (!next) reset()
    onOpenChange(next)
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    setError(null)
    setPhase("running")
    try {
      const limit = Math.min(500, Math.max(1, Number(lastNAlerts) || 50))
      const { operation_id } = await initiateAttackDiscovery({
        analysis_types: ["smart"],
        limit_to_latest_alerts: limit,
        force_reanalysis: true,
      })
      const final = await pollOperation(operation_id, setStatus)
      setPhase("done")
      if (final.status === "completed") {
        onComplete()
      } else if (final.status === "failed") {
        setError(final.message || "Analysis failed")
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setPhase("form")
    } finally {
      setSubmitting(false)
    }
  }

  const firstFindingId = status?.result_payload?.finding_ids?.[0]

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <NeonDialogContent className="max-w-lg">
        <NeonDialogHeaderWithIcon
          icon={<RadarIcon className="size-5 text-teal-400" />}
          title="Attack Discovery"
          description="Run Smart Analysis to correlate alerts and create new findings."
        />

        {phase === "form" ? (
          <NeonFieldGroup className="py-2">
            <NeonField>
              <NeonFieldLabel>Analysis type</NeonFieldLabel>
              <p className="text-sm text-slate-300">Smart Analysis (recommended)</p>
            </NeonField>
            <NeonField>
              <NeonFieldLabel htmlFor="last-n-alerts">Latest alerts to scan</NeonFieldLabel>
              <NeonInput
                id="last-n-alerts"
                type="number"
                min={1}
                max={500}
                value={lastNAlerts}
                onChange={(e) => setLastNAlerts(e.target.value)}
              />
            </NeonField>
          </NeonFieldGroup>
        ) : (
          <OperationStatusViewer status={status} />
        )}

        {error ? (
          <NeonAlert variant="destructive" className="mt-3">
            <NeonAlertDescription>{error}</NeonAlertDescription>
          </NeonAlert>
        ) : null}

        {phase === "done" && status?.status === "completed" ? (
          <NeonAlert className="mt-3">
            <NeonAlertDescription>
              Created {status.result_payload?.findings_created ?? 0} finding(s).
              Refresh the list to see updates.
            </NeonAlertDescription>
          </NeonAlert>
        ) : null}

        <NeonDialogFooter>
          {phase === "form" ? (
            <>
              <NeonDialogFooterButton
                footerVariant="secondary"
                onClick={() => handleOpenChange(false)}
              >
                Cancel
              </NeonDialogFooterButton>
              <NeonActionButton
                accent="teal"
                onClick={handleSubmit}
                disabled={submitting}
              >
                Start Smart Analysis
              </NeonActionButton>
            </>
          ) : phase === "running" ? (
            <NeonDialogFooterButton footerVariant="secondary" disabled>
              Running…
            </NeonDialogFooterButton>
          ) : (
            <>
              <NeonDialogFooterButton
                footerVariant="secondary"
                onClick={() => handleOpenChange(false)}
              >
                Close
              </NeonDialogFooterButton>
              {firstFindingId ? (
                <NeonActionButton
                  accent="teal"
                  onClick={() => {
                    handleOpenChange(false)
                    router.push(
                      `/correlation/explorer?finding_id=${firstFindingId}&identifier=${firstFindingId}`,
                    )
                  }}
                >
                  View finding
                </NeonActionButton>
              ) : (
                <Link href="/correlation" onClick={() => handleOpenChange(false)}>
                  <NeonActionButton accent="teal">Back to list</NeonActionButton>
                </Link>
              )}
            </>
          )}
        </NeonDialogFooter>
      </NeonDialogContent>
    </Dialog>
  )
}
