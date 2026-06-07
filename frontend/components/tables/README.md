# TsocDataTable — shared frontend data table

Data-driven table component for list pages in the ThinkingSOC hackathon. Any page with a table (Analysis, Inventory, Identity Rules, etc.) should use this component so **search, column filters, sorting, pagination**, and styling stay consistent.

Visual reference: [`project-engineering/04-ui/ui-standard/ui-standards/10-datatable.md`](../../../project-engineering/04-ui/ui-standard/ui-standards/10-datatable.md) and [`19-patterns-experiences.md`](../../../project-engineering/04-ui/ui-standard/ui-standards/19-patterns-experiences.md).

## Files

| File | Role |
|------|------|
| `tsoc-data-table.tsx` | Main component (toolbar + table + pagination) |
| `use-tsoc-table.ts` | State hook: search, filter, sort, paging |
| `tsoc-table-toolbar.tsx` | Search bar and column filter dropdowns |
| `tsoc-table-pagination.tsx` | Footer: Showing…, Rows per page, Prev/Next |
| `lib/tsoc-table.ts` | Pure helpers (compare, paginate, range) |
| `lib/storage-events.ts` | Column helpers for Analysis storage events |

## Import

```tsx
import { TsocDataTable, type TsocColumn } from "@/components/tables"
```

## Quick start

```tsx
type Row = { id: string; name: string }

const columns: TsocColumn<Row>[] = [
  {
    id: "name",
    header: "Name",
    cell: (row) => row.name,
    sortable: true,
    sortValue: (row) => row.name,
    searchValue: (row) => row.name,
  },
]

<TsocDataTable
  accent="orange"
  columns={columns}
  rows={data}
  getRowKey={(row) => row.id}
  defaultPageSize={10}
  searchPlaceholder="Search records…"
/>
```

## Column definition (`TsocColumn<T>`)

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Unique id for sort/filter |
| `header` | `ReactNode` | Column header |
| `cell` | `(row) => ReactNode` | Cell content |
| `headClassName` | `string?` | Extra class on `<th>` |
| `cellClassName` | `string?` | Extra class on `<td>` |
| `sortable` | `boolean?` | Enable header sort |
| `sortValue` | `(row) => string \| number \| null` | Value used for comparison |
| `searchValue` | `(row) => string \| number \| null` | Included in global search (falls back to `sortValue`) |
| `filterable` | `boolean?` | Show column filter in toolbar |
| `filterLabel` | `string?` | Filter label (default: column `id`) |
| `filterOptions` | `{ label, value }[]` | Filter choices (`__all__` for “All” is added automatically) |
| `filterValue` | `(row) => string \| null` | Row value matched against the filter |

### Sorting

- Header click cycle: **ascending → descending → no sort**
- Sort buttons use class `header-sort-btn` (ui-standard: no boxed border)
- When `enablePagination={false}`, rows still come from `sortedRows` (not unsorted `filteredRows`)

### Search

- Matches any column with `searchValue` or `sortValue`
- Or supply custom `globalSearchFn` on the table

### Column filters

- Only columns with `filterable: true` and non-empty `filterOptions`
- Value `__all__` clears the filter for that column

## Table props (`TsocDataTableProps<T>`)

| Prop | Default | Description |
|------|---------|-------------|
| `columns` | — | Column definitions (required) |
| `rows` | — | Data rows (required) |
| `getRowKey` | — | Stable React key per row (required) |
| `accent` | `"teal"` | Neon accent (`teal`, `orange`, `violet`, …) |
| `emptyMessage` | `"No records"` | Text when there are no rows |
| `loading` | `false` | Loading state |
| `loadingMessage` | `"Loading…"` | Loading text in table or initial block |
| `maxHeight` | `"420px"` | Max height of vertical scroll area |
| `onRowClick` | — | Row click handler |
| `selectedRowKey` | — | Sets `data-state=selected` on matching row |
| `enableSearch` | `true` | Search toolbar |
| `enableFilters` | `true` | Column filters in toolbar |
| `enablePagination` | `true` | Pagination footer |
| `searchPlaceholder` | `"Search table…"` | Search input placeholder |
| `defaultPageSize` | `10` | Rows per page |
| `pageSizeOptions` | `[10,25,50,100]` | Rows-per-page choices |
| `globalSearchFn` | — | Custom `(row, query) => boolean` |
| `tableContainerClassName` | — | Extra classes on table container |

## Loading (ui-standard)

- **`loading && rows.length === 0`**: Replace table with a `font-mono text-slate-400` message (e.g. `Loading analysis records…`)
- **`loading && rows.length > 0`**: Single “Loading…” row in tbody (e.g. refresh)

## Analysis page (real example)

[`components/pages/analysis-content.tsx`](../pages/analysis-content.tsx):

- Columns: Type, Search, SID, Row, Created, Verdict, Investigation
- Verdict filter options built from distinct values in the dataset
- **View** link → `/analysis/investigation/{id}`

Column helpers: [`lib/storage-events.ts`](../../lib/storage-events.ts)

```ts
import {
  formatEventCreatedAt,
  getEventVerdict,
  getStorageEventId,
} from "@/lib/storage-events"
```

Investigation page: [`components/pages/investigation-content.tsx`](../pages/investigation-content.tsx) — `GET /storage/events/{id}`

## `useTsocTable` hook (advanced)

Use when you need table state without the default UI:

```tsx
import { useTsocTable } from "@/components/tables"

const table = useTsocTable({ rows, columns, defaultPageSize: 25 })

// table.search, table.setSearch
// table.toggleSort, table.setColumnFilter
// table.pageIndex, table.setPageIndex, table.pageSize, table.setPageSize
// table.pageRows, table.filteredRows, table.sortedRows, table.totalRows
```

## ui-standard checklist

- [ ] Table container: `rounded-xl border border-white/10 bg-black/10 backdrop-blur-sm`
- [ ] Toolbar: `border-b border-white/5 px-6 py-4` + Search icon
- [ ] Pagination footer: `px-4 sm:px-6`
- [ ] Rows per page: `getNeonSelectContentClassName(accent)` on `SelectContent`
- [ ] Horizontal scroll: `TsocHorizontalScroll` + `min-w-[800px]`
- [ ] Sort headers: `header-sort-btn` class, no extra border

## Tests

```bash
cd frontend
npm install
npm test -- --run components/tables lib/tsoc-table.test.ts lib/storage-events.test.ts
```

| Test file | Coverage |
|-----------|----------|
| `tsoc-data-table.test.tsx` | Integrated UI, search, sort, pagination |
| `use-tsoc-table.test.ts` | State logic |
| `tsoc-table-toolbar.test.tsx` | Toolbar |
| `tsoc-table-pagination.test.tsx` | Footer |
| `lib/tsoc-table.test.ts` | Pure helpers |
| `lib/storage-events.test.ts` | Analysis column helpers |

Test environment: **happy-dom** (`vitest.config.mts`).

## vs `NeonTable`

| | `NeonTable` | `TsocDataTable` |
|---|-------------|-----------------|
| Level | Styled primitives (`<table>`, `<tr>`, …) | Data-driven + search/filter/sort/paging |
| Use | Manual tables or inside TsocDataTable | Product list/table pages |
| Pagination | No | Yes |

New list pages must use **`TsocDataTable` only**; manual `<NeonTable>` + separate pagination is not allowed (ui-standard §10).
