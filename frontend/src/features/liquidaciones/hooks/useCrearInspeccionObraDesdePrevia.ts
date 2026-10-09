/**
 * Hook para crear una Inspección de Obra PRIMERA-REVISIÓN desde una liquidación previa.
 *
 * Endpoint: POST /liquidaciones/inspeccion-obra/nueva-liquidacion
 * Payload:
 * {
 *   liquidacion_previa_id: uuid,
 *   liquidacion_especifica: {
 *     datos: { cantidad_visitas: number, categoria: string },
 *     tarifa: { tarifa_visitas_id: string },
 *     inspector_operacion_id: string,
 *   },
 *   contacto?: { nombres, apellidos, dni, cargo, telefono, celular, email },
 * }
 * Se hereda de la previa: proyecto, municipalidad, entidad, expediente, observacion, retencion.
 *
 * Usa useLiquidacionesCreateMutation (cache manual reactivo).
 */
import { useMemo } from "react";
import type { NuevaRevisionInspeccionObraFormData } from "../schemas/liquidacion-nueva-revision-io.schema";
import { useLiquidacionesCreateMutation } from "./cache";

const BASE_URL = "/liquidaciones/inspeccion-obra";
const LIST_KEY = ["liquidaciones", "inspeccion-obra"] as const;

export function useCrearInspeccionObraDesdePrevia() {
  const mutation = useLiquidacionesCreateMutation<{
    liquidacion_previa_id: string;
    liquidacion_especifica: {
      datos: { cantidad_visitas: number; categoria: string };
      tarifa: { tarifa_visitas_id: string };
      inspector_operacion_id: string;
    };
    contacto?: {
      nombres: string;
      apellidos?: string;
      dni?: string;
      cargo?: string;
      telefono?: string;
      celular?: string;
      email?: string;
    };
  }>({
    tipoQueryKey: LIST_KEY,
    url: `${BASE_URL}/nueva-liquidacion`,
  });

  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (payload: NuevaRevisionInspeccionObraFormData) => {
        mutation.mutate({
          liquidacion_previa_id: payload.liquidacion_previa_id,
          liquidacion_especifica: {
            datos: {
              cantidad_visitas: payload.cantidad_visitas,
              categoria: payload.categoria,
            },
            tarifa: { tarifa_visitas_id: payload.tarifa_visitas_id },
            inspector_operacion_id: payload.inspector_operacion_id,
          },
          contacto: payload.contacto ?? undefined,
        });
      },
      mutateAsync: async (payload: NuevaRevisionInspeccionObraFormData) => {
        return mutation.mutateAsync({
          liquidacion_previa_id: payload.liquidacion_previa_id,
          liquidacion_especifica: {
            datos: {
              cantidad_visitas: payload.cantidad_visitas,
              categoria: payload.categoria,
            },
            tarifa: { tarifa_visitas_id: payload.tarifa_visitas_id },
            inspector_operacion_id: payload.inspector_operacion_id,
          },
          contacto: payload.contacto ?? undefined,
        });
      },
    }),
    [mutation],
  );

  return crearMutation;
}
