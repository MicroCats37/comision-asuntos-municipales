/**
 * Tipos para Liquidaciones de Mecánica de Suelos — API contracts.
 * Matches backend LiquidacionMecanicaSuelosOut structure.
 */
import { z } from "zod";
import {
  tipoLiquidacionSchema,
  entidadInlineSchema,
  proyectoInlineSchema,
  municipalidadInlineSchema,
  revisionBasicaSchema,
  valoresFinancierosSchema,
  variablesFinancierasSchema,
} from "./liquidacion-general.types";

export const tramiteAccionSchema = z.enum(["PRIMERA_REVISION", "REVISION"]);
export type TramiteAccion = z.infer<typeof tramiteAccionSchema>;

// ── Flat Output Type ───────────────────────────────────────────────────────────

export const liquidacionMecanicaSuelosOutSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  estado: z.string(),
  tipo_liquidacion: tipoLiquidacionSchema,
  fecha_registro: z.string(),
  expediente: z.string().nullable(),
  observacion: z.string().nullable(),
  numero_revision: z.number(),
  proyecto: proyectoInlineSchema,
  entidad: entidadInlineSchema.nullable(),
  municipalidad: municipalidadInlineSchema,
  valores: valoresFinancierosSchema,
  proyectistas: z.array(
    z.object({
      id: z.string(),
      perfil_ingeniero_id: z.string().nullable(),
      perfil_ingeniero_nombres: z.string().nullable(),
      perfil_ingeniero_apellidos: z.string().nullable(),
      perfil_ingeniero_cip: z.string().nullable(),
      especialidad_id: z.string().nullable(),
      especialidad_nombre: z.string().nullable(),
      descripcion: z.string().nullable(),
    }),
  ),
  delegados: z.array(
    z.object({
      id: z.string(),
      perfil_ingeniero_id: z.string().nullable(),
      perfil_ingeniero_nombres: z.string().nullable(),
      perfil_ingeniero_apellidos: z.string().nullable(),
      perfil_ingeniero_cip: z.string().nullable(),
      especialidad_id: z.string().nullable(),
      especialidad_nombre: z.string().nullable(),
      tipo: z.string().nullable(),
    }),
  ),
  inspectores: z.array(z.unknown()).default([]),
  contactos: z.array(
    z.object({
      id: z.string(),
      nombres: z.string().nullable(),
      apellidos: z.string().nullable(),
      dni: z.string().nullable(),
      cargo: z.string().nullable(),
      telefono: z.string().nullable(),
      celular: z.string().nullable(),
      email: z.string().nullable(),
      direccion: z.string().nullable(),
      principal: z.boolean(),
      descripcion: z.string().nullable(),
    }),
  ),
  revisiones: z.array(revisionBasicaSchema),
  subtotal: z.number(),
  igv: z.number(),
  total: z.number(),
  total_a_pagar: z.number(),
  variables_financieras_usadas: variablesFinancierasSchema.nullable(),
});

export type LiquidacionMecanicaSuelosOut = z.infer<typeof liquidacionMecanicaSuelosOutSchema>;
export type LiquidacionMecanicaSuelosListItem = LiquidacionMecanicaSuelosOut;

// ── 3-Wrapper List Item ───────────────────────────────────────────────────────

export interface LiquidacionMecanicaSuelosWrapper {
  liquidacion_general: import("./liquidacion-general.types").LiquidacionGeneralWrapper;
  liquidacion_especifica: import("./liquidacion-general.types").LiquidacionEspecificaWrapper;
  liquidacion_tipo: LiquidacionMecanicaSuelosOut;
}
