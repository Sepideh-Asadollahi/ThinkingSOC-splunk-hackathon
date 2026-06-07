"use client"

import type { ReactNode } from "react"

import { FieldGrid } from "./field-grid"
import { DataSection } from "./section"
import { isRecord, labelize } from "./utils"

function isPrimitive(value: unknown): boolean {
  return value === null || ["string", "number", "boolean"].includes(typeof value)
}

function renderValue(value: unknown, depth: number): ReactNode {
  if (value === null || value === undefined) return <span className="text-slate-500">—</span>
  if (isPrimitive(value)) {
    return <span className="text-sm text-slate-300">{String(value)}</span>
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-slate-500">Empty list</span>
    if (value.every((v) => typeof v === "string" || typeof v === "number")) {
      return (
        <ul className="list-inside list-disc text-sm text-slate-300">
          {value.map((item, i) => (
            <li key={i}>{String(item)}</li>
          ))}
        </ul>
      )
    }
    return (
      <ul className="space-y-2">
        {value.map((item, i) => (
          <li key={i} className="rounded border border-white/10 bg-black/30 p-2">
            {isRecord(item) ? (
              <StructuredDataView data={item} depth={depth + 1} compact />
            ) : (
              <span className="text-sm text-slate-300">{String(item)}</span>
            )}
          </li>
        ))}
      </ul>
    )
  }
  if (isRecord(value)) {
    return <StructuredDataView data={value} depth={depth + 1} compact />
  }
  return <span className="text-sm text-slate-300">{String(value)}</span>
}

export function StructuredDataView({
  data,
  depth = 0,
  compact = false,
}: {
  data: Record<string, unknown>
  depth?: number
  compact?: boolean
}) {
  const entries = Object.entries(data)
  if (entries.length === 0) return <p className="text-sm text-slate-500">No data</p>

  const simpleFields = entries
    .filter(([, v]) => isPrimitive(v))
    .map(([key, value]) => ({
      fieldKey: key,
      label: labelize(key),
      value,
      mono: /sid|_id|spl/i.test(key),
    }))

  const nested = entries.filter(([, v]) => !isPrimitive(v))

  if (compact || depth > 0) {
    return (
      <div className="space-y-2">
        {simpleFields.length > 0 ? <FieldGrid fields={simpleFields} /> : null}
        {nested.map(([key, value]) => (
          <div key={key}>
            <p className="mb-1 text-xs font-medium text-slate-500">{labelize(key)}</p>
            {renderValue(value, depth)}
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {simpleFields.length > 0 ? (
        <DataSection title="Overview" defaultOpen>
          <FieldGrid fields={simpleFields} />
        </DataSection>
      ) : null}
      {nested.map(([key, value]) => (
        <DataSection key={key} title={labelize(key)} defaultOpen={nested.length <= 3}>
          {renderValue(value, depth)}
        </DataSection>
      ))}
    </div>
  )
}
