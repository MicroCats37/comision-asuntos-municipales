/**
 * Safe empty hook for Especialidad options in DelegadosFiltroModal.
 *
 * TODO: Replace with real endpoint hook when backend exposes
 * GET /delegados/especialidades (or similar) that returns EspecialidadOption[].
 *
 * NOTE: This is different from useEspecialidadesRevision which returns
 * EspecialidadRevisionOption[]. The perfil ingeniero especialidad has a
 * different shape (id, codigo, nombre) matching Especialidad from tipos.
 *
 * Current state: returns empty array so the Select UI can be wired now
 * and populated later without changing the component interface.
 *
 * Return shape matches other option hooks (e.g., useMunicipalidades):
 *   { data: Especialidad[], isLoading: false, isError: false, refetch }
 */
import type { Especialidad } from "../types/delegados.types";

export function useEspecialidadesOptions(): {
  data: Especialidad[];
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
