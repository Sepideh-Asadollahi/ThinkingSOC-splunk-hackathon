export type FrameworkMappingRow = {
  framework?: string
  id?: string
  name?: string
  confidence?: string
  rationale?: string
}

function normFramework(value: string): string {
  return value.trim().toLowerCase().replace("&", "and")
}

export function isMitreFramework(framework: string): boolean {
  const n = normFramework(framework)
  return n.includes("mitre") || n.includes("att&ck") || n.includes("attck")
}

export function isKillChainFramework(framework: string): boolean {
  const n = normFramework(framework)
  return n.includes("kill chain") || n === "killchain"
}

export function groupFrameworkMapping(items: unknown[]): {
  mitre: FrameworkMappingRow[]
  killChain: FrameworkMappingRow[]
  other: FrameworkMappingRow[]
} {
  const mitre: FrameworkMappingRow[] = []
  const killChain: FrameworkMappingRow[] = []
  const other: FrameworkMappingRow[] = []

  for (const item of items) {
    if (!item || typeof item !== "object") continue
    const row = item as FrameworkMappingRow
    const fw = String(row.framework ?? "MITRE ATT&CK")
    if (isKillChainFramework(fw)) killChain.push(row)
    else if (isMitreFramework(fw)) mitre.push(row)
    else other.push(row)
  }

  return { mitre, killChain, other }
}
