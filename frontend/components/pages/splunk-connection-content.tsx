"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { PencilIcon, PlugIcon, PlusIcon, RefreshCwIcon, Trash2Icon } from "lucide-react"

import {
  Dialog,
  getNeonSelectContentClassName,
  NeonActionButton,
  NeonAlert,
  NeonAlertDescription,
  NeonAlertTitle,
  NeonCardHeader,
  NeonDialogContent,
  NeonDialogFooter,
  NeonDialogFooterButton,
  NeonDialogHeaderWithIcon,
  NeonField,
  NeonFieldLabel,
  NeonGlassCard,
  NeonInput,
  NeonTable,
  NeonTableBody,
  NeonTableCell,
  NeonTableHead,
  NeonTableHeader,
  NeonTableRow,
  NeonTabs,
  NeonTabsContent,
  NeonTabsContents,
  NeonTabsList,
  NeonTabsTrigger,
} from "@/components/neon-glass"
import { TsocHorizontalScroll } from "@/components/ui/tsoc-scroll"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ApiError, backendFetch } from "@/lib/api/client"
import type { IntegrationSettingRecord, SettingCategory } from "@/lib/api/types"

const TAB_ORDER: SettingCategory[] = [
  "splunk_rest",
  "splunk_mcp",
  "litellm",
  "postgres",
  "virustotal",
  "ingest",
  "analysis",
  "custom",
]

const CATEGORY_LABELS: Record<SettingCategory, string> = {
  splunk_rest: "Splunk REST",
  splunk_mcp: "Splunk MCP",
  litellm: "LiteLLM",
  postgres: "PostgreSQL & inventory",
  virustotal: "VirusTotal",
  ingest: "Ingest",
  analysis: "Analysis",
  custom: "Custom",
}

const emptySetting = (category: SettingCategory = "custom"): IntegrationSettingRecord => ({
  id: "",
  category,
  key: "",
  value: "",
  description: "",
  is_secret: false,
  builtin: false,
  env_var: null,
  configured: false,
})

function SettingsTable({
  rows,
  onEdit,
  onDelete,
}: {
  rows: IntegrationSettingRecord[]
  onEdit: (row: IntegrationSettingRecord) => void
  onDelete: (id: string) => void
}) {
  if (rows.length === 0) {
    return <p className="text-sm text-slate-500">No settings in this section.</p>
  }

  return (
    <TsocHorizontalScroll>
      <NeonTable>
        <NeonTableHeader>
          <NeonTableRow>
            <NeonTableHead>Key</NeonTableHead>
            <NeonTableHead>Value</NeonTableHead>
            <NeonTableHead>Description</NeonTableHead>
            <NeonTableHead>Type</NeonTableHead>
            <NeonTableHead />
          </NeonTableRow>
        </NeonTableHeader>
        <NeonTableBody>
          {rows.map((row) => (
            <NeonTableRow key={row.id}>
              <NeonTableCell className="font-mono text-xs">{row.key}</NeonTableCell>
              <NeonTableCell className="max-w-[280px] truncate font-mono text-xs">
                {row.value || (row.is_secret && !row.configured ? "—" : "")}
              </NeonTableCell>
              <NeonTableCell className="max-w-[320px] truncate text-xs text-slate-400">
                {row.description ?? "—"}
              </NeonTableCell>
              <NeonTableCell className="text-xs whitespace-nowrap">
                {row.builtin ? "built-in" : "custom"}
                {row.is_secret ? " · secret" : ""}
              </NeonTableCell>
              <NeonTableCell>
                <div className="flex justify-end gap-1">
                  <NeonActionButton
                    accent="teal"
                    size="sm"
                    type="button"
                    onClick={() => onEdit(row)}
                  >
                    <PencilIcon className="size-3.5" />
                  </NeonActionButton>
                  {!row.builtin ? (
                    <NeonActionButton
                      accent="teal"
                      size="sm"
                      type="button"
                      onClick={() => onDelete(row.id)}
                    >
                      <Trash2Icon className="size-3.5" />
                    </NeonActionButton>
                  ) : null}
                </div>
              </NeonTableCell>
            </NeonTableRow>
          ))}
        </NeonTableBody>
      </NeonTable>
    </TsocHorizontalScroll>
  )
}

export function SplunkConnectionContent() {
  const [settings, setSettings] = useState<IntegrationSettingRecord[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<SettingCategory>("splunk_rest")
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState(emptySetting())
  const [isEdit, setIsEdit] = useState(false)
  const selectContentClass = getNeonSelectContentClassName("teal")

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await backendFetch<IntegrationSettingRecord[]>("/integrations/settings")
      setSettings(data)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load settings")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const byCategory = useMemo(() => {
    const map = Object.fromEntries(TAB_ORDER.map((c) => [c, [] as IntegrationSettingRecord[]])) as Record<
      SettingCategory,
      IntegrationSettingRecord[]
    >
    for (const row of settings) {
      const cat = row.category in map ? row.category : "custom"
      map[cat].push(row)
    }
    for (const cat of TAB_ORDER) {
      map[cat].sort((a, b) => a.key.localeCompare(b.key))
    }
    return map
  }, [settings])

  function openCreate(category: SettingCategory) {
    setIsEdit(false)
    setEditing(emptySetting(category))
    setOpen(true)
  }

  function openEdit(row: IntegrationSettingRecord) {
    setIsEdit(true)
    setTab(row.category)
    setEditing({
      ...row,
      value: row.is_secret && row.configured ? "" : row.value,
    })
    setOpen(true)
  }

  async function saveSetting(e: React.FormEvent) {
    e.preventDefault()
    try {
      if (isEdit) {
        const patchBody = editing.builtin
          ? { value: editing.value ?? "" }
          : {
              category: editing.category,
              key: editing.key,
              value: editing.value ?? "",
              description: editing.description || null,
              is_secret: editing.is_secret,
            }
        await backendFetch(`/integrations/settings/${encodeURIComponent(editing.id)}`, {
          method: "PATCH",
          body: JSON.stringify(patchBody),
        })
      } else {
        await backendFetch("/integrations/settings", {
          method: "POST",
          body: JSON.stringify({
            id: editing.id,
            category: editing.category ?? tab,
            key: editing.key,
            value: editing.value ?? "",
            description: editing.description || null,
            is_secret: editing.is_secret ?? false,
          }),
        })
      }
      setOpen(false)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed")
    }
  }

  async function deleteSetting(id: string) {
    try {
      await backendFetch(`/integrations/settings/${encodeURIComponent(id)}`, {
        method: "DELETE",
      })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed")
    }
  }

  const lockCategoryInDialog = isEdit ? Boolean(editing.builtin) : tab !== "custom"

  return (
    <div className="space-y-4">
      <NeonGlassCard accent="teal" animatePreset="page">
        <NeonCardHeader
          accent="teal"
          icon={<PlugIcon className="size-5 text-teal-400" />}
          title="Splunk & Integrations"
          description="Each tab groups related connection settings in one table"
          actions={
            <NeonActionButton accent="teal" onClick={() => void load()} disabled={loading}>
              <RefreshCwIcon className="size-4" />
              Refresh
            </NeonActionButton>
          }
        />

        <div className="px-6 pb-6">
          {error ? (
            <NeonAlert variant="destructive" className="mb-4">
              <NeonAlertTitle>Error</NeonAlertTitle>
              <NeonAlertDescription>{error}</NeonAlertDescription>
            </NeonAlert>
          ) : null}

          {loading ? (
            <p className="text-sm text-slate-500">Loading settings…</p>
          ) : (
            <NeonTabs value={tab} onValueChange={(v) => setTab(v as SettingCategory)}>
              <NeonTabsList accent="teal" className="flex-wrap">
                {TAB_ORDER.map((cat) => (
                  <NeonTabsTrigger key={cat} accent="teal" value={cat}>
                    {CATEGORY_LABELS[cat]} ({byCategory[cat].length})
                  </NeonTabsTrigger>
                ))}
              </NeonTabsList>

              <NeonTabsContents>
                {TAB_ORDER.map((cat) => (
                  <NeonTabsContent key={cat} value={cat} className="space-y-4 pt-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm text-slate-400">
                        {CATEGORY_LABELS[cat]} — {byCategory[cat].length} setting
                        {byCategory[cat].length === 1 ? "" : "s"}
                      </p>
                      {cat === "custom" ? (
                        <NeonActionButton accent="teal" type="button" onClick={() => openCreate(cat)}>
                          <PlusIcon className="size-4" />
                          Add custom setting
                        </NeonActionButton>
                      ) : null}
                    </div>
                    <SettingsTable
                      rows={byCategory[cat]}
                      onEdit={openEdit}
                      onDelete={(id) => void deleteSetting(id)}
                    />
                  </NeonTabsContent>
                ))}
              </NeonTabsContents>
            </NeonTabs>
          )}
        </div>

        <Dialog open={open} onOpenChange={setOpen}>
          <NeonDialogContent accent="teal">
            <form onSubmit={saveSetting} className="space-y-4">
              <NeonDialogHeaderWithIcon
                accent="teal"
                icon={<PlugIcon className="size-5 text-teal-400" />}
                title={isEdit ? "Edit setting" : `Add — ${CATEGORY_LABELS[editing.category ?? tab]}`}
              />
              <div className="grid gap-3 px-6">
                {!isEdit ? (
                  <NeonField>
                    <NeonFieldLabel>ID</NeonFieldLabel>
                    <NeonInput
                      accent="teal"
                      placeholder="my_setting_id"
                      value={editing.id}
                      onChange={(e) => setEditing({ ...editing, id: e.target.value })}
                      required
                    />
                  </NeonField>
                ) : null}
                {!lockCategoryInDialog ? (
                  <NeonField>
                    <NeonFieldLabel>Category</NeonFieldLabel>
                    <Select
                      value={editing.category ?? tab}
                      onValueChange={(v) =>
                        setEditing({ ...editing, category: v as SettingCategory })
                      }
                    >
                      <SelectTrigger className="w-full border-white/10 bg-slate-900/60">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className={selectContentClass}>
                        {TAB_ORDER.map((c) => (
                          <SelectItem key={c} value={c}>
                            {CATEGORY_LABELS[c]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </NeonField>
                ) : null}
                <NeonField>
                  <NeonFieldLabel>Key</NeonFieldLabel>
                  <NeonInput
                    accent="teal"
                    placeholder="ENV_VAR or label"
                    value={editing.key ?? ""}
                    onChange={(e) => setEditing({ ...editing, key: e.target.value })}
                    required
                    disabled={isEdit && editing.builtin}
                  />
                </NeonField>
                <NeonField>
                  <NeonFieldLabel>
                    Value
                    {editing.is_secret && isEdit && editing.configured
                      ? " (leave blank to keep current)"
                      : null}
                  </NeonFieldLabel>
                  <NeonInput
                    accent="teal"
                    placeholder={editing.is_secret ? "secret value" : "value"}
                    type={editing.is_secret ? "password" : "text"}
                    value={editing.value ?? ""}
                    onChange={(e) => setEditing({ ...editing, value: e.target.value })}
                  />
                </NeonField>
                <NeonField>
                  <NeonFieldLabel>Description</NeonFieldLabel>
                  <NeonInput
                    accent="teal"
                    placeholder="optional description"
                    value={editing.description ?? ""}
                    onChange={(e) => setEditing({ ...editing, description: e.target.value })}
                    disabled={isEdit && editing.builtin}
                  />
                </NeonField>
                {!editing.builtin ? (
                  <label className="flex items-center gap-2 text-sm text-slate-300">
                    <input
                      type="checkbox"
                      checked={Boolean(editing.is_secret)}
                      onChange={(e) => setEditing({ ...editing, is_secret: e.target.checked })}
                    />
                    Secret (mask in table)
                  </label>
                ) : null}
              </div>
              <NeonDialogFooter className="px-6 pb-6">
                <NeonDialogFooterButton
                  accent="teal"
                  type="button"
                  footerVariant="secondary"
                  onClick={() => setOpen(false)}
                >
                  Cancel
                </NeonDialogFooterButton>
                <NeonDialogFooterButton accent="teal" type="submit">
                  Save
                </NeonDialogFooterButton>
              </NeonDialogFooter>
            </form>
          </NeonDialogContent>
        </Dialog>
      </NeonGlassCard>
    </div>
  )
}
