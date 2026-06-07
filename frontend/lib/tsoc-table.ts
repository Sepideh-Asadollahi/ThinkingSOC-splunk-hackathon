export type SortDirection = "asc" | "desc"

export function compareValues(a: unknown, b: unknown): number {
  if (a == null && b == null) return 0
  if (a == null) return 1
  if (b == null) return -1
  if (typeof a === "number" && typeof b === "number") return a - b
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" })
}

export function paginateSlice<T>(rows: T[], pageIndex: number, pageSize: number): T[] {
  const start = pageIndex * pageSize
  return rows.slice(start, start + pageSize)
}

export function pageCount(total: number, pageSize: number): number {
  if (total === 0) return 1
  return Math.max(1, Math.ceil(total / pageSize))
}

export function showingRange(
  total: number,
  pageIndex: number,
  pageSize: number
): { start: number; end: number } {
  if (total === 0) return { start: 0, end: 0 }
  const start = pageIndex * pageSize + 1
  const end = Math.min(total, (pageIndex + 1) * pageSize)
  return { start, end }
}
