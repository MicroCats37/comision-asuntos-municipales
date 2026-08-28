/**
 * Hook para consultar un ingeniero habilitado por CIP.
 *
 * Endpoint: GET /ingenieros/habilitados/{cip}
 * Usa el error-handler central (getErrorMessage) para normalizar errores
 * de red/HTTP. Sigue el patrón estándar del proyecto (como useApiUpdate/useConsultaExterna).
 */
import { useMutation } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import { getErrorMessage, notify } from "@/errors";
import {
  consultarIngeniero,
  type IngenieroHabilitado,
} from "../services/consultar-ingeniero.service";

/**
 * Hook para consultar los datos de un ingeniero por su número de CIP.
 */
export function useConsultarIngeniero() {
  return useMutation<IngenieroHabilitado | null, AxiosError, string>({
    mutationFn: async (cip: string) => {
      return consultarIngeniero(cip);
    },
    onSuccess: (data) => {
      if (!data) {
        notify.error("No se encontraron datos para este CIP");
      }
    },
    onError: (error: AxiosError) => {
      notify.error(getErrorMessage(error) || "Error al consultar el ingeniero");
    },
  });
}
