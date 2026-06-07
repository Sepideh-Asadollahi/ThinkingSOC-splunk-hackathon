"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { EyeIcon, Link2Icon, PencilIcon, PlusIcon, RefreshCwIcon, Trash2Icon } from "lucide-react"

import { RelationshipDetailDialog } from "@/components/pages/relationship-detail-dialog"

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
} from "@/components/neon-glass"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { TsocHorizontalScroll } from "@/components/ui/tsoc-scroll"
import { ApiError, backendFetch } from "@/lib/api/client"
import type { AssetRecord, RelationshipRecord, UserRecord } from "@/lib/api/types"

function userLabel(u: UserRecord): string {
  const name = u.display_name?.trim() || u.email?.trim()
  return name ? `${name} (${u.user_id})` : u.user_id
}

function assetLabel(a: AssetRecord): string {
  const host = a.hostname?.trim() || a.ip?.trim() || a.fqdn?.trim()
  return host ? `${host} (${a.asset_id})` : a.asset_id
}

function suggestRelationshipId(userId: string, assetId: string): string {
  const base = `rel-${userId}-${assetId}`
  return base.replace(/[^a-zA-Z0-9_-]/g, "-").slice(0, 120)
}

const emptyForm = (): Partial<RelationshipRecord> => ({
  relationship_id: "",
  user_id: "",
  asset_id: "",
  description: "",
})

export function RelationshipsContent() {
  const [rows, setRows] = useState<RelationshipRecord[]>([])
  const [users, setUsers] = useState<UserRecord[]>([])
  const [assets, setAssets] = useState<AssetRecord[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<Partial<RelationshipRecord>>(emptyForm)
  const [isEdit, setIsEdit] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailRow, setDetailRow] = useState<RelationshipRecord | null>(null)

  const selectContentClass = getNeonSelectContentClassName("violet")
  const userById = useMemo(() => new Map(users.map((u) => [u.user_id, u])), [users])
  const assetById = useMemo(() => new Map(assets.map((a) => [a.asset_id, a])), [assets])
  const canCreate = users.length > 0 && assets.length > 0

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [rels, u, a] = await Promise.all([
        backendFetch<RelationshipRecord[]>("/inventory/relationships"),
        backendFetch<UserRecord[]>("/inventory/users"),
        backendFetch<AssetRecord[]>("/inventory/assets"),
      ])
      setRows(rels)
      setUsers(u)
      setAssets(a)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load relationships")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  function openCreate() {
    if (!canCreate) {
      setError("Add at least one user and one asset in Inventory before creating a relationship.")
      return
    }
    setIsEdit(false)
    const firstUser = users[0]!
    const firstAsset = assets[0]!
    setEditing({
      ...emptyForm(),
      user_id: firstUser.user_id,
      asset_id: firstAsset.asset_id,
      relationship_id: suggestRelationshipId(firstUser.user_id, firstAsset.asset_id),
    })
    setOpen(true)
  }

  function openEdit(row: RelationshipRecord) {
    setIsEdit(true)
    setEditing({ ...row })
    setOpen(true)
  }

  function openDetail(row: RelationshipRecord) {
    setDetailRow(row)
    setDetailOpen(true)
  }

  function onUserChange(userId: string) {
    setEditing((prev) => {
      const assetId = prev.asset_id ?? ""
      return {
        ...prev,
        user_id: userId,
        relationship_id:
          !isEdit && assetId ? suggestRelationshipId(userId, assetId) : prev.relationship_id,
      }
    })
  }

  function onAssetChange(assetId: string) {
    setEditing((prev) => {
      const userId = prev.user_id ?? ""
      return {
        ...prev,
        asset_id: assetId,
        relationship_id:
          !isEdit && userId ? suggestRelationshipId(userId, assetId) : prev.relationship_id,
      }
    })
  }

  async function save(e: React.FormEvent) {
    e.preventDefault()
    const body = { ...(editing as RelationshipRecord) }
    if (!isEdit && !body.relationship_id?.trim() && body.user_id && body.asset_id) {
      body.relationship_id = suggestRelationshipId(body.user_id, body.asset_id)
    }
    try {
      if (isEdit) {
        await backendFetch(`/inventory/relationships/${encodeURIComponent(body.relationship_id)}`, {
          method: "PATCH",
          body: JSON.stringify({
            user_id: body.user_id,
            asset_id: body.asset_id,
            description: body.description || null,
          }),
        })
      } else {
        await backendFetch("/inventory/relationships", {
          method: "POST",
          body: JSON.stringify(body),
        })
      }
      setOpen(false)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed")
    }
  }

  async function remove(id: string) {
    try {
      await backendFetch(`/inventory/relationships/${encodeURIComponent(id)}`, {
        method: "DELETE",
      })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed")
    }
  }

  return (
    <div className="space-y-4">
      <NeonGlassCard accent="violet">
        <NeonCardHeader
          accent="violet"
          icon={<Link2Icon className="size-5 text-violet-400" />}
          title="Relationships"
          description="Map users to assets for enrichment when alerts match only one side"
          actions={
            <>
              <NeonActionButton accent="violet" onClick={() => void load()} disabled={loading}>
                <RefreshCwIcon className="size-4" />
                Refresh
              </NeonActionButton>
              <NeonActionButton
                accent="violet"
                type="button"
                onClick={openCreate}
                disabled={!canCreate && !loading}
                title={
                  canCreate ? undefined : "Add users and assets in Inventory first"
                }
              >
                <PlusIcon className="size-4" />
                Add relationship
              </NeonActionButton>
              <Dialog open={open} onOpenChange={setOpen}>
                <NeonDialogContent accent="violet">
                  <form onSubmit={save} className="space-y-4">
                    <NeonDialogHeaderWithIcon
                      accent="violet"
                      icon={<Link2Icon className="size-5 text-violet-400" />}
                      title={isEdit ? "Edit relationship" : "Create relationship"}
                    />
                    <div className="grid gap-3 px-6">
                      <NeonField>
                        <NeonFieldLabel>User</NeonFieldLabel>
                        <Select value={editing.user_id ?? ""} onValueChange={onUserChange}>
                          <SelectTrigger className="w-full border-white/10 bg-slate-900/60">
                            <SelectValue placeholder="Select user" />
                          </SelectTrigger>
                          <SelectContent className={selectContentClass}>
                            {users.map((u) => (
                              <SelectItem key={u.user_id} value={u.user_id}>
                                {userLabel(u)}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </NeonField>
                      <NeonField>
                        <NeonFieldLabel>Asset</NeonFieldLabel>
                        <Select value={editing.asset_id ?? ""} onValueChange={onAssetChange}>
                          <SelectTrigger className="w-full border-white/10 bg-slate-900/60">
                            <SelectValue placeholder="Select asset" />
                          </SelectTrigger>
                          <SelectContent className={selectContentClass}>
                            {assets.map((a) => (
                              <SelectItem key={a.asset_id} value={a.asset_id}>
                                {assetLabel(a)}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </NeonField>
                      <NeonField>
                        <NeonFieldLabel>Description (optional)</NeonFieldLabel>
                        <NeonInput
                          accent="violet"
                          placeholder="Short note for analysts"
                          value={editing.description ?? ""}
                          onChange={(e) =>
                            setEditing({ ...editing, description: e.target.value })
                          }
                        />
                      </NeonField>
                    </div>
                    <NeonDialogFooter className="px-6 pb-6">
                      <NeonDialogFooterButton
                        accent="violet"
                        type="button"
                        footerVariant="secondary"
                        onClick={() => setOpen(false)}
                      >
                        Cancel
                      </NeonDialogFooterButton>
                      <NeonDialogFooterButton accent="violet" type="submit">
                        Save
                      </NeonDialogFooterButton>
                    </NeonDialogFooter>
                  </form>
                </NeonDialogContent>
              </Dialog>
            </>
          }
        />
        <div className="px-6 pb-6">
          {error ? (
            <NeonAlert variant="destructive" className="mb-4">
              <NeonAlertTitle>Error</NeonAlertTitle>
              <NeonAlertDescription>{error}</NeonAlertDescription>
            </NeonAlert>
          ) : null}
          {!loading && !canCreate ? (
            <NeonAlert className="mb-4">
              <NeonAlertTitle>Inventory required</NeonAlertTitle>
              <NeonAlertDescription>
                Add users and assets under Inventory, then return here to link them.
              </NeonAlertDescription>
            </NeonAlert>
          ) : null}
          <TsocHorizontalScroll>
            <NeonTable>
              <NeonTableHeader>
                <NeonTableRow>
                  <NeonTableHead>ID</NeonTableHead>
                  <NeonTableHead>User</NeonTableHead>
                  <NeonTableHead>Asset</NeonTableHead>
                  <NeonTableHead>Description</NeonTableHead>
                  <NeonTableHead />
                </NeonTableRow>
              </NeonTableHeader>
              <NeonTableBody>
                {rows.map((r) => (
                  <NeonTableRow key={r.relationship_id}>
                    <NeonTableCell className="font-mono text-xs">{r.relationship_id}</NeonTableCell>
                    <NeonTableCell>
                      {userById.has(r.user_id)
                        ? userLabel(userById.get(r.user_id)!)
                        : r.user_id}
                    </NeonTableCell>
                    <NeonTableCell>
                      {assetById.has(r.asset_id)
                        ? assetLabel(assetById.get(r.asset_id)!)
                        : r.asset_id}
                    </NeonTableCell>
                    <NeonTableCell className="max-w-[240px] truncate">{r.description}</NeonTableCell>
                    <NeonTableCell className="flex gap-1">
                      <NeonActionButton
                        accent="violet"
                        size="sm"
                        type="button"
                        title="View linked attributes"
                        onClick={() => openDetail(r)}
                      >
                        <EyeIcon className="size-3.5" />
                      </NeonActionButton>
                      <NeonActionButton
                        accent="violet"
                        size="sm"
                        type="button"
                        onClick={() => openEdit(r)}
                      >
                        <PencilIcon className="size-3.5" />
                      </NeonActionButton>
                      <NeonActionButton
                        accent="violet"
                        size="sm"
                        type="button"
                        onClick={() => void remove(r.relationship_id)}
                      >
                        <Trash2Icon className="size-3.5" />
                      </NeonActionButton>
                    </NeonTableCell>
                  </NeonTableRow>
                ))}
              </NeonTableBody>
            </NeonTable>
          </TsocHorizontalScroll>
        </div>
      </NeonGlassCard>

      <RelationshipDetailDialog
        open={detailOpen}
        onOpenChange={setDetailOpen}
        relationship={detailRow}
        user={detailRow ? userById.get(detailRow.user_id) : undefined}
        asset={detailRow ? assetById.get(detailRow.asset_id) : undefined}
      />
    </div>
  )
}
