"use client";

import { create } from "zustand";

/**
 * UI Store for Inspectores list view.
 * State: pagination and search.
 */
interface InspectoresUIState {
  page: number;
  pageSize: number;
  searchQuery: string;
}

interface InspectoresUIActions {
  setPage: (page: number) => void;
  setSearchQuery: (query: string) => void;
}

export type InspectoresUIStore = InspectoresUIState & InspectoresUIActions;

const initialState: InspectoresUIState = {
  page: 1,
  pageSize: 10,
  searchQuery: "",
};

export const useInspectoresUIStore = create<InspectoresUIStore>()((set) => ({
  ...initialState,

  setPage: (page) => set({ page }),

  setSearchQuery: (searchQuery) => set({ searchQuery, page: 1 }),
}));
