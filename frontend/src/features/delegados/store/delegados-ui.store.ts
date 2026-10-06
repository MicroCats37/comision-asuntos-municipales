"use client";

import { create } from "zustand";

/**
 * UI Store for Delegados list view.
 * State: pagination and search.
 */
interface DelegadosUIState {
  page: number;
  pageSize: number;
  searchQuery: string;
}

interface DelegadosUIActions {
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  setSearchQuery: (query: string) => void;
}

export type DelegadosUIStore = DelegadosUIState & DelegadosUIActions;

const initialState: DelegadosUIState = {
  page: 1,
  pageSize: 10,
  searchQuery: "",
};

export const useDelegadosUIStore = create<DelegadosUIStore>()((set) => ({
  ...initialState,

  setPage: (page) => set({ page }),

  setPageSize: (pageSize) => set({ pageSize, page: 1 }),

  setSearchQuery: (searchQuery) => set({ searchQuery, page: 1 }),
}));
