import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { pickThreatIntel, ThreatIntelPanel } from "./threat-intel-panel"

describe("ThreatIntelPanel", () => {
  it("renders all iocs from compact threat_intel payload", () => {
    const data = {
      threat_intel: {
        status: "ok",
        source: "virustotal",
        checked_ioc_count: 2,
        findings: [
          {
            ioc: "203.0.113.9",
            ioc_type: "ip",
            verdict: "malicious",
            last_analysis_stats: { malicious: 5, suspicious: 0, harmless: 1, undetected: 0, timeout: 0 },
          },
        ],
        iocs: [
          {
            ioc: "203.0.113.9",
            ioc_type: "ip",
            verdict: "malicious",
            last_analysis_stats: { malicious: 5, suspicious: 0, harmless: 1, undetected: 0, timeout: 0 },
            tags: ["c2"],
            link: "https://www.virustotal.com/gui/ip-address/203.0.113.9",
          },
          {
            ioc: "8.8.8.8",
            ioc_type: "ip",
            verdict: "harmless",
            last_analysis_stats: { malicious: 0, suspicious: 0, harmless: 60, undetected: 0, timeout: 0 },
          },
        ],
      },
    }

    render(<ThreatIntelPanel data={data} />)
    expect(screen.getByText("203.0.113.9")).toBeInTheDocument()
    expect(screen.getByText("8.8.8.8")).toBeInTheDocument()
    expect(screen.getByText(/tags: c2/)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /View on VirusTotal/i })).toBeInTheDocument()
  })

  it("pickThreatIntel builds iocs from legacy virustotal buckets", () => {
    const ti = pickThreatIntel({
      threat_intel: {
        virustotal: {
          enabled: true,
          ips: {
            "1.2.3.4": {
              summary: {
                type: "ip_address",
                last_analysis_stats: { malicious: 0, suspicious: 0, harmless: 10 },
              },
            },
          },
        },
      },
    })
    expect(ti?.iocs).toHaveLength(1)
    expect(ti?.iocs?.[0]?.verdict).toBe("harmless")
  })
})
