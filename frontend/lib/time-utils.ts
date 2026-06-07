export type TimeFilterOption = { label: string; value: string }

export const TIME_FILTER_OPTIONS: TimeFilterOption[] = [
  { label: "All time", value: "all" },
  { label: "Last 15 minutes", value: "15m" },
  { label: "Last 1 hour", value: "1h" },
  { label: "Last 24 hours", value: "24h" },
  { label: "Last 7 days", value: "7d" },
  { label: "Last 30 days", value: "30d" },
  { label: "Last 90 days", value: "90d" },
]

const TIME_FILTER_PATTERN = /^(\d+)\s*(s|m|h|d|w|mo|y)$/i

const UNIT_MS: Record<string, number> = {
  s: 1000,
  m: 60 * 1000,
  h: 60 * 60 * 1000,
  d: 24 * 60 * 60 * 1000,
  w: 7 * 24 * 60 * 60 * 1000,
  mo: 30 * 24 * 60 * 60 * 1000,
  y: 365 * 24 * 60 * 60 * 1000,
}

/** Earliest instant included when filter is "all". */
export function parseTimeFilter(filter: string): Date {
  const trimmed = filter.trim()
  if (trimmed.toLowerCase() === "all") {
    return new Date(0)
  }
  if (!trimmed) {
    return new Date()
  }

  const match = trimmed.match(TIME_FILTER_PATTERN)
  if (!match) {
    return new Date()
  }

  const amount = Number.parseInt(match[1], 10)
  const unit = match[2].toLowerCase()
  const unitMs = UNIT_MS[unit]
  if (!Number.isFinite(amount) || amount <= 0 || unitMs == null) {
    return new Date()
  }

  return new Date(Date.now() - amount * unitMs)
}

export function rowMatchesTimeFilter(
  rowTime: unknown,
  filter: string
): boolean {
  if (!filter.trim() || filter.toLowerCase() === "all") return true
  if (rowTime == null || rowTime === "") return false

  const instant = new Date(String(rowTime))
  if (Number.isNaN(instant.getTime())) return false

  return instant >= parseTimeFilter(filter)
}

export const TIME_FILTER_STORAGE_PREFIX = "tsoc.timeFilter."

export function readStoredTimeFilter(storageKey: string): string | null {
  if (typeof window === "undefined") return null
  try {
    const value = window.localStorage.getItem(`${TIME_FILTER_STORAGE_PREFIX}${storageKey}`)
    if (!value) return null
    return TIME_FILTER_OPTIONS.some((o) => o.value === value) ? value : null
  } catch {
    return null
  }
}

export function writeStoredTimeFilter(storageKey: string, value: string): void {
  if (typeof window === "undefined") return
  try {
    window.localStorage.setItem(`${TIME_FILTER_STORAGE_PREFIX}${storageKey}`, value)
  } catch {
    // ignore quota / private mode
  }
}
