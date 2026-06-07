export function riskScoreClass(score: number): string {
  if (score >= 70) return "bg-red-500/20 text-red-300 border-red-500/30"
  if (score >= 40) return "bg-amber-500/20 text-amber-300 border-amber-500/30"
  return "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
}

export function nodeColorByRisk(score: number | undefined, group: string[]): string {
  if (group.includes("Alert") && typeof score === "number") {
    if (score >= 70) return "#f87171"
    if (score >= 40) return "#fbbf24"
    return "#34d399"
  }
  if (group.includes("Identity")) return "#38bdf8"
  if (group.includes("Asset")) return "#a78bfa"
  if (group.includes("IOC")) return "#fb923c"
  if (group.includes("Incident")) return "#f472b6"
  return "#94a3b8"
}
