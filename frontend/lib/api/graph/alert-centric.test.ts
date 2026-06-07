import { describe, expect, it } from "vitest"

import { dedupeCausedEdges } from "@/lib/api/graph/alert-centric"
import type { GraphEdge } from "@/lib/api/graph/types"

describe("dedupeCausedEdges", () => {
  it("merges duplicate CAUSED edges between the same alerts", () => {
    const edges: GraphEdge[] = [
      {
        id: "seq",
        from: "a",
        to: "b",
        label: "CAUSED",
        properties: { narrative: "Sequential Step (+15m)" },
      },
      {
        id: "neo",
        from: "a",
        to: "b",
        label: "CAUSED",
        properties: { confidence: "chronological_sequence" },
      },
    ]
    const out = dedupeCausedEdges(edges)
    expect(out.filter((e) => e.label === "CAUSED")).toHaveLength(1)
    expect(out[0].properties?.narrative).toBe("Sequential Step (+15m)")
  })
})
