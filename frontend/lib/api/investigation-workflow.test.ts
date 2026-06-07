import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import {
  fetchAnalystActions,
  fetchInvestigationTimeline,
  postAnalystAction,
} from "@/lib/api/investigation-workflow"

const backendFetch = vi.fn()

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status = 500) {
      super(message)
      this.status = status
    }
  },
  backendFetch: (...args: unknown[]) => backendFetch(...args),
}))

describe("investigation-workflow API", () => {
  beforeEach(() => {
    backendFetch.mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it("fetchInvestigationTimeline calls correct path", async () => {
    backendFetch.mockResolvedValueOnce({
      record_id: 10,
      found: true,
      sid: "sid-1",
      steps: [],
    })
    const data = await fetchInvestigationTimeline(10)
    expect(backendFetch).toHaveBeenCalledWith("/investigation/records/10/timeline")
    expect(data.sid).toBe("sid-1")
  })

  it("fetchAnalystActions calls correct path", async () => {
    backendFetch.mockResolvedValueOnce({
      record_id: 5,
      count: 0,
      results: [],
    })
    await fetchAnalystActions("5")
    expect(backendFetch).toHaveBeenCalledWith("/investigation/records/5/analyst-actions")
  })

  it("postAnalystAction sends JSON body", async () => {
    backendFetch.mockResolvedValueOnce({
      record_id: 5,
      saved: { ok: true },
      latest: { action: "acknowledge" },
      results: [{ action: "acknowledge" }],
    })
    const res = await postAnalystAction(5, { action: "acknowledge", note: "LGTM" })
    expect(backendFetch).toHaveBeenCalledWith(
      "/investigation/records/5/analyst-actions",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ action: "acknowledge", note: "LGTM" }),
      })
    )
    expect(res.latest?.action).toBe("acknowledge")
  })

  it("postAnalystAction supports escalate", async () => {
    backendFetch.mockResolvedValueOnce({
      record_id: 7,
      saved: { ok: true },
      latest: { action: "escalate" },
      results: [],
    })
    await postAnalystAction("7", { action: "escalate" })
    const call = backendFetch.mock.calls[0]
    expect(call[1]).toMatchObject({ method: "POST" })
    expect(JSON.parse(String(call[1]?.body))).toEqual({ action: "escalate" })
  })
})
