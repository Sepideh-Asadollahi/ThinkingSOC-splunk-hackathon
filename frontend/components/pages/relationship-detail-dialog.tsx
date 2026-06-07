"use client"

import { Link2Icon, ServerIcon, UserIcon } from "lucide-react"

import {
  Dialog,
  NeonDialogContent,
  NeonDialogFooter,
  NeonDialogFooterButton,
  NeonDialogHeaderWithIcon,
} from "@/components/neon-glass"
import { TsocOverflowScroll } from "@/components/ui/tsoc-scroll"
import type { AssetRecord, RelationshipRecord, UserRecord } from "@/lib/api/types"

const USER_ENRICHMENT_KEYS: { alertField: string; inventoryField: keyof UserRecord }[] = [
  { alertField: "user", inventoryField: "user_id" },
  { alertField: "username", inventoryField: "user_id" },
  { alertField: "src_user", inventoryField: "user_id" },
  { alertField: "dest_user", inventoryField: "user_id" },
  { alertField: "account", inventoryField: "user_id" },
  { alertField: "user", inventoryField: "email" },
  { alertField: "username", inventoryField: "email" },
]

const ASSET_ENRICHMENT_KEYS: { alertField: string; inventoryField: keyof AssetRecord }[] = [
  { alertField: "host", inventoryField: "hostname" },
  { alertField: "hostname", inventoryField: "hostname" },
  { alertField: "dest", inventoryField: "hostname" },
  { alertField: "dest_host", inventoryField: "hostname" },
  { alertField: "src", inventoryField: "ip" },
  { alertField: "src_ip", inventoryField: "ip" },
  { alertField: "dest_ip", inventoryField: "ip" },
  { alertField: "ip", inventoryField: "ip" },
]

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—"
  return String(value)
}

function AttributeTable({
  title,
  icon,
  entries,
}: {
  title: string
  icon: React.ReactNode
  entries: { label: string; value: string }[]
}) {
  return (
    <section className="rounded-lg border border-white/10 bg-black/20 p-4">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-violet-200">
        {icon}
        {title}
      </h3>
      <dl className="grid gap-2 text-sm">
        {entries.map(({ label, value }) => (
          <div key={label} className="grid grid-cols-[minmax(7rem,9rem)_1fr] gap-2">
            <dt className="text-slate-400">{label}</dt>
            <dd className="break-all font-mono text-xs text-slate-100">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

function EnrichmentHints({
  title,
  icon,
  rows,
}: {
  title: string
  icon: React.ReactNode
  rows: { alertField: string; inventoryField: string; exampleValue: string }[]
}) {
  if (rows.length === 0) return null
  return (
    <section className="rounded-lg border border-violet-500/20 bg-violet-950/20 p-4">
      <h3 className="mb-2 flex items-center gap-2 text-sm font-medium text-violet-200">
        {icon}
        {title}
      </h3>
      <p className="mb-3 text-xs text-slate-400">
        When an alert matches only the user or only the asset, enrichment uses this link to fill
        the other side. These alert fields can match the inventory values below.
      </p>
      <ul className="space-y-2 text-xs">
        {rows.map((row) => (
          <li
            key={`${row.alertField}-${row.inventoryField}`}
            className="rounded border border-white/5 bg-black/30 px-3 py-2"
          >
            <span className="text-slate-300">
              alert.<span className="font-mono text-violet-300">{row.alertField}</span>
            </span>
            <span className="mx-2 text-slate-500">→</span>
            <span className="text-slate-300">
              inventory.<span className="font-mono text-teal-300">{row.inventoryField}</span>
            </span>
            <span className="mt-1 block font-mono text-slate-400">= {row.exampleValue}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

export type RelationshipDetailDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  relationship: RelationshipRecord | null
  user: UserRecord | null | undefined
  asset: AssetRecord | null | undefined
}

export function RelationshipDetailDialog({
  open,
  onOpenChange,
  relationship,
  user,
  asset,
}: RelationshipDetailDialogProps) {
  if (!relationship) return null

  const userHints = user
    ? USER_ENRICHMENT_KEYS.map(({ alertField, inventoryField }) => ({
        alertField,
        inventoryField,
        exampleValue: formatValue(user[inventoryField]),
      })).filter((r) => r.exampleValue !== "—")
    : []

  const assetHints = asset
    ? ASSET_ENRICHMENT_KEYS.map(({ alertField, inventoryField }) => ({
        alertField,
        inventoryField,
        exampleValue: formatValue(asset[inventoryField]),
      })).filter((r) => r.exampleValue !== "—")
    : []

  const uniqueAssetHints = assetHints.filter(
    (row, i, arr) =>
      arr.findIndex(
        (x) => x.inventoryField === row.inventoryField && x.exampleValue === row.exampleValue
      ) === i
  )

  const uniqueUserHints = userHints.filter(
    (row, i, arr) =>
      arr.findIndex(
        (x) => x.inventoryField === row.inventoryField && x.exampleValue === row.exampleValue
      ) === i
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <NeonDialogContent accent="violet" className="flex max-h-[90vh] flex-col sm:max-w-2xl">
        <NeonDialogHeaderWithIcon
          accent="violet"
          icon={<Link2Icon className="size-5 text-violet-400" />}
          title="Linked inventory attributes"
          description={relationship.relationship_id}
        />
        <TsocOverflowScroll className="max-h-[min(60vh,640px)] space-y-4 px-6 pr-4">
          <AttributeTable
            title="Relationship"
            icon={<Link2Icon className="size-4 text-violet-400" />}
            entries={[
              { label: "relationship_id", value: relationship.relationship_id },
              { label: "user_id", value: relationship.user_id },
              { label: "asset_id", value: relationship.asset_id },
              { label: "description", value: formatValue(relationship.description) },
            ]}
          />

          {user ? (
            <>
              <AttributeTable
                title="User (linked)"
                icon={<UserIcon className="size-4 text-violet-400" />}
                entries={[
                  { label: "user_id", value: user.user_id },
                  { label: "display_name", value: formatValue(user.display_name) },
                  { label: "email", value: formatValue(user.email) },
                  { label: "department", value: formatValue(user.department) },
                  { label: "risk_score", value: formatValue(user.risk_score) },
                  { label: "description", value: formatValue(user.description) },
                ]}
              />
              <EnrichmentHints
                title="User enrichment keys"
                icon={<UserIcon className="size-4 text-violet-400" />}
                rows={uniqueUserHints}
              />
            </>
          ) : (
            <p className="rounded-lg border border-amber-500/30 bg-amber-950/30 px-4 py-3 text-sm text-amber-100">
              User <span className="font-mono">{relationship.user_id}</span> not found in
              inventory. Refresh or fix the link.
            </p>
          )}

          {asset ? (
            <>
              <AttributeTable
                title="Asset (linked)"
                icon={<ServerIcon className="size-4 text-violet-400" />}
                entries={[
                  { label: "asset_id", value: asset.asset_id },
                  { label: "asset_type", value: asset.asset_type },
                  { label: "hostname", value: formatValue(asset.hostname) },
                  { label: "fqdn", value: formatValue(asset.fqdn) },
                  { label: "ip", value: formatValue(asset.ip) },
                  { label: "owner", value: formatValue(asset.owner) },
                  { label: "criticality", value: asset.criticality },
                  { label: "risk_score", value: formatValue(asset.risk_score) },
                  { label: "description", value: formatValue(asset.description) },
                ]}
              />
              <EnrichmentHints
                title="Asset enrichment keys"
                icon={<ServerIcon className="size-4 text-violet-400" />}
                rows={uniqueAssetHints}
              />
            </>
          ) : (
            <p className="rounded-lg border border-amber-500/30 bg-amber-950/30 px-4 py-3 text-sm text-amber-100">
              Asset <span className="font-mono">{relationship.asset_id}</span> not found in
              inventory. Refresh or fix the link.
            </p>
          )}
        </TsocOverflowScroll>
        <NeonDialogFooter className="shrink-0 px-6 pb-6 pt-2">
          <NeonDialogFooterButton
            accent="violet"
            type="button"
            onClick={() => onOpenChange(false)}
          >
            Close
          </NeonDialogFooterButton>
        </NeonDialogFooter>
      </NeonDialogContent>
    </Dialog>
  )
}
