/**
 * Safe empty hook for Capitulo options in DelegadosFiltroModal.
 *
 * TODO: Replace with real endpoint hook when backend exposes
 * GET /delegados/capitulos (or similar) that returns CapituloOption[].
 *
 * Current state: returns empty array so the Select UI can be wired now
 * and populated later without changing the component interface.
 *
 * Return shape matches other option hooks (e.g., useMunicipalidades):
 *   { data: Capitulo[], isLoading: false, isError: false, refetch }
 */
import type { Capitulo } from "../types/delegados.types";

export function useCapitulosOptions(): {
  data: Capitulo[];
  isLoading: false;
  isError: false;
  refetch: () => void;
} {
  // Safe empty: no backend endpoint yet
  return {
    data: [],
    isLoading: false,
    isError: false,
    refetch: () => {
      // no-op until real endpoint exists
    },
  };
}
