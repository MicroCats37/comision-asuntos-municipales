/**
 * Hooks para consulta externa SUNAT/RENIEC unificado.
 *
 * Hook único: useDocumentoLookup — auto-detecta DNI (8) vs RUC (11).
 */
import { useMutation } from "@tanstack/react-query";
import { notify } from "@/errors";
import { consultarDocumento } from "../services/consulta-externa.service";

export interface DocumentoConsultaData {
  tipo_documento: string;
  numero_documento: string;
  razon_social: string;
}

/**
 * Hook para consultar datos de documento por número (DNI o RUC).
 * Auto-detecta: 8 dígitos → DNI, 11 dígitos → RUC.
 */
export function useDocumentoLookup() {
  return useMutation<DocumentoConsultaData | null, Error, string>({
    mutationFn: async (documento: string) => {
      return consultarDocumento(documento);
    },
    onSuccess: (data) => {
      if (!data) {
        notify.error("No se encontraron datos para este documento");
      }
    },
    onError: (error: Error) => {
      notify.error(error.message || "Error al consultar documento");
    },
  });
}

/**
 * Hook para consultar datos de institución por RUC (deprecated).
 */
export function useSunatLookup() {
  return useMutation<DocumentoConsultaData | null, Error, string>({
    mutationFn: async (ruc: string) => {
      return consultarDocumento(ruc);
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
 * Hook para consultar datos de persona por DNI (deprecated).
 */
export function useReniecLookup() {
  return useMutation<DocumentoConsultaData | null, Error, string>({
    mutationFn: async (dni: string) => {
      return consultarDocumento(dni);
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
