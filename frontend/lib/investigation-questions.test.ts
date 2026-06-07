import { describe, expect, it } from "vitest"

import {
  normalizeInvestigationQuestions,
  parseSplResultsAnalysis,
  parseSplSaiaAnalysis,
  pickInvestigationQuestionsRaw,
  pickSplResultsAnalysisBody,
} from "./investigation-questions"

describe("normalizeInvestigationQuestions", () => {
  it("merges legacy string questions with root_cause_spl", () => {
    const items = normalizeInvestigationQuestions(
      ["What is the parent process?"],
      { spl: "index=* earliest=-1h | head 10", explanation: "baseline" }
    )
    expect(items).toHaveLength(1)
    expect(items[0]?.question).toContain("parent process")
    expect(items[0]?.spl).toContain("index=*")
  })

  it("parses unified question+SPL objects", () => {
    const items = normalizeInvestigationQuestions([
      {
        question: "Check auth for user?",
        spl: "index=wineventlog user=admin earliest=-24h",
        explanation: "auth timeline",
      },
    ])
    expect(items[0]?.spl).toContain("wineventlog")
  })

  it("parses spl_saia_analysis and spl_results_analysis", () => {
    const items = normalizeInvestigationQuestions([
      {
        question: "Q?",
        spl: "search index=main",
        spl_saia_analysis: {
          explanation: "Counts failed logins.",
          optimized: true,
          steps: ["optimize", "explain"],
        },
        spl_results_analysis: { summary: "No rows returned.", confidence: "medium" },
      },
    ])
    expect(items[0]?.spl_saia_analysis?.explanation).toContain("failed logins")
    expect(items[0]?.spl_saia_analysis?.optimized).toBe(true)
    expect(items[0]?.spl_results_analysis?.summary).toContain("No rows")
  })

  it("parses JSON-string spl_saia_analysis and nested result_analysis", () => {
    const items = normalizeInvestigationQuestions([
      {
        question: "Q?",
        spl: "search index=main",
        spl_saia_analysis: JSON.stringify({
          explanation: "**Bold SAIA** guidance",
        }),
        spl_results_analysis: {
          result_analysis: {
            summary: "Nested summary",
            key_observations: ["obs 1", "obs 2"],
            recommended_next_step: "Pivot on host",
            usefulness: "high",
            confidence: "medium",
          },
        },
      },
    ])
    expect(items[0]?.spl_saia_analysis?.explanation).toContain("Bold SAIA")
    const body = pickSplResultsAnalysisBody(items[0]?.spl_results_analysis)
    expect(body.text).toContain("Nested summary")
    expect(body.findings).toEqual(["obs 1", "obs 2"])
    expect(body.recommendedNextStep).toBe("Pivot on host")
    expect(body.usefulness).toBe("high")
  })

  it("pickInvestigationQuestionsRaw reads graph output wrapper", () => {
    const raw = pickInvestigationQuestionsRaw({
      investigation_questions_output: {
        investigation_questions: [{ question: "Who logged in?", spl: "index=main" }],
      },
    })
    expect(Array.isArray(raw)).toBe(true)
    expect((raw as { question: string }[])[0]?.question).toContain("logged in")
  })

  it("pickSplResultsAnalysisBody reads nested result_analysis", () => {
    const body = pickSplResultsAnalysisBody({
      result_analysis: { summary: "Nested summary", findings: ["a"], confidence: "high" },
    })
    expect(body.text).toContain("Nested summary")
    expect(body.findings).toEqual(["a"])
    expect(body.confidence).toBe("high")
  })

  it("parseSplResultsAnalysis reads flat backend shape", () => {
    const parsed = parseSplResultsAnalysis({
      summary: "Batch summary",
      key_observations: ["a"],
      recommended_next_step: "Review host",
      usefulness: "medium",
    })
    expect(parsed?.summary).toBe("Batch summary")
    expect(parsed?.key_observations).toEqual(["a"])
  })

  it("parseSplSaiaAnalysis reads answer alias", () => {
    const parsed = parseSplSaiaAnalysis({ answer: "Explain SPL pivots" })
    expect(parsed?.explanation).toBe("Explain SPL pivots")
  })
})
