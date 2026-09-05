/**
 * Shared edit payload builders for PO types (Edificaciones, Taludes, Impacto Vial).
 *
 * These replace the inline buildPayload functions in the edit hooks.
 * Provides typed, auditable payload construction with explicit field lists.
 */

import type { EdificacionesFormData } from "./liquidacion-edificaciones-form.schema";
import type {
  PorcentajeObraEditPayload,
  PorcentajeObraTipoEdit,
} from "./liquidacion-edit-payloads.schema";
import type { ContactoInline } from "./liquidacion-form-base.schema";
import type { ImpactoVialFormData } from "./liquidacion-impacto-vial-form.schema";
import type { TaludesFormData } from "./liquidacion-taludes-form.schema";

export type POFormData =
  | EdificacionesFormData
  | TaludesFormData
  | ImpactoVialFormData;

// ── Contacto inline adapter ─────────────────────────────────────────────────

export function toContactoInline(
  contacto:
    | {
        nombres: string;
        apellidos?: string | null;
        dni?: string | null;
        cargo?: string | null;
        telefono?: string | null;
        celular?: string | null;
        email?: string | null;
      }
    | null
    | undefined,
): ContactoInline | null {
  if (!contacto?.nombres) return null;
  return {
    nombres: contacto.nombres,
    apellidos: contacto.apellidos ?? undefined,
    dni: contacto.dni ?? undefined,
    cargo: contacto.cargo ?? undefined,
    telefono: contacto.telefono ?? undefined,
    celular: contacto.celular ?? undefined,
    email: contacto.email ?? undefined,
  };
}

// ── PO general payload builder ──────────────────────────────────────────────

/**
 * Builds the liquidacion_general section for PO edit payloads.
 * Handles proyecto nested fields and contacto.
 *
 * @param data - The form data
 * @param canEditProyecto - When false, skips all proyecto fields from the payload
 *                          (used for revisions > 1 to avoid backend errors).
 */
export function buildPOGeneralPayload(
  data: POFormData,
  canEditProyecto: boolean = true,
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

  // Only include proyecto fields when explicitly allowed (first revision)
  if (canEditProyecto) {
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
  }

  return generalFields;
}

// ── PO tipo payload builder ─────────────────────────────────────────────────

/**
 * Builds the liquidacion_tipo section for PO edit payloads.
 * Includes tipo_tramite (Bug 1 fix) and tarifas.
 */
export function buildPOTipoPayload(data: POFormData): PorcentajeObraTipoEdit {
  const { tarifa_unica_id, especialidades_seleccionadas, valor_declarado } =
    data;
  // tipo_tramite only exists on EdificacionesFormData — cast to access safely
  const tipo_tramite = (data as EdificacionesFormData).tipo_tramite;

  const tipoFields: PorcentajeObraTipoEdit = {};

  if (valor_declarado !== undefined || tipo_tramite !== undefined) {
    tipoFields.datos = {};
    if (valor_declarado !== undefined)
      tipoFields.datos.valor_declarado = valor_declarado;
    // tipo_tramite fix: include it when present (Edificaciones only)
    if (tipo_tramite !== undefined)
      (tipoFields.datos as Record<string, unknown>).tipo_tramite = tipo_tramite;
  }

  if (
    (tarifa_unica_id !== undefined ||
      especialidades_seleccionadas !== undefined) &&
    tarifa_unica_id &&
    especialidades_seleccionadas?.length
  ) {
    tipoFields.tarifas = especialidades_seleccionadas.map((espId) => ({
      tarifa_porcentaje_obra_id: tarifa_unica_id,
      especialidad_id: espId,
    }));
  }

  return tipoFields;
}

// ── Full PO payload builder ─────────────────────────────────────────────────

/**
 * Full PATCH payload builder for PO edit hooks.
 * Replaces the inline buildPayload function in each PO hook.
 *
 * @param data - The form data
 * @param canEditProyecto - When false, skips all proyecto fields from the payload
 *                          (used for revisions > 1 to avoid backend errors).
 */
export function buildPOEditPayload(
  data: POFormData,
  canEditProyecto: boolean = true,
): PorcentajeObraEditPayload {
  const payload: PorcentajeObraEditPayload = {};

  const generalFields = buildPOGeneralPayload(data, canEditProyecto);
  if (Object.keys(generalFields).length > 0) {
    payload.liquidacion_general = generalFields;
  }

  const tipoFields = buildPOTipoPayload(data);
  if (Object.keys(tipoFields).length > 0) {
    payload.liquidacion_tipo = tipoFields;
  }

  return payload;
}
