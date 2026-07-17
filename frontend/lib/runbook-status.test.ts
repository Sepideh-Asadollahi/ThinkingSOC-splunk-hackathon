import { describe, expect, it } from "vitest"

import { getRunbookDraftStatusPresentation } from "./runbook-status"

describe("getRunbookDraftStatusPresentation", () => {
  it("labels a partial result set as incomplete verification instead of a failure", () => {
    expect(getRunbookDraftStatusPresentation({
      status: "FAILED",
      steps: [{}, {}, {}],
      source_results: [{ spl_results: { error: null } }],
    })).toEqual({
      label: "VERIFICATION INCOMPLETE",
      detail: "Verification produced 1 of 3 required step results.",
      tone: "warning",
    })
  })

  it("reserves the red error state for a real execution error", () => {
    expect(getRunbookDraftStatusPresentation({
      status: "FAILED",
      steps: [{}],
      source_results: [{ spl_results: { error: "Splunk unavailable" } }],
    })).toMatchObject({ label: "EXECUTION ERROR", tone: "danger" })
  })
})
