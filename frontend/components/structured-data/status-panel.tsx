"use client"

import { FieldGrid } from "./field-grid"
import { isRecord, labelize } from "./utils"

export function StatusPanel({ data }: { data: Record<string, unknown> | null }) {
  if (!data) return <p className="px-6 pb-6 text-sm text-slate-500">—</p>

  const fields = Object.entries(data).map(([key, value]) => {
    if (Array.isArray(value)) {
      return { fieldKey: key, label: labelize(key), value: value.map(String).join(", ") || "—" }
    }
    if (isRecord(value)) {
      return {
        fieldKey: key,
        label: labelize(key),
        value: Object.entries(value)
          .map(([k, v]) => `${labelize(k)}: ${String(v)}`)
          .join(" · "),
      }
    }
    return {
      fieldKey: key,
      label: labelize(key),
      value: value == null || value === "" ? "—" : value,
      mono: /url|host|model|sid/i.test(key),
    }
  })

  return (
    <div className="px-6 pb-6">
      <FieldGrid fields={fields} />
    </div>
  )
}
