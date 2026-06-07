"use client"

import { useCallback, useEffect, useState } from "react"
import {
  PencilIcon,
  PlusIcon,
  RefreshCwIcon,
  ServerIcon,
  Trash2Icon,
  UserPlusIcon,
} from "lucide-react"

import {
  Dialog,
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
  NeonFieldGroup,
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
import { ApiError, backendFetch } from "@/lib/api/client"
import type { AssetRecord, UserRecord } from "@/lib/api/types"

const emptyUserForm = () => ({
  user_id: "",
  display_name: "",
  email: "",
  risk_score: "5",
})

const emptyAssetForm = () => ({
  asset_id: "",
  asset_type: "workstation",
  hostname: "",
  ip: "",
  criticality: "medium" as AssetRecord["criticality"],
  risk_score: "5",
})

export function InventoryContent() {
  const [tab, setTab] = useState("users")
  const [users, setUsers] = useState<UserRecord[]>([])
  const [assets, setAssets] = useState<AssetRecord[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const [userDialogOpen, setUserDialogOpen] = useState(false)
  const [assetDialogOpen, setAssetDialogOpen] = useState(false)
  const [isUserEdit, setIsUserEdit] = useState(false)
  const [isAssetEdit, setIsAssetEdit] = useState(false)
  const [userForm, setUserForm] = useState(emptyUserForm)
  const [assetForm, setAssetForm] = useState(emptyAssetForm)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [u, a] = await Promise.all([
        backendFetch<UserRecord[]>("/inventory/users"),
        backendFetch<AssetRecord[]>("/inventory/assets"),
      ])
      setUsers(u)
      setAssets(a)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load inventory")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  function openCreateUser() {
    setIsUserEdit(false)
    setUserForm(emptyUserForm())
    setUserDialogOpen(true)
  }

  function openEditUser(u: UserRecord) {
    setIsUserEdit(true)
    setUserForm({
      user_id: u.user_id,
      display_name: u.display_name ?? "",
      email: u.email ?? "",
      risk_score: String(u.risk_score),
    })
    setUserDialogOpen(true)
  }

  function openCreateAsset() {
    setIsAssetEdit(false)
    setAssetForm(emptyAssetForm())
    setAssetDialogOpen(true)
  }

  function openEditAsset(a: AssetRecord) {
    setIsAssetEdit(true)
    setAssetForm({
      asset_id: a.asset_id,
      asset_type: a.asset_type,
      hostname: a.hostname ?? "",
      ip: a.ip ?? "",
      criticality: a.criticality,
      risk_score: String(a.risk_score),
    })
    setAssetDialogOpen(true)
  }

  async function saveUser(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const payload = {
        display_name: userForm.display_name || null,
        email: userForm.email || null,
        risk_score: Number(userForm.risk_score),
      }
      if (isUserEdit) {
        await backendFetch<UserRecord>(
          `/inventory/users/${encodeURIComponent(userForm.user_id)}`,
          { method: "PATCH", body: JSON.stringify(payload) }
        )
      } else {
        await backendFetch<UserRecord>("/inventory/users", {
          method: "POST",
          body: JSON.stringify({ user_id: userForm.user_id, ...payload }),
        })
      }
      setUserDialogOpen(false)
      setUserForm(emptyUserForm())
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : isUserEdit ? "Update failed" : "Create failed")
    } finally {
      setSaving(false)
    }
  }

  async function saveAsset(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const payload = {
        asset_type: assetForm.asset_type,
        hostname: assetForm.hostname || null,
        ip: assetForm.ip || null,
        criticality: assetForm.criticality,
        risk_score: Number(assetForm.risk_score),
      }
      if (isAssetEdit) {
        await backendFetch<AssetRecord>(
          `/inventory/assets/${encodeURIComponent(assetForm.asset_id)}`,
          { method: "PATCH", body: JSON.stringify(payload) }
        )
      } else {
        await backendFetch<AssetRecord>("/inventory/assets", {
          method: "POST",
          body: JSON.stringify({ asset_id: assetForm.asset_id, ...payload }),
        })
      }
      setAssetDialogOpen(false)
      setAssetForm(emptyAssetForm())
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : isAssetEdit ? "Update failed" : "Create failed")
    } finally {
      setSaving(false)
    }
  }

  async function deleteUser(id: string) {
    try {
      await backendFetch(`/inventory/users/${encodeURIComponent(id)}`, {
        method: "DELETE",
      })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed")
    }
  }

  async function deleteAsset(id: string) {
    try {
      await backendFetch(`/inventory/assets/${encodeURIComponent(id)}`, {
        method: "DELETE",
      })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed")
    }
  }

  return (
    <div className="space-y-4">
      <NeonGlassCard accent="teal">
        <NeonCardHeader
          accent="teal"
          title="Inventory"
          description="Users and assets (PostgreSQL via FastAPI)"
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

          <NeonTabs value={tab} onValueChange={setTab}>
            <NeonTabsList accent="teal">
              <NeonTabsTrigger accent="teal" value="users">
                Users ({users.length})
              </NeonTabsTrigger>
              <NeonTabsTrigger accent="teal" value="assets">
                Assets ({assets.length})
              </NeonTabsTrigger>
            </NeonTabsList>

            <NeonTabsContents>
              <NeonTabsContent value="users" className="space-y-4">
                <div className="flex justify-end">
                  <NeonActionButton accent="teal" type="button" onClick={openCreateUser}>
                    <PlusIcon className="size-4" />
                    Add user
                  </NeonActionButton>
                </div>
                <TsocHorizontalScroll>
                  <NeonTable>
                    <NeonTableHeader>
                      <NeonTableRow>
                        <NeonTableHead>ID</NeonTableHead>
                        <NeonTableHead>Name</NeonTableHead>
                        <NeonTableHead>Email</NeonTableHead>
                        <NeonTableHead>Risk</NeonTableHead>
                        <NeonTableHead />
                      </NeonTableRow>
                    </NeonTableHeader>
                    <NeonTableBody>
                      {users.map((u) => (
                        <NeonTableRow key={u.user_id}>
                          <NeonTableCell className="font-mono text-xs">{u.user_id}</NeonTableCell>
                          <NeonTableCell>{u.display_name}</NeonTableCell>
                          <NeonTableCell>{u.email}</NeonTableCell>
                          <NeonTableCell>{u.risk_score}</NeonTableCell>
                          <NeonTableCell>
                            <div className="flex justify-end gap-1">
                              <NeonActionButton
                                accent="teal"
                                size="sm"
                                type="button"
                                onClick={() => openEditUser(u)}
                              >
                                <PencilIcon className="size-3.5" />
                              </NeonActionButton>
                              <NeonActionButton
                                accent="teal"
                                size="sm"
                                type="button"
                                onClick={() => void deleteUser(u.user_id)}
                              >
                                <Trash2Icon className="size-3.5" />
                              </NeonActionButton>
                            </div>
                          </NeonTableCell>
                        </NeonTableRow>
                      ))}
                    </NeonTableBody>
                  </NeonTable>
                </TsocHorizontalScroll>
              </NeonTabsContent>

              <NeonTabsContent value="assets" className="space-y-4">
                <div className="flex justify-end">
                  <NeonActionButton accent="teal" type="button" onClick={openCreateAsset}>
                    <PlusIcon className="size-4" />
                    Add asset
                  </NeonActionButton>
                </div>
                <TsocHorizontalScroll>
                  <NeonTable>
                    <NeonTableHeader>
                      <NeonTableRow>
                        <NeonTableHead>ID</NeonTableHead>
                        <NeonTableHead>Type</NeonTableHead>
                        <NeonTableHead>Host</NeonTableHead>
                        <NeonTableHead>IP</NeonTableHead>
                        <NeonTableHead>Crit.</NeonTableHead>
                        <NeonTableHead />
                      </NeonTableRow>
                    </NeonTableHeader>
                    <NeonTableBody>
                      {assets.map((a) => (
                        <NeonTableRow key={a.asset_id}>
                          <NeonTableCell className="font-mono text-xs">{a.asset_id}</NeonTableCell>
                          <NeonTableCell>{a.asset_type}</NeonTableCell>
                          <NeonTableCell>{a.hostname}</NeonTableCell>
                          <NeonTableCell>{a.ip}</NeonTableCell>
                          <NeonTableCell>{a.criticality}</NeonTableCell>
                          <NeonTableCell>
                            <div className="flex justify-end gap-1">
                              <NeonActionButton
                                accent="teal"
                                size="sm"
                                type="button"
                                onClick={() => openEditAsset(a)}
                              >
                                <PencilIcon className="size-3.5" />
                              </NeonActionButton>
                              <NeonActionButton
                                accent="teal"
                                size="sm"
                                type="button"
                                onClick={() => void deleteAsset(a.asset_id)}
                              >
                                <Trash2Icon className="size-3.5" />
                              </NeonActionButton>
                            </div>
                          </NeonTableCell>
                        </NeonTableRow>
                      ))}
                    </NeonTableBody>
                  </NeonTable>
                </TsocHorizontalScroll>
              </NeonTabsContent>
            </NeonTabsContents>
          </NeonTabs>
        </div>
      </NeonGlassCard>

      <Dialog open={userDialogOpen} onOpenChange={setUserDialogOpen}>
        <NeonDialogContent accent="teal" className="sm:max-w-md">
          <form onSubmit={saveUser} className="space-y-4">
            <NeonDialogHeaderWithIcon
              accent="teal"
              icon={
                isUserEdit ? (
                  <PencilIcon className="size-5 text-teal-400" />
                ) : (
                  <UserPlusIcon className="size-5 text-teal-400" />
                )
              }
              title={isUserEdit ? "Edit user" : "Add user"}
              description={
                isUserEdit
                  ? "Update display name, email, and risk score"
                  : "Create a new inventory user record"
              }
            />
            <NeonFieldGroup className="px-6">
              <NeonField>
                <NeonFieldLabel htmlFor="user_id">User ID</NeonFieldLabel>
                <NeonInput
                  id="user_id"
                  accent="teal"
                  placeholder="jdoe"
                  value={userForm.user_id}
                  onChange={(e) => setUserForm({ ...userForm, user_id: e.target.value })}
                  required
                  disabled={isUserEdit}
                />
              </NeonField>
              <NeonField>
                <NeonFieldLabel htmlFor="display_name">Display name</NeonFieldLabel>
                <NeonInput
                  id="display_name"
                  accent="teal"
                  placeholder="Jane Doe"
                  value={userForm.display_name}
                  onChange={(e) => setUserForm({ ...userForm, display_name: e.target.value })}
                />
              </NeonField>
              <NeonField>
                <NeonFieldLabel htmlFor="email">Email</NeonFieldLabel>
                <NeonInput
                  id="email"
                  accent="teal"
                  type="email"
                  placeholder="jane@corp.example"
                  value={userForm.email}
                  onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                />
              </NeonField>
              <NeonField>
                <NeonFieldLabel htmlFor="risk_score">Risk score (0–10)</NeonFieldLabel>
                <NeonInput
                  id="risk_score"
                  accent="teal"
                  type="number"
                  min={0}
                  max={10}
                  value={userForm.risk_score}
                  onChange={(e) => setUserForm({ ...userForm, risk_score: e.target.value })}
                />
              </NeonField>
            </NeonFieldGroup>
            <NeonDialogFooter className="px-6 pb-6">
              <NeonDialogFooterButton
                accent="teal"
                type="button"
                footerVariant="secondary"
                onClick={() => setUserDialogOpen(false)}
                disabled={saving}
              >
                Cancel
              </NeonDialogFooterButton>
              <NeonDialogFooterButton accent="teal" type="submit" disabled={saving}>
                {saving ? "Saving…" : isUserEdit ? "Save changes" : "Create user"}
              </NeonDialogFooterButton>
            </NeonDialogFooter>
          </form>
        </NeonDialogContent>
      </Dialog>

      <Dialog open={assetDialogOpen} onOpenChange={setAssetDialogOpen}>
        <NeonDialogContent accent="teal" className="sm:max-w-md">
          <form onSubmit={saveAsset} className="space-y-4">
            <NeonDialogHeaderWithIcon
              accent="teal"
              icon={
                isAssetEdit ? (
                  <PencilIcon className="size-5 text-teal-400" />
                ) : (
                  <ServerIcon className="size-5 text-teal-400" />
                )
              }
              title={isAssetEdit ? "Edit asset" : "Add asset"}
              description={
                isAssetEdit
                  ? "Update type, hostname, IP, criticality, and risk"
                  : "Create a new asset in inventory"
              }
            />
            <NeonFieldGroup className="px-6">
              <NeonField>
                <NeonFieldLabel htmlFor="asset_id">Asset ID</NeonFieldLabel>
                <NeonInput
                  id="asset_id"
                  accent="teal"
                  placeholder="web-prod-01"
                  value={assetForm.asset_id}
                  onChange={(e) => setAssetForm({ ...assetForm, asset_id: e.target.value })}
                  required
                  disabled={isAssetEdit}
                />
              </NeonField>
              <NeonField>
                <NeonFieldLabel htmlFor="asset_type">Type</NeonFieldLabel>
                <NeonInput
                  id="asset_type"
                  accent="teal"
                  placeholder="workstation"
                  value={assetForm.asset_type}
                  onChange={(e) => setAssetForm({ ...assetForm, asset_type: e.target.value })}
                />
              </NeonField>
              <NeonField>
                <NeonFieldLabel htmlFor="hostname">Hostname</NeonFieldLabel>
                <NeonInput
                  id="hostname"
                  accent="teal"
                  placeholder="web-prod-01.corp.example"
                  value={assetForm.hostname}
                  onChange={(e) => setAssetForm({ ...assetForm, hostname: e.target.value })}
                />
              </NeonField>
              <NeonField>
                <NeonFieldLabel htmlFor="ip">IP address</NeonFieldLabel>
                <NeonInput
                  id="ip"
                  accent="teal"
                  placeholder="10.0.0.10"
                  value={assetForm.ip}
                  onChange={(e) => setAssetForm({ ...assetForm, ip: e.target.value })}
                />
              </NeonField>
              <NeonField>
                <NeonFieldLabel htmlFor="asset_criticality">Criticality</NeonFieldLabel>
                <NeonInput
                  id="asset_criticality"
                  accent="teal"
                  placeholder="low | medium | high | critical"
                  value={assetForm.criticality}
                  onChange={(e) =>
                    setAssetForm({
                      ...assetForm,
                      criticality: e.target.value as AssetRecord["criticality"],
                    })
                  }
                />
              </NeonField>
              <NeonField>
                <NeonFieldLabel htmlFor="asset_risk">Risk score (0–10)</NeonFieldLabel>
                <NeonInput
                  id="asset_risk"
                  accent="teal"
                  type="number"
                  min={0}
                  max={10}
                  value={assetForm.risk_score}
                  onChange={(e) => setAssetForm({ ...assetForm, risk_score: e.target.value })}
                />
              </NeonField>
            </NeonFieldGroup>
            <NeonDialogFooter className="px-6 pb-6">
              <NeonDialogFooterButton
                accent="teal"
                type="button"
                footerVariant="secondary"
                onClick={() => setAssetDialogOpen(false)}
                disabled={saving}
              >
                Cancel
              </NeonDialogFooterButton>
              <NeonDialogFooterButton accent="teal" type="submit" disabled={saving}>
                {saving ? "Saving…" : isAssetEdit ? "Save changes" : "Create asset"}
              </NeonDialogFooterButton>
            </NeonDialogFooter>
          </form>
        </NeonDialogContent>
      </Dialog>
    </div>
  )
}
