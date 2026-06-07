import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { AgentCourt, HunterDefenderDebate } from "./hunter-defender-debate"

describe("AgentCourt", () => {
  it("renders hunter left and defender right with judge centered below", () => {
    render(
      <AgentCourt
        defender="Block outbound traffic from the host."
        hunter={{ narrative: "Pivot on src_ip and user over 7 days.", splunk_search_suggestions: [] }}
        judge={{
          verdict: "investigate",
          priority: "high",
          recommended_next_step: "escalate",
          rationale: "Multiple signals align.",
        }}
      />
    )

    expect(screen.getByTestId("agent-court")).toBeInTheDocument()
    expect(screen.getByText("Hunter & defender")).toBeInTheDocument()
    expect(screen.getByText("Hunter")).toBeInTheDocument()
    expect(screen.getByText("Defender")).toBeInTheDocument()
    expect(screen.getByText("Judge")).toBeInTheDocument()
    expect(screen.getByText(/Pivot on src_ip/)).toBeInTheDocument()
    expect(screen.getByText(/Block outbound traffic/)).toBeInTheDocument()
    expect(screen.getByText(/Multiple signals align/)).toBeInTheDocument()

    expect(screen.getByTestId("agent-court").querySelector(".max-w-2xl")).toBeNull()
  })

  it("renders Splunk search suggestions under hunter", () => {
    render(
      <AgentCourt
        defender="Contain host"
        hunter={{
          narrative: "Hunt lateral movement",
          splunk_search_suggestions: [
            'index=wineventlog EventCode=4624 user="admin"',
            "index=firewall dest_port=445",
          ],
        }}
      />
    )

    expect(screen.getByText(/wineventlog/)).toBeInTheDocument()
    expect(screen.getByText(/dest_port=445/)).toBeInTheDocument()
    expect(screen.getByTestId("hunter-spl-search-ideas-section")).toBeInTheDocument()
    expect(screen.getByText("Splunk search ideas")).toBeInTheDocument()
  })

  it("renders judge directly below hunter and defender, then expansion panels", () => {
    render(
      <AgentCourt
        defender="Contain host"
        hunter={{
          narrative: "Hunt lateral movement",
          splunk_search_suggestions: ['search index=* host="x"'],
          mcp_evidence: {
            tools_called: ["splunk_run_query"],
            hunt_queries: [
              {
                query: 'search index=* user="alice" | head 15',
                row_count: 2,
                summary: '[{"host":"web-01"}]',
              },
            ],
            metadata_sourcetypes: [],
            notes: [],
          },
        }}
        judge={{
          verdict: "investigate",
          priority: "high",
          recommended_next_step: "escalate",
          rationale: "Multiple signals align.",
          mcp_evidence: {
            tools_called: ["saia_ask_splunk_question"],
            saia_answers: [
              {
                question: "How to validate this alert in Splunk?",
                answer: "Review failed logins and parent process chain.",
              },
            ],
            verification_queries: [],
            notes: [],
          },
        }}
      />
    )

    const judgeSection = screen.getByTestId("judge-bench-section")
    const expansionSection = screen.getByTestId("hunter-expansion-section")
    expect(
      judgeSection.compareDocumentPosition(expansionSection) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy()
  })

  it("renders Splunk MCP evidence on hunter and judge", () => {
    render(
      <AgentCourt
        defender="Contain host"
        hunter={{
          narrative: "Hunt lateral movement",
          splunk_search_suggestions: [],
          mcp_evidence: {
            tools_called: ["splunk_run_query"],
            hunt_queries: [
              {
                query: 'search index=* user="alice" | head 15',
                row_count: 2,
                summary: '[{"host":"web-01"}]',
              },
            ],
            metadata_sourcetypes: [],
            notes: [],
          },
        }}
        judge={{
          verdict: "investigate",
          priority: "high",
          recommended_next_step: "escalate",
          rationale: "Multiple signals align.",
          mcp_evidence: {
            tools_called: ["saia_ask_splunk_question"],
            saia_answers: [
              {
                question: "How to validate this alert in Splunk?",
                answer: "Review failed logins and parent process chain.",
              },
            ],
            verification_queries: [],
            notes: [],
          },
        }}
      />
    )

    expect(screen.getByTestId("mcp-hunter-evidence")).toBeInTheDocument()
    expect(screen.getByTestId("mcp-hunter-evidence-section").children[1]).toHaveClass(
      "w-full",
      "min-w-0"
    )
    expect(screen.getByTestId("hunter-expansion-section")).toBeInTheDocument()
    expect(screen.getByTestId("mcp-judge-evidence-section").children[1]).toHaveClass(
      "w-full",
      "min-w-0"
    )
    expect(screen.getByTestId("mcp-judge-evidence")).toBeInTheDocument()
    expect(screen.getByText(/How to validate this alert/)).toBeInTheDocument()
    expect(screen.getByText(/Review failed logins/)).toBeInTheDocument()
  })

  it("shows placeholder when only defender has output", () => {
    render(<AgentCourt defender="Isolate the endpoint." hunter={null} />)

    expect(screen.getByText(/Isolate the endpoint/)).toBeInTheDocument()
    expect(screen.getByText("No output from this agent")).toBeInTheDocument()
  })

  it("returns null when all agents are empty", () => {
    const { container } = render(<AgentCourt defender="" hunter={null} judge={null} />)
    expect(container.firstChild).toBeNull()
  })

  it("HunterDefenderDebate alias renders court without judge", () => {
    render(
      <HunterDefenderDebate
        defender="d"
        hunter={{ narrative: "h", splunk_search_suggestions: [] }}
      />
    )
    expect(screen.getByTestId("agent-court")).toBeInTheDocument()
    expect(screen.queryByText("Judge")).not.toBeInTheDocument()
  })
})
