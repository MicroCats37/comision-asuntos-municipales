/**
 * Hook para crear una liquidación RELACIONADA de Inspección de Obra.
 *
 * POST /liquidaciones/inspeccion-obra/relacionada
 * Payload:
 * {
 *   liquidacion_previa_id: uuid,
 *   liquidacion_especifica: {
 *     datos: { cantidad_visitas: number },
 *     tarifa: { tarifa_visitas_id: string },
 *     inspector_operacion_id: string,
 *   },
 *   contacto?: { nombres, apellidos, dni, cargo, telefono, celular, email },
 * }
 *
 * Crea una liquidación con numero_revision = 1, heredando proyecto, municipalidad,
 * entidad, expediente y observacion de la previa.
 *
 * Usa useLiquidacionesCreateMutation (cache manual reactivo). La liquidación devuelta se inserta/actualiza en las listas visibles; la revisión previa permanece en la lista (ya no hay revisión canónica).
 */
import { useMemo } from "react";
import type { NuevaRevisionInspeccionObraFormData } from "../schemas/liquidacion-nueva-revision-io.schema";
import { useLiquidacionesCreateMutation } from "./cache";

const BASE_URL = "/liquidaciones/inspeccion-obra";
const LIST_KEY = ["liquidaciones", "inspeccion-obra"] as const;

type CrearRelacionadaInspeccionObraData = Omit<
  NuevaRevisionInspeccionObraFormData,
  "categoria"
>;

export function buildCrearRelacionadaInspeccionObraPayload(
  payload: CrearRelacionadaInspeccionObraData,
) {
  return {
    liquidacion_previa_id: payload.liquidacion_previa_id,
    liquidacion_especifica: {
      datos: { cantidad_visitas: payload.cantidad_visitas },
      tarifa: { tarifa_visitas_id: payload.tarifa_visitas_id },
      inspector_operacion_id: payload.inspector_operacion_id,
    },
    contacto: payload.contacto ?? undefined,
  };
}

export function useCrearRelacionadaInspeccionObra() {
  const mutation = useLiquidacionesCreateMutation<{
    liquidacion_previa_id: string;
    liquidacion_especifica: {
      datos: { cantidad_visitas: number };
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
    url: `${BASE_URL}/relacionada`,
  });

  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (payload: CrearRelacionadaInspeccionObraData) => {
        mutation.mutate(buildCrearRelacionadaInspeccionObraPayload(payload));
      },
      mutateAsync: async (payload: CrearRelacionadaInspeccionObraData) => {
        return mutation.mutateAsync(
          buildCrearRelacionadaInspeccionObraPayload(payload),
        );
      },
    }),
    [mutation],
  );

  return crearMutation;
}
