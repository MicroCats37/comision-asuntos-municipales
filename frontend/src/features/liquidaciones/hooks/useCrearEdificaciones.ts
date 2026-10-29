/**
 * Hook para crear liquidaciones de Edificaciones (primera revisión).
 * Usa useLiquidacionesCreateMutation (cache manual reactivo) + useApiCreate interno.
 *
 * Endpoint: POST /liquidaciones/edificaciones/nueva-liquidacion/primera-revision
 */
import { useMemo } from "react";
import type { EdificacionesFormData } from "../schemas/liquidacion-edificaciones-form.schema";
import {
  construirEstrategiaPayload,
  ESTRATEGIA_NORMAL,
  leerEstrategiaFormData,
} from "../schemas/liquidacion-po-estrategia.schema";
import { useLiquidacionesCreateMutation } from "./cache";

const BASE_URL = "/liquidaciones/edificaciones/nueva-liquidacion";
const LIST_KEY = ["liquidaciones", "edificaciones"] as const;

/**
 * Payload de creación (primera-revisión) de Edificaciones.
 *
 * `numero_revision` viaja en el TOP LEVEL del body (contrato backend
 * `LiquidacionEdificacionesInput` = `NumeroRevisionRequeridoMixin` + wrappers):
 * es obligatorio y lo elige el usuario (etiqueta editable, no lo deriva el
 * backend).
 *
 * `liquidacion_especifica` es la UNION DISCRIMINADA de estrategias de
 * Edificaciones: el backend exige el discriminador y un `datos` distinto por
 * estrategia (`valor_declarado` o `total_explicito`, nunca ambos).
 */
export function buildCrearEdificacionesPayload(payload: EdificacionesFormData) {
  const {
    tarifa_unica_id,
    especialidades_seleccionadas,
    tipo_tramite,
    numero_revision,
    ...rest
  } = payload;
  const {
    estrategia_cotizacion,
    valor_declarado,
    total_explicito,
  } = leerEstrategiaFormData(payload);
  return {
    numero_revision,
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
      // Contacto principal (singular, opcional)
      ...(rest.contacto ? { contacto: rest.contacto } : {}),
    },
    liquidacion_especifica: construirEstrategiaPayload({
      estrategia: estrategia_cotizacion ?? ESTRATEGIA_NORMAL,
      valor_declarado,
      total_explicito,
      tipo_tramite,
      tarifas: (especialidades_seleccionadas || []).map((espId) => ({
        tarifa_porcentaje_obra_id: tarifa_unica_id,
        especialidad_id: espId,
      })),
    }),
  };
}

export function useCrearEdificaciones() {
  const mutation = useLiquidacionesCreateMutation<{
    liquidacion_general: unknown;
    liquidacion_especifica: unknown;
    numero_revision: number;
  }>({
    tipoQueryKey: LIST_KEY,
    url: `${BASE_URL}/primera-revision`,
  });

  // Wrapper that formats payload as { liquidacion_general, liquidacion_especifica } for the API
  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (payload: EdificacionesFormData) => {
        mutation.mutate(buildCrearEdificacionesPayload(payload));
      },
      mutateAsync: async (payload: EdificacionesFormData) => {
        return mutation.mutateAsync(buildCrearEdificacionesPayload(payload));
      },
    }),
    [mutation],
  );

  return crearMutation;
}
