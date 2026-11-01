/**
 * Hook para crear liquidaciones de Inspección de Obra (primera revisión).
 * Usa useLiquidacionesCreateMutation (cache manual reactivo) + useApiCreate interno.
 *
 * Endpoint: POST /liquidaciones/inspeccion-obra/nueva-liquidacion
 */
import { useMemo } from "react";
import type { VisitasFormData } from "../schemas/liquidacion-visitas-form.schema";
import { useLiquidacionesCreateMutation } from "./cache";

const BASE_URL = "/liquidaciones/inspeccion-obra";
const LIST_KEY = ["liquidaciones", "inspeccion-obra"] as const;

export function buildCrearInspeccionObraPayload(
  payload: VisitasFormData,
  legacy = false,
) {
  const {
    tarifa_visitas_id,
    cantidad_visitas,
    inspector_id,
    inspector_operacion_id,
    numero,
    fecha_registro,
    ...rest
  } = payload;

  const apiPayload = {
    liquidacion_general: {
      municipalidad_id: rest.municipalidad_id,
      expediente: rest.expediente,
      observacion: rest.observacion,
      denominacion_de_proyecto: rest.denominacion || undefined,
      proyecto: {
        nombre_propietario: rest.nombre_propietario,
        direccion: rest.direccion,
        distrito_id: rest.distrito_id || undefined,
        entidad: {
          tipo_documento: rest.entidad_tipo_documento,
          numero_documento: rest.entidad_numero_documento,
          razon_social: rest.entidad_razon_social,
        },
      },
      ...(rest.contacto ? { contacto: rest.contacto } : {}),
    },
    liquidacion_especifica: {
      datos: { cantidad_visitas },
      tarifa: { tarifa_visitas_id },
      ...(!legacy
        ? { inspector_operacion_id }
        : inspector_id && inspector_operacion_id
          ? { inspector_id, inspector_operacion_id }
          : {}),
    },
  };
  return legacy ? { ...apiPayload, numero, fecha_registro } : apiPayload;
}

export function useCrearInspeccionObra(mode: "create" | "legacy" = "create") {
  const mutation = useLiquidacionesCreateMutation<{
    liquidacion_general: unknown;
    liquidacion_especifica: {
      datos: { cantidad_visitas: number };
      tarifa: { tarifa_visitas_id: string | undefined };
      inspector_id?: string;
      inspector_operacion_id?: string;
    };
  }>({
    tipoQueryKey: LIST_KEY,
    url:
      mode === "legacy"
        ? `${BASE_URL}/nueva-liquidacion/legacy`
        : `${BASE_URL}/nueva-liquidacion`,
  });

  // Wrapper that formats payload as { liquidacion_general, liquidacion_especifica } for the API.
  // inspector_operacion_id is sent — the ID of the InspectorOperacion selected by the user
  // in the modal (obtained from /seleccionables). This allows the backend to derive
  // especialidad_revision directly from the operation instead of looking up by deprecated
  // INSPECCION_OBRA tipo.
  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (payload: VisitasFormData) => {
        mutation.mutate(
          buildCrearInspeccionObraPayload(payload, mode === "legacy"),
        );
      },
      mutateAsync: async (payload: VisitasFormData) => {
        return mutation.mutateAsync(
          buildCrearInspeccionObraPayload(payload, mode === "legacy"),
        );
      },
    }),
    [mode, mutation],
  );

  return crearMutation;
}
