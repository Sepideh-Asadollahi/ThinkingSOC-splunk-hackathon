import { describe, expect, it, vi, beforeEach, afterEach } from "vitest"

import type { InvestigationWorkflowExport } from "@/lib/api/investigation-workflow"
import { fetchInvestigationWorkflowForExport } from "@/lib/api/investigation-workflow"
import {
  OPS_INVESTIGATION_SECTION_KEYS,
  SECURITY_INVESTIGATION_SECTION_KEYS,
  buildInvestigationExport,
  buildOpsInvestigationSections,
  buildSecurityInvestigationSections,
  downloadInvestigationExport,
  investigationExportFilename,
} from "./investigation-export"
import type { StoredEventRecord } from "@/lib/api/types"

vi.mock("@/lib/api/investigation-workflow", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/investigation-workflow")>()
  return {
    ...actual,
    fetchInvestigationWorkflowForExport: vi.fn(),
  }
})

const mockFetchWorkflow = vi.mocked(fetchInvestigationWorkflowForExport)

const sampleWorkflow: InvestigationWorkflowExport = {
  event_timeline: {
    record_id: 42,
    found: true,
    sid: "scheduler_123",
    search_name: "Suspicious login",
    row_index: 0,
    steps: [
      {
        record_id: 10,
        record_type: "splunk_ingest",
        title: "Ingest",
        description: "Alert indexed",
        detail: null,
        created_at: "2026-05-22T09:00:00Z",
        is_current_record: false,
        is_analyst_action: false,
      },
    ],
  },
  analyst_actions: {
    record_id: 42,
    count: 1,
    results: [
      {
        id: 1,
        created_at: "2026-05-22T11:00:00Z",
        action: "acknowledge",
        note: "Reviewing",
        recommended_step: null,
        investigation_record_id: 42,
      },
    ],
  },
  verified_runbook: {
    record_id: 42,
    draft: null,
    latest_approval: null,
    latest_run: null,
    latest_response_preview: null,
    latest_response_decision: null,
  },
  fetch_errors: [],
}

const securityFullEvent: StoredEventRecord = {
  id: 42,
  sid: "scheduler_123",
  search_name: "Suspicious login",
  created_at: "2026-05-22T10:00:00Z",
  tsoc_record_type: "soc_analysis",
  payload: {
    classification: { track: "security", recommended_pipeline: "security" },
    triage: { review_verdict: "investigate", investigation_priority: "high" },
    raw_alert: { user: "alice" },
    analysis_input: { sid: "scheduler_123" },
    analysis_output: { status: "ok" },
    security_result: {
      summary: "Possible credential abuse",
      judge: {
        verdict: "needs_investigation",
        priority: "high",
        recommended_next_step: "Isolate host",
        rationale: "Critical asset",
      },
      hunter: { narrative: "Hunt lateral movement", splunk_search_suggestions: ["index=wineventlog"] },
      defender: "Contain host",
      triage: {
        review_verdict: "NEEDS_HUMAN_REVIEW",
        report: { recommended_action: "Escalate" },
      },
      enrichment: { confidence: "high", resolved_user_id: "u1" },
      investigation_questions: [
        {
          question: "Who logged in?",
          spl: "index=wineventlog earliest=-24h | stats count",
        },
      ],
      framework_mapping: [{ framework: "MITRE", technique_id: "T1078" }],
      threat_intel: { status: "completed", findings: [] },
      admin_org_gap: {
        should_suggest_question: true,
        gap_summary: "Ownership unknown",
        question_for_admin: "Who owns this host?",
      },
    },
  },
}

const opsFullEvent: StoredEventRecord = {
  id: 7,
  sid: "ops_sid",
  search_name: "High CPU",
  tsoc_record_type: "observability_analysis",
  payload: {
    classification: { track: "observability" },
    raw_alert: { host: "web-01" },
    analysis: {
      track: "observability",
      summary: "CPU spike",
      ops_judge: { verdict: "degraded", priority: "high" },
      entity_resolution: { resolved_host: "web-01", confidence: "high" },
      impact_context: { impact_level: "high" },
      diagnoser: {
        root_cause_hypotheses: [{ hypothesis: "Saturation", confidence: "medium" }],
        followup_searches: ["index=metrics | timechart avg(cpu)"],
      },
      responder: {
        recommended_actions: ["Scale pods"],
        safety_notes: ["Confirm with SRE"],
      },
      evidence_refs: ["cpu-chart-1"],
    },
  },
}

describe("investigation-export", () => {
  it("exports every Security investigation tab when data exists", () => {
    const bundle = buildInvestigationExport(securityFullEvent, "security")

    expect(bundle.sections_included).toContain("overview")
    expect(bundle.sections_included).toContain("recommended-action")
    expect(bundle.sections_included).toContain("triage")
    expect(bundle.sections_included).toContain("agents")
    expect(bundle.sections_included).toContain("enrichment")
    expect(bundle.sections_included).toContain("questions")
    expect(bundle.sections_included).toContain("threat-intel")
    expect(bundle.sections_included).toContain("framework")
    expect(bundle.sections_included).toContain("admin-question")
    expect(bundle.sections_included).toContain("technical")

    expect(bundle.sections_included.length).toBe(SECURITY_INVESTIGATION_SECTION_KEYS.length)
    for (const key of bundle.sections_included) {
      expect(SECURITY_INVESTIGATION_SECTION_KEYS).toContain(key)
      expect(bundle.sections[key]).toBeDefined()
    }

    expect(bundle.sections.agents).toMatchObject({
      defender: "Contain host",
    })
    expect(bundle.sections.technical).toMatchObject({
      raw_alert: { user: "alice" },
    })
    expect(bundle.analysis?.summary).toBe("Possible credential abuse")
    expect(bundle.payload.security_result).toBeDefined()
    expect(bundle.investigation_workflow).toBeNull()
  })

  it("includes analyst gate and event timeline in overview when workflow is provided", () => {
    const bundle = buildInvestigationExport(securityFullEvent, "security", sampleWorkflow)

    expect(bundle.investigation_workflow).toEqual(sampleWorkflow)
    const overview = bundle.sections.overview as Record<string, unknown>
    expect(overview.analyst_gate).toMatchObject({
      count: 1,
      latest: expect.objectContaining({ action: "acknowledge" }),
    })
    expect(overview.event_timeline).toMatchObject({
      sid: "scheduler_123",
      step_count: 1,
      steps: expect.arrayContaining([expect.objectContaining({ title: "Ingest" })]),
    })
    const keys = Object.keys(overview)
    expect(keys[0]).toBe("analyst_gate")
    expect(keys[1]).toBe("event_timeline")
  })

  it("does not attach workflow data for observability exports", () => {
    const bundle = buildInvestigationExport(opsFullEvent, "observability", sampleWorkflow)
    expect(bundle.investigation_workflow).toBeNull()
    const overview = bundle.sections.overview as Record<string, unknown>
    expect(overview.analyst_gate).toBeUndefined()
    expect(overview.event_timeline).toBeUndefined()
  })

  it("exports every Observability investigation tab when data exists", () => {
    const bundle = buildInvestigationExport(opsFullEvent, "observability")

    for (const key of OPS_INVESTIGATION_SECTION_KEYS) {
      expect(bundle.sections_included).toContain(key)
      expect(bundle.sections[key]).toBeDefined()
    }

    expect(bundle.sections.entity).toMatchObject({ resolved_host: "web-01" })
    expect(bundle.sections.diagnoser).toMatchObject({
      followup_searches: ["index=metrics | timechart avg(cpu)"],
    })
    expect((bundle.sections.technical as Record<string, unknown>).raw_alert).toEqual({ host: "web-01" })
  })

  it("omits Security tabs that have no UI content", () => {
    const minimal: StoredEventRecord = {
      id: 1,
      payload: {
        security_result: { summary: "Only summary" },
      },
    }
    const bundle = buildInvestigationExport(minimal, "security")
    expect(bundle.sections_included).toEqual(["overview"])
    expect(bundle.sections.overview).toMatchObject({ summary: "Only summary" })
    expect(bundle.sections_included).not.toContain("agents")
    expect(bundle.sections_included).not.toContain("technical")
  })

  it("buildSecurityInvestigationSections mirrors UI tab gating", () => {
    const bundle = buildInvestigationExport(securityFullEvent, "security")
    const rebuilt = buildSecurityInvestigationSections(bundle)
    expect(rebuilt.sections_included).toEqual(bundle.sections_included)
    expect(Object.keys(rebuilt.sections).sort()).toEqual(Object.keys(bundle.sections).sort())
  })

  it("buildOpsInvestigationSections mirrors UI tab gating", () => {
    const bundle = buildInvestigationExport(opsFullEvent, "observability")
    const rebuilt = buildOpsInvestigationSections(bundle)
    expect(rebuilt.sections_included).toEqual(bundle.sections_included)
  })

  it("generates safe filenames", () => {
    expect(investigationExportFilename(securityFullEvent, "security")).toMatch(
      /^investigation-scheduler_123-42-\d{4}-\d{2}-\d{2}\.json$/
    )
    expect(investigationExportFilename(opsFullEvent, "observability")).toMatch(
      /^ops-investigation-ops_sid-7-\d{4}-\d{2}-\d{2}\.json$/
    )
  })

  describe("downloadInvestigationExport", () => {
    let createObjectURL: ReturnType<typeof vi.fn>
    let revokeObjectURL: ReturnType<typeof vi.fn>
    let click: ReturnType<typeof vi.fn>
    let anchor: { click: ReturnType<typeof vi.fn>; download: string; href: string; rel: string }

    beforeEach(() => {
      createObjectURL = vi.fn(() => "blob:mock")
      revokeObjectURL = vi.fn()
      click = vi.fn()
      anchor = { click, download: "", href: "", rel: "" }
      vi.stubGlobal("URL", {
        createObjectURL,
        revokeObjectURL,
      })
      const nativeCreateElement = document.createElement.bind(document)
      vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
        if (tag === "a") return anchor as unknown as HTMLAnchorElement
        return nativeCreateElement(tag)
      })
      vi.spyOn(document.body, "appendChild").mockImplementation(() => null as unknown as Node)
      vi.spyOn(document.body, "removeChild").mockImplementation(() => null as unknown as Node)
    })

    afterEach(() => {
      vi.unstubAllGlobals()
      vi.restoreAllMocks()
    })

    it("creates a JSON download with workflow fetched for security", async () => {
      mockFetchWorkflow.mockResolvedValueOnce(sampleWorkflow)

      await downloadInvestigationExport(securityFullEvent, "security")

      expect(mockFetchWorkflow).toHaveBeenCalledWith(42)
      expect(createObjectURL).toHaveBeenCalled()
      const blobArg = createObjectURL.mock.calls[0]?.[0] as Blob
      expect(blobArg).toBeInstanceOf(Blob)
      expect(click).toHaveBeenCalled()
      expect(revokeObjectURL).toHaveBeenCalledWith("blob:mock")
      expect(anchor.download).toMatch(/^investigation-/)
    })

    it("skips workflow fetch for observability", async () => {
      mockFetchWorkflow.mockClear()
      await downloadInvestigationExport(opsFullEvent, "observability")
      expect(mockFetchWorkflow).not.toHaveBeenCalled()
      expect(createObjectURL).toHaveBeenCalled()
    })
  })
})
