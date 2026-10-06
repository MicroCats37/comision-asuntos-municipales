"use client";

import { create } from "zustand";

/**
 * Flat UI store for Edificaciones list view.
 * State: pagination, search, and form modal control.
 * NO steppers — this is purely list-level UI state.
 */
interface EdificacionesUIState {
  page: number;
  pageSize: number;
  searchQuery: string;
  isFormModalOpen: boolean;
  selectedItemId: string | null;
}

interface EdificacionesUIActions {
  setPage: (page: number) => void;
  setSearchQuery: (query: string) => void;
  openFormModal: (id?: string) => void;
  closeFormModal: () => void;
}

export type EdificacionesUIStore = EdificacionesUIState &
  EdificacionesUIActions;

const initialState: EdificacionesUIState = {
  page: 1,
  pageSize: 10,
  searchQuery: "",
  isFormModalOpen: false,
  selectedItemId: null,
};

export const useEdificacionesUIStore = create<EdificacionesUIStore>()(
  (set) => ({
    ...initialState,

    setPage: (page) => set({ page }),

    setSearchQuery: (searchQuery) => set({ searchQuery, page: 1 }),

    openFormModal: (id) =>
      set({ isFormModalOpen: true, selectedItemId: id ?? null }),

    closeFormModal: () => set({ isFormModalOpen: false, selectedItemId: null }),
  }),
);
