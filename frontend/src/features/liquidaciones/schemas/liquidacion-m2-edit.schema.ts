/**
 * Shared edit payload builders for M2 types (Habilitación Urbana, Mecánica de Suelos).
 *
 * These replace the inline buildPayload functions in the edit hooks.
 */
import type { M2EditPayload } from "./liquidacion-edit-payloads.schema";
import type { HabilitacionUrbanaFormData } from "./liquidacion-habilitacion-urbana-form.schema";
import type { MecanicaSuelosFormData } from "./liquidacion-mecanica-suelos-form.schema";

export type M2FormData = HabilitacionUrbanaFormData | MecanicaSuelosFormData;

// ── M2 general payload builder ─────────────────────────────────────────────

/**
 * Builds the liquidacion_general section for M2 edit payloads.
 */
export function buildM2GeneralPayload(
  data: M2FormData,
): Record<string, unknown> {
  const {
    contacto,
    municipalidad_id,
    expediente,
    observacion,
    retencion,
    denominacion,
    nombre_propietario,
    direccion,
    urbanizacion,
    distrito_id,
    entidad_tipo_documento,
    entidad_numero_documento,
    entidad_razon_social,
  } = data;

  const generalFields: Record<string, unknown> = {};
  if (municipalidad_id !== undefined)
    generalFields.municipalidad_id = municipalidad_id;
  if (expediente !== undefined) generalFields.expediente = expediente;
  if (observacion !== undefined) generalFields.observacion = observacion;
  if (retencion !== undefined) generalFields.retencion = retencion;
  if (denominacion !== undefined)
    generalFields.denominacion_de_proyecto = denominacion;
  if (contacto !== undefined) generalFields.contacto = contacto;

  const proyectoFields: Record<string, unknown> = {};
  if (nombre_propietario !== undefined)
    proyectoFields.nombre_propietario = nombre_propietario;
  if (direccion !== undefined) proyectoFields.direccion = direccion;
  if (urbanizacion !== undefined) proyectoFields.urbanizacion = urbanizacion;
  if (distrito_id !== undefined) proyectoFields.distrito_id = distrito_id;
  if (
    entidad_tipo_documento !== undefined ||
    entidad_numero_documento !== undefined ||
    entidad_razon_social !== undefined
  ) {
    proyectoFields.entidad = {};
    if (entidad_tipo_documento !== undefined)
      (proyectoFields.entidad as Record<string, unknown>).tipo_documento =
        entidad_tipo_documento;
    if (entidad_numero_documento !== undefined)
      (proyectoFields.entidad as Record<string, unknown>).numero_documento =
        entidad_numero_documento;
    if (entidad_razon_social !== undefined)
      (proyectoFields.entidad as Record<string, unknown>).razon_social =
        entidad_razon_social;
  }

  if (Object.keys(proyectoFields).length > 0)
    generalFields.proyecto = proyectoFields;

  return generalFields;
}

// ── M2 tipo payload builder ─────────────────────────────────────────────────

/**
 * Builds the liquidacion_tipo section for M2 edit payloads.
 */
export function buildM2TipoPayload(
  data: M2FormData,
): M2EditPayload["liquidacion_tipo"] {
  const { tarifa_m2_id, area_solicitada } = data;

  const tipoFields: M2EditPayload["liquidacion_tipo"] = {};

  if (area_solicitada !== undefined) {
    tipoFields.datos = { area_solicitada };
  }

  if (tarifa_m2_id !== undefined) {
    tipoFields.tarifa = { tarifa_m2_id };
  }

  return tipoFields;
}

// ── Full M2 payload builder ─────────────────────────────────────────────────

/**
 * Full PATCH payload builder for M2 edit hooks.
 */
export function buildM2EditPayload(data: M2FormData): M2EditPayload {
  const payload: M2EditPayload = {};

  const generalFields = buildM2GeneralPayload(data);
  if (Object.keys(generalFields).length > 0) {
    payload.liquidacion_general = generalFields;
  }

  const tipoFields = buildM2TipoPayload(data);
  if (tipoFields && Object.keys(tipoFields).length > 0) {
    payload.liquidacion_tipo = tipoFields;
  }

  return payload;
}
