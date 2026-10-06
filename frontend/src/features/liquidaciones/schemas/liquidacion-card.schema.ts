/**
 * Schemas de la "card" de detalle de liquidación (vista de detalle).
 * Formas compartidas por los payloads de detalle de todos los dominios.
 */
import { z } from "zod";

export const EntidadCardSchema = z.object({
  id: z.string().nullable(),
  tipo: z.string().nullable(),
  nombre: z.string().nullable(),
  ruc: z.string().nullable(),
});
export type EntidadCardData = z.infer<typeof EntidadCardSchema>;

export const ProyectoCardSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  nombre: z.string(),
  direccion: z.string().nullable(),
  valor_proyecto: z.union([z.number(), z.string()]),
  entidad: EntidadCardSchema.nullable(),
});
export type ProyectoCardData = z.infer<typeof ProyectoCardSchema>;

export const ProvinciaCardSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});
export type ProvinciaCardData = z.infer<typeof ProvinciaCardSchema>;

export const DistritoCardSchema = z.object({
  id: z.string(),
  nombre: z.string(),
  provincia: ProvinciaCardSchema.nullable(),
});
export type DistritoCardData = z.infer<typeof DistritoCardSchema>;

export const MunicipalidadCardSchema = z.object({
  id: z.string(),
  nombre: z.string(),
  codigo: z.string().nullable(),
  provincia: ProvinciaCardSchema.nullable(),
  distrito: DistritoCardSchema.nullable(),
});
export type MunicipalidadCardData = z.infer<typeof MunicipalidadCardSchema>;

/** Valores para dominios M2 (solo subtotal + total a pagar en el detalle). */
export const ValoresM2CardSchema = z.object({
  subtotal: z.union([z.number(), z.string()]),
  total_a_pagar: z.union([z.number(), z.string()]),
});
export type ValoresM2CardData = z.infer<typeof ValoresM2CardSchema>;

export const ValoresCardSchema = z.object({
  subtotal: z.union([z.number(), z.string()]),
  igv: z.union([z.number(), z.string()]),
  total: z.union([z.number(), z.string()]),
  total_a_pagar: z.union([z.number(), z.string()]),
});
export type ValoresCardData = z.infer<typeof ValoresCardSchema>;

export const ValoresCardUnionSchema = z.union([
  ValoresCardSchema,
  ValoresM2CardSchema,
]);
export type ValoresCardUnionData = z.infer<typeof ValoresCardUnionSchema>;

export const ProyectistaCardSchema = z.object({
  id: z.string(),
  perfil_ingeniero_id: z.string().nullable(),
  perfil_ingeniero_nombres: z.string().nullable(),
  perfil_ingeniero_apellidos: z.string().nullable(),
  perfil_ingeniero_cip: z.string().nullable(),
  especialidad_id: z.string().nullable(),
  especialidad_nombre: z.string().nullable(),
  descripcion: z.string().nullable(),
});
export type ProyectistaCardData = z.infer<typeof ProyectistaCardSchema>;

export const DelegadoCardSchema = z.object({
  id: z.string(),
  perfil_ingeniero_id: z.string().nullable(),
  perfil_ingeniero_nombres: z.string().nullable(),
  perfil_ingeniero_apellidos: z.string().nullable(),
  perfil_ingeniero_cip: z.string().nullable(),
  especialidad_id: z.string().nullable(),
  especialidad_nombre: z.string().nullable(),
  tipo: z.string().nullable(),
});
export type DelegadoCardData = z.infer<typeof DelegadoCardSchema>;

export const ContactoCardSchema = z.object({
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
});
export type ContactoCardData = z.infer<typeof ContactoCardSchema>;

export const EspecialidadRevisionCardSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});
export type EspecialidadRevisionCardData = z.infer<
  typeof EspecialidadRevisionCardSchema
>;

/** Tarifa de revisión con campos por dominio (todos opcionales). */
export const TarifaRevisionCardSchema = z.object({
  id: z.string(),
  costo_por_m2: z.number().nullable().optional(),
  area_m2: z.number().nullable().optional(),
  derecho_minimo: z.number().nullable().optional(),
  derecho_maximo: z.number().nullable().optional(),
  costo_por_visita: z.number().nullable().optional(),
  visitas_minimas: z.number().nullable().optional(),
  categoria: z.string().nullable().optional(),
  porcentaje_liquidacion: z.number().nullable().optional(),
  porcentaje_minimo_uit: z.number().nullable().optional(),
  cantidad_visitas: z.number().nullable().optional(),
});
export type TarifaRevisionCardData = z.infer<typeof TarifaRevisionCardSchema>;

export const RevisionCardSchema = z.object({
  id: z.string(),
  numero_revision: z.number().optional(),
  especialidades: z.array(EspecialidadRevisionCardSchema),
  tarifa: TarifaRevisionCardSchema.nullable(),
});
export type RevisionCardData = z.infer<typeof RevisionCardSchema>;

/** Item de detalle (card base) — común a todos los dominios. */
export const LiquidacionCardBaseSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  estado: z.string(),
  tipo_liquidacion: z.string(),
  numero_revision: z.number(),
  fecha_registro: z.string(),
  proyecto: ProyectoCardSchema,
  entidad: EntidadCardSchema.nullable(),
  municipalidad: MunicipalidadCardSchema,
  valores: ValoresCardUnionSchema,
  proyectistas: z.array(ProyectistaCardSchema),
  delegados: z.array(DelegadoCardSchema),
  contactos: z.array(ContactoCardSchema),
  revisiones: z.array(RevisionCardSchema),
  expediente: z.string().nullable().optional(),
  observacion: z.string().nullable().optional(),
});
export type LiquidacionCardBase = z.infer<typeof LiquidacionCardBaseSchema>;
