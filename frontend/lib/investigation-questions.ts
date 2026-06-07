export type SplSearchResult = {
  row_count?: number
  rows?: Record<string, unknown>[]
  truncated?: boolean
  error?: string | null
}

export type SplSaiaAnalysis = {
  explanation?: string
  optimized?: boolean
  spl_before_optimize?: string | null
  steps?: string[]
  unavailable_reason?: string | null
}

export type SplResultsAnalysis = {
  summary?: string
  findings?: string[]
  key_observations?: string[]
  answer?: string
  confidence?: string
  usefulness?: string
  recommended_next_step?: string
  investigation_answer?: string
  result_analysis?: SplResultsAnalysis
  [key: string]: unknown
}

export type SplResultsAnalysisBody = {
  text: string
  findings: string[]
  confidence?: string
  usefulness?: string
  recommendedNextStep?: string
}

function parseMaybeJsonRecord(raw: unknown): Record<string, unknown> | null {
  if (raw && typeof raw === "object" && !Array.isArray(raw)) {
    return raw as Record<string, unknown>
  }
  if (typeof raw === "string") {
    const trimmed = raw.trim()
    if (!trimmed) return null
    try {
      const parsed = JSON.parse(trimmed) as unknown
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        return parsed as Record<string, unknown>
      }
    } catch {
      return null
    }
  }
  return null
}

function parseStringList(raw: unknown): string[] | undefined {
  if (!Array.isArray(raw)) return undefined
  const items = raw.map((x) => String(x)).filter(Boolean)
  return items.length > 0 ? items : undefined
}

export function parseSplSaiaAnalysis(raw: unknown): SplSaiaAnalysis | null {
  const row = parseMaybeJsonRecord(raw)
  if (!row) return null
  const explanation =
    typeof row.explanation === "string"
      ? row.explanation
      : typeof row.answer === "string"
        ? row.answer
        : typeof row.text === "string"
          ? row.text
          : undefined
  const steps = parseStringList(row.steps)
  const unavailable =
    typeof row.unavailable_reason === "string" ? row.unavailable_reason : undefined
  if (!explanation && !unavailable && !steps?.length) return null
  return {
    explanation,
    optimized: row.optimized === true,
    spl_before_optimize:
      typeof row.spl_before_optimize === "string" ? row.spl_before_optimize : null,
    steps,
    unavailable_reason: unavailable,
  }
}

export function parseSplResultsAnalysis(raw: unknown): SplResultsAnalysis | null {
  const row = parseMaybeJsonRecord(raw)
  if (!row) return null
  const nested =
    row.result_analysis && typeof row.result_analysis === "object"
      ? (row.result_analysis as SplResultsAnalysis)
      : null
  const source = nested ?? (row as SplResultsAnalysis)
  const findings = parseStringList(source.findings) ?? parseStringList(source.key_observations)
  const summary = typeof source.summary === "string" ? source.summary : undefined
  const answer = typeof source.answer === "string" ? source.answer : undefined
  const investigationAnswer =
    typeof source.investigation_answer === "string" ? source.investigation_answer : undefined
  const recommendedNextStep =
    typeof source.recommended_next_step === "string" ? source.recommended_next_step : undefined
  const confidence = typeof source.confidence === "string" ? source.confidence : undefined
  const usefulness = typeof source.usefulness === "string" ? source.usefulness : undefined
  if (
    !summary &&
    !answer &&
    !investigationAnswer &&
    !findings?.length &&
    !recommendedNextStep
  ) {
    return null
  }
  return {
    summary,
    answer,
    investigation_answer: investigationAnswer,
    findings,
    key_observations: parseStringList(source.key_observations),
    confidence,
    usefulness,
    recommended_next_step: recommendedNextStep,
    result_analysis: nested ?? undefined,
  }
}

/** Normalize LLM / API shapes for spl_results_analysis display. */
export function pickSplResultsAnalysisBody(
  raw: SplResultsAnalysis | null | undefined
): SplResultsAnalysisBody {
  const parsed = parseSplResultsAnalysis(raw) ?? raw
  if (!parsed) return { text: "", findings: [] }
  const nested =
    parsed.result_analysis && typeof parsed.result_analysis === "object"
      ? parsed.result_analysis
      : null
  const source = nested ?? parsed
  const text = [
    typeof source.summary === "string" ? source.summary.trim() : "",
    typeof source.answer === "string" ? source.answer.trim() : "",
    typeof source.investigation_answer === "string" ? source.investigation_answer.trim() : "",
  ].find(Boolean) ?? ""
  const findings =
    parseStringList(source.findings) ??
    parseStringList(source.key_observations) ??
    []
  const confidence =
    typeof source.confidence === "string" ? source.confidence : undefined
  const usefulness =
    typeof source.usefulness === "string" ? source.usefulness : undefined
  const recommendedNextStep =
    typeof source.recommended_next_step === "string"
      ? source.recommended_next_step.trim()
      : undefined
  return { text, findings, confidence, usefulness, recommendedNextStep }
}

export type InvestigationQuestionItem = {
  question: string
  spl: string
  explanation?: string
  time_window?: string
  pivots?: string[]
  notes?: string[]
  validation?: {
    method?: string
    valid?: boolean | null
    message?: string | null
  }
  spl_results?: SplSearchResult | null
  spl_saia_analysis?: SplSaiaAnalysis | null
  spl_results_analysis?: SplResultsAnalysis | null
}

export function pickInvestigationQuestionsRaw(data: Record<string, unknown>): unknown {
  if (Array.isArray(data.investigation_questions)) {
    return data.investigation_questions
  }
  const output = parseMaybeJsonRecord(data.investigation_questions_output)
  if (output && Array.isArray(output.investigation_questions)) {
    return output.investigation_questions
  }
  return data.investigation_questions
}

export function normalizeInvestigationQuestions(
  raw: unknown,
  legacyRootSpl?: Record<string, unknown> | null
): InvestigationQuestionItem[] {
  const out: InvestigationQuestionItem[] = []

  if (Array.isArray(raw)) {
    for (const entry of raw) {
      if (typeof entry === "string" && entry.trim()) {
        out.push({ question: entry.trim(), spl: legacyRootSpl?.spl ? String(legacyRootSpl.spl) : "" })
        continue
      }
      const row = parseMaybeJsonRecord(entry)
      if (!row) continue
      const question = String(row.question ?? row.text ?? "").trim()
      const spl = String(row.spl ?? row.query ?? "").trim()
      if (!question) continue
      const splResults = parseMaybeJsonRecord(row.spl_results)
      out.push({
        question,
        spl: spl || (legacyRootSpl?.spl ? String(legacyRootSpl.spl) : ""),
        explanation: row.explanation ? String(row.explanation) : undefined,
        time_window: row.time_window ? String(row.time_window) : undefined,
        pivots: parseStringList(row.pivots),
        notes: parseStringList(row.notes),
        validation:
          row.validation && typeof row.validation === "object"
            ? (row.validation as InvestigationQuestionItem["validation"])
            : undefined,
        spl_results: splResults ? (splResults as SplSearchResult) : undefined,
        spl_saia_analysis: parseSplSaiaAnalysis(row.spl_saia_analysis),
        spl_results_analysis: parseSplResultsAnalysis(row.spl_results_analysis),
      })
    }
  }

  if (out.length === 0 && legacyRootSpl && typeof legacyRootSpl.spl === "string" && legacyRootSpl.spl) {
    out.push({
      question: "Run root-cause SPL for this alert context.",
      spl: legacyRootSpl.spl,
      explanation: legacyRootSpl.explanation ? String(legacyRootSpl.explanation) : undefined,
      time_window: legacyRootSpl.time_window ? String(legacyRootSpl.time_window) : undefined,
      spl_saia_analysis: parseSplSaiaAnalysis(legacyRootSpl.spl_saia_analysis),
      spl_results_analysis: parseSplResultsAnalysis(legacyRootSpl.spl_results_analysis),
    })
  }

  return out.filter((item) => item.question && item.spl)
}
