import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { McpMarkdownContent } from "./mcp-markdown-content"
import {
  LITELLM_FALLBACK_ANSWER_PREFIX,
  McpHunterEvidencePanel,
  McpJudgeEvidencePanel,
  parseMcpJudgeEvidence,
  parseSaiaAnswerText,
} from "./mcp-evidence-panel"

describe("parseSaiaAnswerText", () => {
  it("splits LiteLLM fallback banner from markdown body", () => {
    const parsed = parseSaiaAnswerText(
      `${LITELLM_FALLBACK_ANSWER_PREFIX}\n**Decisive Splunk evidence**\n\n| Step | Data source |\n|------|-------------|\n| 1 | Sysmon |`
    )
    expect(parsed.isFallback).toBe(true)
    expect(parsed.fallbackLabel).toMatch(/LiteLLM fallback/i)
    expect(parsed.body).toContain("**Decisive Splunk evidence**")
    expect(parsed.body).not.toContain(LITELLM_FALLBACK_ANSWER_PREFIX)
  })

  it("returns plain body when no fallback prefix", () => {
    const parsed = parseSaiaAnswerText("Review auth logs on the host.")
    expect(parsed.isFallback).toBe(false)
    expect(parsed.body).toBe("Review auth logs on the host.")
  })
})

describe("McpMarkdownContent", () => {
  it("renders markdown emphasis and tables", () => {
    render(
      <McpMarkdownContent
        content={
          "**Decisive Splunk evidence**\n\n| Step | Source |\n| --- | --- |\n| 1 | Sysmon |"
        }
      />
    )
    expect(screen.getByTestId("mcp-markdown-content")).toBeInTheDocument()
    expect(screen.getByText("Decisive Splunk evidence")).toBeInTheDocument()
    expect(screen.getByRole("table")).toBeInTheDocument()
    expect(screen.getByText("Sysmon")).toBeInTheDocument()
  })

  it("renders compact markdown without block elements for graph and button previews", () => {
    render(<McpMarkdownContent content="**Generating command** with `search`" compact />)

    const root = screen.getByTestId("mcp-markdown-content")
    expect(root.tagName).toBe("SPAN")
    expect(root.querySelector("p, div")).toBeNull()
    expect(screen.getByText("Generating command").tagName).toBe("STRONG")
  })
})

describe("McpEvidencePanel", () => {
  it("renders hunter hunt queries", () => {
    render(
      <McpHunterEvidencePanel
        evidence={{
          tools_called: ["splunk_run_query"],
          hunt_queries: [
            {
              query: 'search index=* host="web-01" | head 15',
              row_count: 3,
              summary: '[{"user":"alice"}]',
            },
          ],
          metadata_sourcetypes: ["WinEventLog:Security"],
          notes: [],
        }}
      />
    )

    expect(screen.getByTestId("mcp-hunter-evidence")).toBeInTheDocument()
    expect(screen.getByText(/host="web-01"/)).toBeInTheDocument()
    expect(screen.getByText("WinEventLog:Security")).toBeInTheDocument()
  })

  it("renders judge SAIA fallback answer as markdown with badge", () => {
    render(
      <McpJudgeEvidencePanel
        evidence={{
          tools_called: ["litellm_saia_fallback"],
          saia_answers: [
            {
              question: "What searches confirm true positive vs benign?",
              answer: `${LITELLM_FALLBACK_ANSWER_PREFIX}\n**Decisive Splunk evidence**\n\nCheck Sysmon EventCode=1.`,
            },
          ],
          verification_queries: [],
          notes: [],
        }}
      />
    )

    expect(screen.getByTestId("mcp-judge-evidence")).toBeInTheDocument()
    expect(screen.getByTestId("mcp-saia-fallback-badge-0")).toBeInTheDocument()
    expect(screen.getByText("LiteLLM fallback answer")).toBeInTheDocument()
    expect(screen.getByText("Decisive Splunk evidence")).toBeInTheDocument()
    expect(screen.queryByText(LITELLM_FALLBACK_ANSWER_PREFIX)).not.toBeInTheDocument()
  })

  it("parseMcpJudgeEvidence returns null for empty payload", () => {
    expect(parseMcpJudgeEvidence({ tools_called: [] })).toBeNull()
  })
})
