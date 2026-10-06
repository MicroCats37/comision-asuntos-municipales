/**
 * Zod schemas for liquidacion edit PATCH payloads.
 *
 * Contract: each PATCH endpoint accepts a partial payload with optional
 * { liquidacion_general?, liquidacion_tipo? } wrappers.
 * Only fields being updated need to be sent.
 *
 * Based on backend patch schemas:
 * - liquidacion_patch_po_schemas.py  (PO: valor_declarado, tarifas[])
 * - liquidacion_patch_m2_schemas.py (M2: area_solicitada, tarifa_m2_id)
 * - liquidacion_patch_visitas_schemas.py (Visitas: cantidad_visitas, categoria, tarifa_visitas_id)
 */
import { z } from "zod";
import { contactoInlineSchema } from "./liquidacion-form-base.schema";

// ── General edit payload (shared across all types) ──────────────────────────

/**
 * Partial liquidacion_general fields editable via PATCH.
 * All fields optional — only send what changed.
 *
 * Editability rules (enforced by backend):
 * - expediente, observacion, retencion, contacto: always editable (estado !== PAGADA)
 * - proyecto.*, municipalidad_id: only when numero_revision == 1
 */
export const LiquidacionGeneralEditSchema = z.object({
  expediente: z.string().optional(),
  observacion: z.string().optional(),
  retencion: z.boolean().optional(),
  contacto: contactoInlineSchema.optional(),
  denominacion_de_proyecto: z.string().optional(),
  // Proyecto edit (only when canEditProyecto is true)
  proyecto: z
    .object({
      nombre_propietario: z.string().optional(),
      direccion: z.string().optional(),
      urbanizacion: z.string().optional(),
      distrito_id: z.string().optional(),
      entidad: z
        .object({
          tipo_documento: z.string().optional(),
          numero_documento: z.string().optional(),
          razon_social: z.string().optional(),
        })
        .optional(),
    })
    .optional(),
  municipalidad_id: z.string().optional(),
});

export type LiquidacionGeneralEdit = z.infer<
  typeof LiquidacionGeneralEditSchema
>;

// ── PO edit payload (Edificaciones, Impacto Vial, Taludes) ───────────────────

/** Tarifa row for PO (PorcentajeObra) edit payload */
export const PorcentajeObraTarifaEditSchema = z.object({
  tarifa_porcentaje_obra_id: z.string(),
  especialidad_id: z.string(),
});

export type PorcentajeObraTarifaEdit = z.infer<
  typeof PorcentajeObraTarifaEditSchema
>;

/** liquidacion_tipo payload for PO types */
export const PorcentajeObraTipoEditSchema = z.object({
  datos: z
    .object({
      valor_declarado: z.number().optional(),
      tipo_tramite: z.string().optional(),
    })
    .optional(),
  tarifas: z.array(PorcentajeObraTarifaEditSchema).optional(),
});

export type PorcentajeObraTipoEdit = z.infer<
  typeof PorcentajeObraTipoEditSchema
>;

// ── M2 edit payload (Habilitación Urbana, Mecánica de Suelos) ─────────────

/** liquidacion_tipo payload for M2 types */
export const M2TipoEditSchema = z.object({
  datos: z
    .object({
      area_solicitada: z.number().optional(),
    })
    .optional(),
  tarifa: z
    .object({
      tarifa_m2_id: z.string().optional(),
    })
    .optional(),
});

export type M2TipoEdit = z.infer<typeof M2TipoEditSchema>;

// ── Visitas edit payload (Inspección de Obra) ───────────────────────────────

/** liquidacion_tipo payload for Visitas (IO) */
export const VisitasTipoEditSchema = z.object({
  datos: z
    .object({
      cantidad_visitas: z.number().optional(),
      categoria: z.string().optional(),
    })
    .optional(),
  tarifa: z
    .object({
      tarifa_visitas_id: z.string().optional(),
    })
    .optional(),
  inspector_operacion_id: z.string().optional(),
});

export type VisitasTipoEdit = z.infer<typeof VisitasTipoEditSchema>;

// ── Full edit payload wrappers ─────────────────────────────────────────────

/** Full PATCH payload for PO types (Edificaciones, IV, Taludes) */
export const PorcentajeObraEditPayloadSchema = z.object({
  liquidacion_general: LiquidacionGeneralEditSchema.optional(),
  liquidacion_tipo: PorcentajeObraTipoEditSchema.optional(),
});

export type PorcentajeObraEditPayload = z.infer<
  typeof PorcentajeObraEditPayloadSchema
>;

/** Full PATCH payload for M2 types (HU, MS) */
export const M2EditPayloadSchema = z.object({
  liquidacion_general: LiquidacionGeneralEditSchema.optional(),
  liquidacion_tipo: M2TipoEditSchema.optional(),
});

export type M2EditPayload = z.infer<typeof M2EditPayloadSchema>;

/** Full PATCH payload for Visitas (IO) */
export const VisitasEditPayloadSchema = z.object({
  liquidacion_general: LiquidacionGeneralEditSchema.optional(),
  liquidacion_tipo: VisitasTipoEditSchema.optional(),
});

export type VisitasEditPayload = z.infer<typeof VisitasEditPayloadSchema>;
