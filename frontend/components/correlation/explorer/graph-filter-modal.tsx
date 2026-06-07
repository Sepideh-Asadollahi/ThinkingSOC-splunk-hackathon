"use client"

import { useState } from "react"
import { FilterIcon, RotateCcwIcon } from "lucide-react"

import {
  useGraphDispatch,
  useGraphState,
} from "@/components/correlation/explorer/graph-context"
import { useFilteredGraphView } from "@/hooks/correlation/use-filtered-graph"
import {
  Dialog,
  NeonActionButton,
  NeonBadge,
  NeonDialogContent,
  NeonDialogFooter,
  NeonDialogFooterButton,
  NeonDialogHeaderWithIcon,
} from "@/components/neon-glass"
import {
  DEFAULT_GRAPH_VIEW_FILTERS,
  discoverAvailableKinds,
  GRAPH_EDGE_FILTER_OPTIONS,
  GRAPH_NODE_FILTER_OPTIONS,
  isDefaultGraphViewFilters,
  toggleFilterKind,
  type GraphEdgeKind,
  type GraphNodeKind,
} from "@/lib/api/graph/graph-filters"
import { cn } from "@/lib/utils"

function FilterCheckbox({
  id,
  label,
  hint,
  checked,
  disabled,
  onChange,
}: {
  id: string
  label: string
  hint: string
  checked: boolean
  disabled?: boolean
  onChange: (checked: boolean) => void
}) {
  return (
    <label
      htmlFor={id}
      className={cn(
        "flex cursor-pointer items-start gap-2 rounded-md border px-2.5 py-2 text-xs transition-colors",
        checked
          ? "border-teal-500/40 bg-teal-500/10 text-teal-100"
          : "border-white/10 bg-black/20 text-slate-400 hover:border-white/20",
        disabled && "cursor-not-allowed opacity-40",
      )}
      title={hint}
    >
      <input
        id={id}
        type="checkbox"
        className="mt-0.5 accent-teal-400"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span>{label}</span>
    </label>
  )
}

export function GraphFilterModal({ disabled = false }: { disabled?: boolean }) {
  const [open, setOpen] = useState(false)
  const dispatch = useGraphDispatch()
  const { viewFilters } = useGraphState()
  const { topology, sourceTopology } = useFilteredGraphView()
  const available = discoverAvailableKinds(sourceTopology)
  const isDefault = isDefaultGraphViewFilters(viewFilters)

  const setNodeKind = (kind: GraphNodeKind, enabled: boolean) => {
    if (
      !enabled &&
      viewFilters.nodeKinds.length === 1 &&
      viewFilters.nodeKinds[0] === kind
    ) {
      return
    }
    dispatch({
      type: "SET_VIEW_FILTERS",
      payload: {
        ...viewFilters,
        nodeKinds: toggleFilterKind(viewFilters.nodeKinds, kind, enabled),
      },
    })
  }

  const setEdgeKind = (kind: GraphEdgeKind, enabled: boolean) => {
    if (
      !enabled &&
      viewFilters.edgeKinds.length === 1 &&
      viewFilters.edgeKinds[0] === kind
    ) {
      return
    }
    dispatch({
      type: "SET_VIEW_FILTERS",
      payload: {
        ...viewFilters,
        edgeKinds: toggleFilterKind(viewFilters.edgeKinds, kind, enabled),
      },
    })
  }

  const resetFilters = () => {
    dispatch({ type: "SET_VIEW_FILTERS", payload: DEFAULT_GRAPH_VIEW_FILTERS })
  }

  return (
    <>
      <NeonActionButton
        accent="teal"
        size="sm"
        className="border-white/15 text-slate-300"
        disabled={disabled}
        onClick={() => setOpen(true)}
      >
        <FilterIcon className="size-4" />
        Filters
        {!isDefault ? (
          <NeonBadge className="ml-1 border-amber-500/30 bg-amber-500/10 px-1.5 py-0 text-[10px] text-amber-200">
            Custom
          </NeonBadge>
        ) : null}
      </NeonActionButton>

      <Dialog open={open} onOpenChange={setOpen}>
        <NeonDialogContent className="max-w-xl" accent="teal">
          <NeonDialogHeaderWithIcon
            icon={<FilterIcon className="size-5 text-teal-400" />}
            title="Graph filters"
            description="Choose which nodes and links appear on the correlation graph."
          />

          <div className="space-y-4 py-2">
            <p className="text-xs text-slate-400">
              Visible now: {topology?.nodes.length ?? 0} nodes ·{" "}
              {topology?.edges.length ?? 0} links
            </p>

            <section>
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                Node types
              </p>
              <div className="flex flex-wrap gap-2">
                {GRAPH_NODE_FILTER_OPTIONS.map((opt) => (
                  <FilterCheckbox
                    key={opt.id}
                    id={`modal-node-${opt.id}`}
                    label={opt.label}
                    hint={opt.hint}
                    checked={viewFilters.nodeKinds.includes(opt.id)}
                    disabled={
                      sourceTopology != null &&
                      !available.nodeKinds.includes(opt.id)
                    }
                    onChange={(checked) => setNodeKind(opt.id, checked)}
                  />
                ))}
              </div>
            </section>

            <section>
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                Link types
              </p>
              <div className="flex flex-wrap gap-2">
                {GRAPH_EDGE_FILTER_OPTIONS.map((opt) => (
                  <FilterCheckbox
                    key={opt.id}
                    id={`modal-edge-${opt.id}`}
                    label={opt.label}
                    hint={opt.hint}
                    checked={viewFilters.edgeKinds.includes(opt.id)}
                    disabled={
                      sourceTopology != null &&
                      !available.edgeKinds.includes(opt.id)
                    }
                    onChange={(checked) => setEdgeKind(opt.id, checked)}
                  />
                ))}
              </div>
            </section>

            <p className="text-[11px] text-slate-500">
              Default:{" "}
              <span className="text-slate-400">Alert → Alert (CAUSED)</span>.
              Disabled options are not present in the current finding graph.
            </p>
          </div>

          <NeonDialogFooter>
            {!isDefault ? (
              <NeonDialogFooterButton
                footerVariant="secondary"
                onClick={resetFilters}
              >
                <RotateCcwIcon className="size-4" />
                Reset default
              </NeonDialogFooterButton>
            ) : null}
            <NeonDialogFooterButton onClick={() => setOpen(false)}>
              Done
            </NeonDialogFooterButton>
          </NeonDialogFooter>
        </NeonDialogContent>
      </Dialog>
    </>
  )
}
