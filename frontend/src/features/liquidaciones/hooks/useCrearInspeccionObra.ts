/**
 * Hook para crear liquidaciones de Inspección de Obra (primera revisión).
 * Usa useLiquidacionesCreateMutation (cache manual reactivo) + useApiCreate interno.
 *
 * Endpoint: POST /liquidaciones/inspeccion-obra/nueva-liquidacion
 */
import { useMemo } from "react";
import { MODO_COTIZACION_IO_NORMAL } from "../schemas/liquidacion-io-modo-cotizacion.schema";
import type { VisitasFormData } from "../schemas/liquidacion-visitas-form.schema";
import { useLiquidacionesCreateMutation } from "./cache";

const BASE_URL = "/liquidaciones/inspeccion-obra";
const LIST_KEY = ["liquidaciones", "inspeccion-obra"] as const;

/**
 * Bloque OPCIONAL de continuidad que viaja en `liquidacion_especifica`.
 *
 * Es el MISMO tipo que el del formulario (el servidor calcula
 * `monto_acumulado` / `total_acumulado` y deriva `total_credito`), pero
 * declarado EXPLÍCITAMENTE porque el payload de alta lleva solo un subconjunto
 * de sus campos: el bruto declarado (`total_pagado_previa`) o, en su defecto,
 * el crédito neto legacy (`subtotal_credito`).
 */
export interface InspeccionObraContinuidadPayload {
  /** Referencia a la IO previa (A) dentro de CAM. */
  liquidacion_previa_id?: string | undefined;
  /** BRUTO declarado pagado en la IO previa (IGV incluido). */
  total_pagado_previa?: number | null | undefined;
  /** Crédito NETO legacy (solo si no hay bruto declarado). */
  subtotal_credito?: number | undefined;
}

/**
 * Bloque de continuidad del payload de ALTA.
 *
 * El endpoint de creación NO tiene discriminador de modo (`modo` es del
 * PATCH de edición): se construye campo por campo para que la petición de
 * alta siga siendo byte a byte la vigente.
 *
 * El dato que el usuario DECLARA es el BRUTO pagado en la IO previa
 * (`total_pagado_previa`, IGV incluido): si viaja, MANDA y el servidor deriva
 * el par (crédito neto, crédito bruto) con el IGV vigente. El neto
 * (`subtotal_credito`) solo viaja como camino LEGACY cuando NO hay bruto
 * declarado: nunca se envían las dos cifras del mismo dinero.
 */
function buildContinuidadCreacionPayload(
  continuidad: InspeccionObraContinuidadPayload,
): InspeccionObraContinuidadPayload {
  const totalPagadoPrevia = continuidad.total_pagado_previa;
  return {
    liquidacion_previa_id: continuidad.liquidacion_previa_id,
    ...(totalPagadoPrevia !== undefined &&
    totalPagadoPrevia !== null &&
    totalPagadoPrevia > 0
      ? { total_pagado_previa: totalPagadoPrevia }
      : { subtotal_credito: continuidad.subtotal_credito }),
  };
}

/**
 * Bloque específico de la liquidación de IO.
 *
 * El tipo es explícito (y no inferido) para que la clave `continuidad` sea
 * accesible de forma tipada tanto presente como ausente: sin el bloque la
 * petición es idéntica a la vigente.
 */
export interface InspeccionObraEspecificaPayload {
  datos: { cantidad_visitas: number };
  tarifa: { tarifa_visitas_id: string | undefined };
  inspector_id?: string;
  inspector_operacion_id?: string;
  continuidad?: InspeccionObraContinuidadPayload;
}

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
    modo_cotizacion,
    continuidad,
    ...rest
  } = payload;

  const liquidacion_especifica: InspeccionObraEspecificaPayload = {
    datos: { cantidad_visitas },
    tarifa: { tarifa_visitas_id },
    ...(!legacy
      ? { inspector_operacion_id }
      : inspector_id && inspector_operacion_id
        ? { inspector_id, inspector_operacion_id }
        : {}),
    // Continuidad OPCIONAL: solo viaja en el modo de cotización "Continuar"
    // (el bloque se descarta al volver a "Normal"). Sin el bloque, la IO es
    // normal.
    // El registro legacy NO admite continuidad (su bloque específico es
    // estricto y no la contempla).
    ...(!legacy && continuidad && modo_cotizacion !== MODO_COTIZACION_IO_NORMAL
      ? { continuidad: buildContinuidadCreacionPayload(continuidad) }
      : {}),
  };

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
    liquidacion_especifica,
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
      continuidad?: InspeccionObraContinuidadPayload;
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
