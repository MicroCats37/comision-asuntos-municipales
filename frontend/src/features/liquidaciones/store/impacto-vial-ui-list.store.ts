"use client";

import { create } from "zustand";

/**
 * Flat UI store for Impacto Vial list view.
 * State: pagination, search, and form modal control.
 * NO steppers — this is purely list-level UI state.
 */
interface ImpactoVialUIState {
  page: number;
  pageSize: number;
  searchQuery: string;
  isFormModalOpen: boolean;
  selectedItemId: string | null;
}

interface ImpactoVialUIActions {
  setPage: (page: number) => void;
  setSearchQuery: (query: string) => void;
  openFormModal: (id?: string) => void;
  closeFormModal: () => void;
}

export type ImpactoVialUIStore = ImpactoVialUIState & ImpactoVialUIActions;

const initialState: ImpactoVialUIState = {
  page: 1,
  pageSize: 10,
  searchQuery: "",
  isFormModalOpen: false,
  selectedItemId: null,
};

export const useImpactoVialUIStore = create<ImpactoVialUIStore>()((set) => ({
  ...initialState,

  setPage: (page) => set({ page }),

  setSearchQuery: (searchQuery) => set({ searchQuery, page: 1 }),

  openFormModal: (id) =>
    set({ isFormModalOpen: true, selectedItemId: id ?? null }),

  closeFormModal: () => set({ isFormModalOpen: false, selectedItemId: null }),
}));
