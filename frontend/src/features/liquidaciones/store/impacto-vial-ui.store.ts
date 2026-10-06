import { create } from "zustand";

interface ImpactoVialUIState {
  page: number;
  pageSize: number;
  searchQuery: string;
  isFormModalOpen: boolean;
  selectedItemId: string | null;
  setPage: (page: number) => void;
  setPageSize: (pageSize: number) => void;
  setSearchQuery: (query: string) => void;
  openFormModal: (id?: string) => void;
  closeFormModal: () => void;
  setSelectedItemId: (id: string | null) => void;
}

export const useImpactoVialUIStore = create<ImpactoVialUIState>((set) => ({
  page: 1,
  pageSize: 10,
  searchQuery: "",
  isFormModalOpen: false,
  selectedItemId: null,
  setPage: (page) => set({ page }),
  setPageSize: (pageSize) => set({ pageSize }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  openFormModal: (id?: string) =>
    set({ isFormModalOpen: true, selectedItemId: id || null }),
  closeFormModal: () => set({ isFormModalOpen: false, selectedItemId: null }),
  setSelectedItemId: (selectedItemId) => set({ selectedItemId }),
}));
