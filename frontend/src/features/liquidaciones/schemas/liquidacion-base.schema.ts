import { z } from "zod";

// Coerce helper: backend may send Decimal as string ("123.45") or number
const num = () => z.coerce.number();

// lenient uuid: Django Ninja may serialize UUIDs as plain strings
const uuid = () => z.string();

// Inline entity schema (no id, embedded in ProyectoOutput)
export const EntidadInlineSchema = z.object({
  tipo_documento: z.string(),
  numero_documento: z.string(),
  razon_social: z.string(),
});

// DistritoOutput: id, nombre, ubigeo?, provincia?, departamento?
export const DepartamentoOutputSchema = z.object({
  id: uuid(),
  nombre: z.string(),
});

export const ProvinciaOutputSchema = z.object({
  id: uuid(),
  nombre: z.string(),
});

export const DistritoOutputSchema = z.object({
  id: uuid(),
  nombre: z.string(),
  ubigeo: z.string().nullish(),
  provincia: ProvinciaOutputSchema.nullish(),
  departamento: DepartamentoOutputSchema.nullish(),
});

// ProyectoOutput: id (uuid), denominacion, nombre_propietario, direccion, distrito (object), entidad
export const ProyectoOutputSchema = z.object({
  id: uuid(),
  denominacion: z.string(),
  nombre_propietario: z.string(),
  direccion: z.string(),
  distrito: DistritoOutputSchema.nullish(),
  entidad: EntidadInlineSchema.nullable(),
});

// MunicipalidadOutput: id, codigo, nombre
export const MunicipalidadOutputSchema = z.object({
  id: uuid(),
  codigo: z.string().nullable(),
  nombre: z.string(),
});

// UsuarioCreadorOutput: id, nombres?, apellidos?, email?, dni?, username?
export const UsuarioCreadorOutputSchema = z.object({
  id: uuid(),
  nombres: z.string().nullish(),
  apellidos: z.string().nullish(),
  email: z.string().nullish(),
  dni: z.string().nullish(),
  username: z.string().nullish(),
});

// IgvOutput: id, valor, periodo_inicio?
export const IgvOutputSchema = z.object({
  id: uuid(),
  valor: num(),
  periodo_inicio: z.string().nullish(),
});

// UitOutput: id, valor, periodo_inicio?
export const UitOutputSchema = z.object({
  id: uuid(),
  valor: num(),
  periodo_inicio: z.string().nullish(),
});

// ContactoOutput: id, nombres?, apellidos?, dni?, cargo?, telefono?, celular?, email?
export const ContactoOutputSchema = z.object({
  id: uuid(),
  nombres: z.string().nullish(),
  apellidos: z.string().nullish(),
  dni: z.string().nullish(),
  cargo: z.string().nullish(),
  telefono: z.string().nullish(),
  celular: z.string().nullish(),
  email: z.string().nullish(),
});

// LiquidacionTipoOutput (identidad): id (uuid), numero (int)
export const LiquidacionTipoOutputSchema = z.object({
  id: uuid(),
  numero: z.coerce.number().int(),
});

// TipoLiquidacionOutput: codigo, nombre (sin id)
export const TipoLiquidacionOutputSchema = z.object({
  codigo: z.string().nullish(),
  nombre: z.string().nullish(),
});

// ── Delegados asociados a la liquidación (DelegadoOperativoMinOut) ────────────
export const EspecialidadRevisionOutputSchema = z.object({
  id: uuid(),
  nombre: z.string(),
});

export const ColegiadoMinOutputSchema = z.object({
  id: uuid(),
  cip: z.string(),
  dni: z.string(),
  nombre_completo: z.string(),
  especialidad: EspecialidadRevisionOutputSchema.nullish(),
  capitulo: z
    .object({
      id: uuid(),
      registro_id: z.string().nullish(),
      abreviacion: z.string().nullish(),
      nombre: z.string().nullish(),
    })
    .nullish(),
});

export const DelegadoOperativoMinOutputSchema = z.object({
  id: uuid(),
  colegiado: ColegiadoMinOutputSchema,
});

// LiquidacionGeneralOutput — matches backend EXACTLY (rich fields), tolerant to nulls/strings
export const LiquidacionGeneralOutputSchema = z.object({
  id: uuid(),
  municipalidad: MunicipalidadOutputSchema.nullish(),
  usuario_creador: UsuarioCreadorOutputSchema.nullish(),
  fecha_registro: z.string(),
  expediente: z.string().nullish(),
  observacion: z.string().nullish(),
  numero_revision: z.coerce.number().int(),
  sub_total: num(),
  total: num(),
  retencion: z.boolean().optional(),
  igv: IgvOutputSchema.nullish(),
  uit: UitOutputSchema.nullish(),
  proyecto: ProyectoOutputSchema,
  contacto: ContactoOutputSchema.nullish(),
  tipo_liquidacion: TipoLiquidacionOutputSchema.nullish(),
  revisiones_previas: z
    .array(
      z.object({
        id: uuid(),
        numero_revision: z.coerce.number().int(),
        expediente: z.string().nullish(),
      }),
    )
    .default([]),
  delegados: z.array(DelegadoOperativoMinOutputSchema).default([]),
});

// Paginated response helper (items directly, without ApiResponse wrapper)
export function paginatedResponseSchema<T extends z.ZodTypeAny>(itemSchema: T) {
  return z.object({
    items: z.array(itemSchema),
    total: num(),
    page: z.coerce.number().int(),
    page_size: z.coerce.number().int(),
    total_pages: z.coerce.number().int(),
  });
}

// Re-export for convenience
export type EntidadInline = z.infer<typeof EntidadInlineSchema>;
export type ProyectoOutput = z.infer<typeof ProyectoOutputSchema>;
export type MunicipalidadOutput = z.infer<typeof MunicipalidadOutputSchema>;
export type UsuarioCreadorOutput = z.infer<typeof UsuarioCreadorOutputSchema>;
export type IgvOutput = z.infer<typeof IgvOutputSchema>;
export type UitOutput = z.infer<typeof UitOutputSchema>;
export type ContactoOutput = z.infer<typeof ContactoOutputSchema>;
export type DepartamentoOutput = z.infer<typeof DepartamentoOutputSchema>;
export type ProvinciaOutput = z.infer<typeof ProvinciaOutputSchema>;
export type DistritoOutput = z.infer<typeof DistritoOutputSchema>;
export type LiquidacionTipoOutput = z.infer<typeof LiquidacionTipoOutputSchema>;
export type LiquidacionGeneralOutput = z.infer<
  typeof LiquidacionGeneralOutputSchema
>;
export type DelegadoOperativoMinOutput = z.infer<
  typeof DelegadoOperativoMinOutputSchema
>;
export type ColegiadoMinOutput = z.infer<typeof ColegiadoMinOutputSchema>;
export type EspecialidadRevisionOutput = z.infer<
  typeof EspecialidadRevisionOutputSchema
>;
