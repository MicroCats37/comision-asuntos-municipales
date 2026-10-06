/**
 * Shared edit payload builders for Visitas type (Inspección de Obra).
 *
 * These replace the inline buildPayload function in useEditarInspeccionObra.
 * Includes contacto fix (Bug 2).
 */
import type { VisitasEditPayload } from "./liquidacion-edit-payloads.schema";
import type { VisitasFormData } from "./liquidacion-visitas-form.schema";

// ── Visitas general payload builder ─────────────────────────────────────────

/**
 * Builds the liquidacion_general section for Visitas edit payloads.
 * Includes contacto (Bug 2 fix).
 */
export function buildVisitasGeneralPayload(
  data: VisitasFormData,
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
  // contacto fix: include contacto when present (was silently dropped)
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

// ── Visitas tipo payload builder ────────────────────────────────────────────

/**
 * Builds the liquidacion_tipo section for Visitas edit payloads.
 */
export function buildVisitasTipoPayload(
  data: VisitasFormData,
): VisitasEditPayload["liquidacion_tipo"] {
  const {
    cantidad_visitas,
    categoria,
    tarifa_visitas_id,
    inspector_operacion_id,
  } = data;

  const tipoFields: VisitasEditPayload["liquidacion_tipo"] = {};

  if (cantidad_visitas !== undefined || categoria !== undefined) {
    tipoFields.datos = {};
    if (cantidad_visitas !== undefined)
      tipoFields.datos.cantidad_visitas = cantidad_visitas;
    if (categoria !== undefined) tipoFields.datos.categoria = categoria;
  }

  if (tarifa_visitas_id !== undefined) {
    tipoFields.tarifa = { tarifa_visitas_id };
  }

  if (inspector_operacion_id !== undefined) {
    tipoFields.inspector_operacion_id = inspector_operacion_id;
  }

  return tipoFields;
}

// ── Full Visitas payload builder ────────────────────────────────────────────

/**
 * Full PATCH payload builder for Visitas/IO edit hooks.
 */
export function buildVisitasEditPayload(
  data: VisitasFormData,
): VisitasEditPayload {
  const payload: VisitasEditPayload = {};

  const generalFields = buildVisitasGeneralPayload(data);
  if (Object.keys(generalFields).length > 0) {
    payload.liquidacion_general = generalFields;
  }

  const tipoFields = buildVisitasTipoPayload(data);
  if (tipoFields && Object.keys(tipoFields).length > 0) {
    payload.liquidacion_tipo = tipoFields;
  }

  return payload;
}
