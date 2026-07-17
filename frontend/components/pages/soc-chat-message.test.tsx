import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { SocChatMessageBubble } from "./soc-chat-message"

describe("SocChatMessageBubble", () => {
  it("renders persisted Runbook citations", () => {
    render(
      <SocChatMessageBubble
        role="assistant"
        content="The Autopilot stopped at the human gate."
        citations={[
          {
            doc_id: "verified_runbook_autopilot_session:abc",
            doc_type: "runbook_autopilot",
            search_name: "Suspicious Login",
            summary_line: "Runbook Autopilot — AWAITING HUMAN APPROVAL",
          },
        ]}
      />
    )

    expect(screen.getByText("1 retrieved source")).toBeInTheDocument()
    expect(screen.getByText("runbook autopilot")).toBeInTheDocument()
    expect(screen.getByText(/AWAITING HUMAN APPROVAL/)).toBeInTheDocument()
    expect(screen.getByText("verified_runbook_autopilot_session:abc")).toBeInTheDocument()
  })
})
