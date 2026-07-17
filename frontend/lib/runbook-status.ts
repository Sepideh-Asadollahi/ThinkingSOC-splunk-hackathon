export type RunbookDraftStatusTone = "neutral" | "info" | "success" | "warning" | "danger"

type RunbookDraftStatusInput = {
  status: "DRAFT" | "PARSER_VALID" | "SOURCE_VERIFIED" | "FAILED"
  steps: readonly unknown[]
  source_results: readonly {
    spl_results?: { error?: string | null } | null
  }[]
}

export type RunbookDraftStatusPresentation = {
  label: string
  detail: string
  tone: RunbookDraftStatusTone
}

/** Translate internal trust-gate state into an accurate analyst-facing status. */
export function getRunbookDraftStatusPresentation(
  draft: RunbookDraftStatusInput
): RunbookDraftStatusPresentation {
  if (draft.status === "SOURCE_VERIFIED") {
    return {
      label: "SOURCE VERIFIED",
      detail: "Every step is parser-valid and returned source evidence.",
      tone: "success",
    }
  }
  if (draft.status === "PARSER_VALID") {
    return {
      label: "PARSER VALID",
      detail: "Queries are valid, but source evidence is still missing for one or more steps.",
      tone: "info",
    }
  }
  if (draft.status === "DRAFT") {
    return {
      label: "DRAFT",
      detail: "One or more steps still require valid SPL before source verification.",
      tone: "neutral",
    }
  }

  const executionErrors = draft.source_results.filter(
    (result) => Boolean(result.spl_results?.error)
  ).length
  if (executionErrors > 0) {
    return {
      label: "EXECUTION ERROR",
      detail: `${executionErrors} step${executionErrors === 1 ? "" : "s"} returned a Splunk or transport execution error.`,
      tone: "danger",
    }
  }

  if (draft.source_results.length !== draft.steps.length) {
    return {
      label: "VERIFICATION INCOMPLETE",
      detail: `Verification produced ${draft.source_results.length} of ${draft.steps.length} required step results.`,
      tone: "warning",
    }
  }

  return {
    label: "VERIFICATION INCOMPLETE",
    detail: "The verification pipeline completed without a complete trustworthy result set.",
    tone: "warning",
  }
}
