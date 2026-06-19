/**
 * Hooks para consulta externa SUNAT/RENIEC.
 */
import { useMutation } from "@tanstack/react-query";
import { notify } from "@/errors";
import { consultarSunat, consultarReniec } from "../services/consulta-externa.service";
import type { InstitucionSunatResponse, PersonaReniecResponse } from "../types/entidad";

/**
 * Hook para consultar datos de institución por RUC (SUNAT).
 */
export function useSunatLookup() {
  return useMutation<
    InstitucionSunatResponse | null,
    Error,
    string
  >({
    mutationFn: async (ruc: string) => {
      return consultarSunat(ruc);
    },
    onSuccess: (data) => {
      if (!data) {
        notify.error("No se encontraron datos para este RUC");
      }
    },
    onError: (error: Error) => {
      notify.error(error.message || "Error al consultar SUNAT");
    },
  });
}

/**
 * Hook para consultar datos de persona por DNI (RENIEC).
 */
export function useReniecLookup() {
  return useMutation<
    PersonaReniecResponse | null,
    Error,
    string
  >({
    mutationFn: async (dni: string) => {
      return consultarReniec(dni);
    },
    onSuccess: (data) => {
      if (!data) {
        notify.error("No se encontraron datos para este DNI");
      }
    },
    onError: (error: Error) => {
      notify.error(error.message || "Error al consultar RENIEC");
    },
  });
}
