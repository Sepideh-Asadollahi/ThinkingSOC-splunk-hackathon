import { describe, expect, it } from "vitest"

import {
  adminOrgGapFromStoragePayload,
  collectAdminOrgGapCandidates,
  hasActiveAdminOrgGap,
  mergeAdminOrgGapIntoAnalysis,
  normalizeAdminOrgGap,
  pickActiveAdminOrgGapFromStorageRows,
  pickAdminOrgGap,
} from "./admin-org-gap"

describe("admin-org-gap", () => {
  it("normalizes gap response fields", () => {
    const gap = normalizeAdminOrgGap({
      should_suggest_question: true,
      gap_summary: "Ownership unknown",
      question_for_admin: "Who owns this host?",
      notes: "demo",
    })
    expect(gap?.should_suggest_question).toBe(true)
    expect(gap?.question_for_admin).toContain("Who owns")
    expect(hasActiveAdminOrgGap(gap)).toBe(true)
  })

  it("picks embedded gap from analysis payload", () => {
    const gap = pickAdminOrgGap({
      analysis: {
        admin_org_gap: {
          should_suggest_question: true,
          gap_summary: "gap",
          question_for_admin: "Ask admin?",
        },
      },
    })
    expect(gap?.question_for_admin).toBe("Ask admin?")
  })

  it("picks gap from security_result on route payloads", () => {
    const gap = pickAdminOrgGap({
      security_result: {
        judge: { verdict: "high" },
        admin_org_gap: {
          should_suggest_question: true,
          gap_summary: "Process policy",
          question_for_admin: "Is osk.exe approved on workstations?",
        },
      },
    })
    expect(hasActiveAdminOrgGap(gap)).toBe(true)
    expect(gap?.question_for_admin).toContain("osk.exe")
  })

  it("prefers active gap over inactive embedded", () => {
    const gap = pickAdminOrgGap({
      admin_org_gap: {
        should_suggest_question: false,
        gap_summary: "",
        question_for_admin: "",
      },
      security_result: {
        admin_org_gap: {
          should_suggest_question: true,
          gap_summary: "ok",
          question_for_admin: "Who owns escalation?",
        },
      },
    })
    expect(gap?.question_for_admin).toBe("Who owns escalation?")
  })

  it("reads standalone storage record response", () => {
    const gap = adminOrgGapFromStoragePayload({
      response: {
        should_suggest_question: true,
        gap_summary: "Escalation unclear",
        question_for_admin: "What is the on-call path?",
      },
    })
    expect(hasActiveAdminOrgGap(gap)).toBe(true)
  })

  it("pickActiveAdminOrgGapFromStorageRows prefers active suggest row", () => {
    const gap = pickActiveAdminOrgGapFromStorageRows([
      {
        payload: {
          response: {
            should_suggest_question: false,
            gap_summary: "",
            question_for_admin: "",
          },
        },
      },
      {
        payload: {
          response: {
            should_suggest_question: true,
            gap_summary: "osk",
            question_for_admin: "Is osk.exe allowed?",
          },
        },
      },
    ])
    expect(gap?.question_for_admin).toBe("Is osk.exe allowed?")
  })

  it("mergeAdminOrgGapIntoAnalysis copies active gap onto analysis", () => {
    const merged = mergeAdminOrgGapIntoAnalysis(
      { judge: { verdict: "x" } },
      {
        security_result: {
          admin_org_gap: {
            should_suggest_question: true,
            gap_summary: "g",
            question_for_admin: "Policy?",
          },
        },
      }
    )
    expect(hasActiveAdminOrgGap(normalizeAdminOrgGap(merged?.admin_org_gap))).toBe(true)
  })

  it("collectAdminOrgGapCandidates dedupes shapes", () => {
    const list = collectAdminOrgGapCandidates({
      analysis: { admin_org_gap: { should_suggest_question: true, gap_summary: "a", question_for_admin: "Q1" } },
      admin_org_gap: { should_suggest_question: false, gap_summary: "", question_for_admin: "" },
    })
    expect(list.length).toBe(2)
  })
})
