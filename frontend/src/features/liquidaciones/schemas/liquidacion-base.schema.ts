import { z } from 'zod';

// Inline entity schema (no id, embedded in ProyectoOutput)
export const EntidadInlineSchema = z.object({
  tipo_documento: z.string(),
  numero_documento: z.string(),
  razon_social: z.string(),
});

// ProyectoOutput: id (uuid), denominacion, nombre_propietario, direccion, distrito_id (uuid), entidad
export const ProyectoOutputSchema = z.object({
  id: z.string().uuid(),
  denominacion: z.string(),
  nombre_propietario: z.string(),
  direccion: z.string(),
  distrito_id: z.string().uuid(),
  entidad: EntidadInlineSchema,
});

// LiquidacionTipoOutput (identidad): id (uuid), numero (int)
export const LiquidacionTipoOutputSchema = z.object({
  id: z.string().uuid(),
  numero: z.number().int(),
});

// LiquidacionGeneralOutput: id, municipalidad_id, usuario_creador: { id }, fecha_registro, expediente, observacion?, numero_revision (int), sub_total (float), total (float), igv_id?, uit_id?, proyecto: ProyectoOutput
export const LiquidacionGeneralOutputSchema = z.object({
  id: z.string(),
  municipalidad_id: z.string(),
  usuario_creador: z.object({ id: z.string() }),
  fecha_registro: z.string(),
  expediente: z.string(),
  observacion: z.string().optional(),
  numero_revision: z.number().int(),
  sub_total: z.number(),
  total: z.number(),
  igv_id: z.string().optional(),
  uit_id: z.string().optional(),
  proyecto: ProyectoOutputSchema,
});

// Paginated response helper
export function paginatedResponseSchema<T extends z.ZodTypeAny>(itemSchema: T) {
  return z.object({
    items: z.array(itemSchema),
    total: z.number(),
    page: z.number().int(),
    page_size: z.number().int(),
    total_pages: z.number().int(),
  });
}

// Re-export for convenience
export type EntidadInline = z.infer<typeof EntidadInlineSchema>;
export type ProyectoOutput = z.infer<typeof ProyectoOutputSchema>;
export type LiquidacionTipoOutput = z.infer<typeof LiquidacionTipoOutputSchema>;
export type LiquidacionGeneralOutput = z.infer<typeof LiquidacionGeneralOutputSchema>;
