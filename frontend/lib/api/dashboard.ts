import { backendFetch } from "@/lib/api/client"
import type {
  ActivityTimelinePoint,
  CountByPriority,
  CountByType,
  CountByVerdict,
  DashboardOverview,
} from "@/lib/api/types"

export async function fetchDashboardOverview(): Promise<DashboardOverview> {
  return backendFetch<DashboardOverview>("/dashboard/overview")
}

export function formatActivityTimelineForChart(
  timeline: ActivityTimelinePoint[]
): Array<ActivityTimelinePoint & { label: string }> {
  return timeline.map((point) => ({
    ...point,
    label: formatShortDate(point.date),
  }))
}

export function formatShortDate(isoDate: string): string {
  const date = new Date(`${isoDate}T00:00:00`)
  if (Number.isNaN(date.getTime())) return isoDate
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" })
}

export function topRecordTypes(
  counts: CountByType[],
  limit = 8
): CountByType[] {
  return [...counts].sort((a, b) => b.count - a.count).slice(0, limit)
}

export function verdictChartData(
  items: CountByVerdict[]
): Array<{ name: string; value: number; fill: string }> {
  const colors: Record<string, string> = {
    TRUE_POSITIVE: "hsl(0 72% 55%)",
    FALSE_POSITIVE: "hsl(152 60% 45%)",
    NEEDS_HUMAN_REVIEW: "hsl(38 92% 50%)",
    UNKNOWN: "hsl(215 20% 55%)",
  }
  return items.map((item) => ({
    name: formatVerdictLabel(item.verdict),
    value: item.count,
    fill: colors[item.verdict] ?? "hsl(180 70% 45%)",
  }))
}

export function priorityChartData(
  items: CountByPriority[]
): Array<{ priority: string; count: number; fill: string }> {
  const colors: Record<string, string> = {
    critical: "hsl(0 72% 55%)",
    high: "hsl(25 90% 55%)",
    medium: "hsl(45 90% 50%)",
    low: "hsl(215 20% 55%)",
    unknown: "hsl(180 70% 45%)",
  }
  return items.map((item) => ({
    priority: item.priority,
    count: item.count,
    fill: colors[item.priority.toLowerCase()] ?? colors.unknown,
  }))
}

export function formatVerdictLabel(verdict: string): string {
  return verdict.replace(/_/g, " ")
}

export function hasChartData(values: number[]): boolean {
  return values.some((v) => v > 0)
}
