/**
 * Hook para consulta externa de documentos (DNI o RUC).
 *
 * Servicio externo genérico — NO es SUNAT ni RENIEC.
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
