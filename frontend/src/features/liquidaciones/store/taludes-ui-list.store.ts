"use client";

import { create } from "zustand";

/**
 * Flat UI store for Taludes list view.
 * State: pagination, search, and form modal control.
 * NO steppers — this is purely list-level UI state.
 */
interface TaludesUIState {
  page: number;
  pageSize: number;
  searchQuery: string;
  isFormModalOpen: boolean;
  selectedItemId: string | null;
}

interface TaludesUIActions {
  setPage: (page: number) => void;
  setSearchQuery: (query: string) => void;
  openFormModal: (id?: string) => void;
  closeFormModal: () => void;
}

export type TaludesUIStore = TaludesUIState & TaludesUIActions;

const initialState: TaludesUIState = {
  page: 1,
  pageSize: 10,
  searchQuery: "",
  isFormModalOpen: false,
  selectedItemId: null,
};

export const useTaludesUIStore = create<TaludesUIStore>()((set) => ({
  ...initialState,

  setPage: (page) => set({ page }),

  setSearchQuery: (searchQuery) => set({ searchQuery, page: 1 }),

  openFormModal: (id) =>
    set({ isFormModalOpen: true, selectedItemId: id ?? null }),

  closeFormModal: () => set({ isFormModalOpen: false, selectedItemId: null }),
}));
