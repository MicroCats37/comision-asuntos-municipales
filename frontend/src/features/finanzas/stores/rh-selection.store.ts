"use client";

import { create } from "zustand";
import type {
  CandidataDelegado,
  RHDelegadoCotizarItemIn,
} from "../schemas/rh-delegado-mensual.schema";
import type {
  InspectorCandidataItem,
  RHInspectorCotizarItemIn,
} from "../schemas/rh-inspector-mensual.schema";

// ── Selection item types ───────────────────────────────────────────────────────

/**
 * Selection entry for an inspector candidate.
 * `cotizarItem` fields are used to build the cotizar payload.
 * `candidate` stores the full row for display in the selected-items area.
 */
export interface InspectorSelectionEntry {
  cotizarItem: Pick<
    RHInspectorCotizarItemIn,
    "cantidad_visitas" | "periodo" | "mes"
  >;
  candidate: InspectorCandidataItem;
}

/**
 * Selection entry for a delegado candidate.
 * `cotizarItem` fields are used to build the cotizar payload.
 * `candidate` stores the full row for display in the selected-items area.
 */
export interface DelegadoSelectionEntry {
  cotizarItem: Pick<
    RHDelegadoCotizarItemIn,
    | "numero_rh"
    | "periodo"
    | "mes"
    | "dictamen_revision"
    | "fecha_presentacion"
    | "fecha_revision"
  >;
  candidate: CandidataDelegado;
}

// ── Store shape ────────────────────────────────────────────────────────────────

export interface RHSelectionState {
  /** selectionsByFlow → selectionsById */
  selections: Record<
    string,
    Record<string, InspectorSelectionEntry | DelegadoSelectionEntry>
  >;

  // ── Mutations ──────────────────────────────────────────────────────────────

  /**
   * Add or overwrite a selection for a given flow key + candidate id.
   *
   * For inspector: id = `liquidacion_categoria_visitas_id`, entry = InspectorSelectionEntry
   * For delegado:  id = `liquidacion_general_id`,         entry = DelegadoSelectionEntry
   */
  addSelection: (
    flowKey: string,
    id: string,
    entry: InspectorSelectionEntry | DelegadoSelectionEntry,
  ) => void;

  /**
   * Remove a single selection by flow key + candidate id.
   */
  removeSelection: (flowKey: string, id: string) => void;

  /**
   * If id is already selected → remove it.
   * If id is not selected    → add it with the provided entry.
   */
  toggleSelection: (
    flowKey: string,
    id: string,
    entry: InspectorSelectionEntry | DelegadoSelectionEntry,
  ) => void;

  /**
   * Clear all selections for a given flow key.
   * Call this when the modal closes to avoid stale state on re-open.
   */
  clearSelections: (flowKey: string) => void;

  // ── Selectors ─────────────────────────────────────────────────────────────

  /** True iff the given candidate id is selected under the given flow key. */
  isSelected: (flowKey: string, id: string) => boolean;

  /** All selected candidate ids under the given flow key. */
  getSelectedIds: (flowKey: string) => string[];

  /** All selected entries under the given flow key. */
  getSelectedItems: (
    flowKey: string,
  ) => (InspectorSelectionEntry | DelegadoSelectionEntry)[];

  /** Count of selected items under the given flow key. */
  getSelectedCount: (flowKey: string) => number;
}

export type RHSelectionStore = RHSelectionState;

// ── Store ─────────────────────────────────────────────────────────────────────

export const useRHSelectionStore = create<RHSelectionStore>()((set, get) => ({
  selections: {},

  // ── Mutations ─────────────────────────────────────────────────────────────

  addSelection: (flowKey, id, entry) =>
    set((state) => ({
      selections: {
        ...state.selections,
        [flowKey]: {
          ...(state.selections[flowKey] ?? {}),
          [id]: entry,
        },
      },
    })),

  removeSelection: (flowKey, id) =>
    set((state) => {
      const flowSelections = state.selections[flowKey];
      if (!flowSelections) return state;
      const next = { ...flowSelections };
      delete next[id];
      return {
        selections: {
          ...state.selections,
          [flowKey]: next,
        },
      };
    }),

  toggleSelection: (flowKey, id, entry) => {
    const { isSelected, addSelection, removeSelection } = get();
    if (isSelected(flowKey, id)) {
      removeSelection(flowKey, id);
    } else {
      addSelection(flowKey, id, entry);
    }
  },

  clearSelections: (flowKey) =>
    set((state) => {
      const next = { ...state.selections };
      delete next[flowKey];
      return { selections: next };
    }),

  // ── Selectors ─────────────────────────────────────────────────────────────

  isSelected: (flowKey, id) => {
    const flowSelections = get().selections[flowKey];
    return flowSelections != null && id in flowSelections;
  },

  getSelectedIds: (flowKey) => {
    const flowSelections = get().selections[flowKey];
    return flowSelections ? Object.keys(flowSelections) : [];
  },

  getSelectedItems: (flowKey) => {
    const flowSelections = get().selections[flowKey];
    return flowSelections ? Object.values(flowSelections) : [];
  },

  getSelectedCount: (flowKey) => {
    const flowSelections = get().selections[flowKey];
    return flowSelections ? Object.keys(flowSelections).length : 0;
  },
}));

// ── Stable flow-key helpers ───────────────────────────────────────────────────

/**
 * Build the stable flow key for an inspector RH session.
 * @param cip - Inspector CIP
 */
export function buildInspectorFlowKey(cip: string): string {
  return `inspector-${cip}`;
}

/**
 * Build the stable flow key for a delegado RH session.
 * Prefers delegado_operacion_id when available; falls back to a composite key.
 *
 * @param cip             - Delegado CIP
 * @param opts            - Delegado operation identifier options
 * @param opts.delegado_operacion_id - SmartField-selected DelegadoOperacion UUID
 * @param opts.municipalidad_id      - Legacy filter: municipalidad UUID
 * @param opts.tipo_liquidacion_id   - Legacy filter: tipo_liquidacion UUID
 * @param opts.tipo_delegado         - Legacy filter: TITULAR | ALTERNO
 */
export function buildDelegadoFlowKey(
  cip: string,
  opts: {
    delegado_operacion_id?: string;
    municipalidad_id?: string;
    tipo_liquidacion_id?: string;
    tipo_delegado?: string;
  },
): string {
  if (opts.delegado_operacion_id) {
    return `delegado-${opts.delegado_operacion_id}`;
  }
  // Legacy filter path — include all filter dimensions to isolate flows
  const parts = [
    cip,
    opts.municipalidad_id ?? "none",
    opts.tipo_liquidacion_id ?? "none",
    opts.tipo_delegado ?? "none",
  ];
  return `delegado-${parts.join("-")}`;
}
