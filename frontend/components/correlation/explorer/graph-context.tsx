"use client"

import {
  createContext,
  useContext,
  useReducer,
  type Dispatch,
  type ReactNode,
} from "react"

import {
  DEFAULT_GRAPH_VIEW_FILTERS,
  type GraphViewFilters,
} from "@/lib/api/graph/graph-filters"
import type {
  GraphFindingDetails,
  GraphNode,
  GraphResponse,
  GraphTreeNode,
} from "@/lib/api/graph/types"

export type GraphState = {
  loading: boolean
  error: string | null
  sourceTopology: GraphResponse | null
  sourceAttackTrees: GraphTreeNode[]
  viewFilters: GraphViewFilters
  notifications: string[] | null
  statusMessage: string | null
  finding: GraphFindingDetails | null
  selectedNodeId: string | null
}

type GraphAction =
  | { type: "SET_LOADING"; payload: boolean }
  | { type: "SET_ERROR"; payload: string | null }
  | {
      type: "SET_FULL_DATA"
      payload: {
        topology: GraphResponse
        attackTrees?: GraphTreeNode[]
        notifications?: string[] | null
        message?: string | null
      }
    }
  | { type: "SET_FINDING_METADATA"; payload: GraphFindingDetails }
  | { type: "SET_VIEW_FILTERS"; payload: GraphViewFilters }
  | { type: "SELECT_NODE"; payload: string | null }
  | { type: "RESET" }

const initialState: GraphState = {
  loading: false,
  error: null,
  sourceTopology: null,
  sourceAttackTrees: [],
  viewFilters: DEFAULT_GRAPH_VIEW_FILTERS,
  notifications: null,
  statusMessage: null,
  finding: null,
  selectedNodeId: null,
}

function graphReducer(state: GraphState, action: GraphAction): GraphState {
  switch (action.type) {
    case "SET_LOADING":
      return { ...state, loading: action.payload }
    case "SET_ERROR":
      return { ...state, error: action.payload, loading: false }
    case "SET_FULL_DATA": {
      const { topology, attackTrees, notifications, message } = action.payload
      return {
        ...state,
        sourceTopology: topology,
        sourceAttackTrees: attackTrees ?? [],
        viewFilters: DEFAULT_GRAPH_VIEW_FILTERS,
        notifications: notifications ?? null,
        statusMessage: message ?? topology.message ?? null,
        error: null,
        selectedNodeId: null,
      }
    }
    case "SET_FINDING_METADATA":
      return { ...state, finding: action.payload }
    case "SET_VIEW_FILTERS":
      return { ...state, viewFilters: action.payload, selectedNodeId: null }
    case "SELECT_NODE":
      return { ...state, selectedNodeId: action.payload }
    case "RESET":
      return initialState
    default:
      return state
  }
}

const GraphStateContext = createContext<GraphState | null>(null)
const GraphDispatchContext = createContext<Dispatch<GraphAction> | null>(null)

export function GraphProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(graphReducer, initialState)
  return (
    <GraphStateContext.Provider value={state}>
      <GraphDispatchContext.Provider value={dispatch}>
        {children}
      </GraphDispatchContext.Provider>
    </GraphStateContext.Provider>
  )
}

export function useGraphState(): GraphState {
  const ctx = useContext(GraphStateContext)
  if (!ctx) throw new Error("useGraphState must be used within GraphProvider")
  return ctx
}

export function useGraphDispatch(): Dispatch<GraphAction> {
  const ctx = useContext(GraphDispatchContext)
  if (!ctx) throw new Error("useGraphDispatch must be used within GraphProvider")
  return ctx
}

/** @deprecated Use selectedNodeFromFilteredView from use-filtered-graph */
export function selectedNodeFromState(state: GraphState): GraphNode | null {
  if (!state.sourceTopology || !state.selectedNodeId) return null
  return (
    state.sourceTopology.nodes.find((n) => n.id === state.selectedNodeId) ??
    null
  )
}
