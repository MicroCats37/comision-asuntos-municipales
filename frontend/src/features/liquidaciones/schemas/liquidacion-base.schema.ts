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

// ProyectoOutput: id (uuid), nombre_propietario, direccion, urbanizacion, distrito (object), entidad
export const ProyectoOutputSchema = z.object({
  id: uuid(),
  nombre_propietario: z.string(),
  direccion: z.string(),
  urbanizacion: z.string().nullish(),
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

// TipoLiquidacionMinimal: id, codigo, nombre (for select dropdowns)
export const TipoLiquidacionMinimalSchema = z.object({
  id: z.string(),
  codigo: z.string(),
  nombre: z.string(),
});

// ── Delegados asociados a la liquidación (nested structure) ───────────────────

/** Especialidad básica de un delegado — id + nombre */
export const EspecialidadBasicaDelegadoSchema = z.object({
  id: uuid(),
  nombre: z.string(),
});

/**
 * Base delegate info — shared betweenvigentes lookup and liquidacion assignment.
 * Fields: id, nombre_completo, cip, tipo, especialidad
 */
export const DelegadoBaseOutputSchema = z.object({
  id: uuid(),
  nombre_completo: z.string(),
  cip: z.string(),
  tipo: z.string(),
  especialidad: EspecialidadBasicaDelegadoSchema,
});

/**
 * Metadata for a delegate assigned to a liquidacion.
 * Fields: periodo, mes, dictamen_revision, fecha_presentacion, fecha_revision
 */
export const LiquidacionDelegadoDatosOutputSchema = z.object({
  periodo: z.number().int().nullish(),
  mes: z.number().int().nullish(),
  dictamen_revision: z.string().nullish(),
  fecha_presentacion: z.string().nullish(),
  fecha_revision: z.string().nullish(),
});

/**
 * Full delegate output for liquidacion assignment — combines delegate base info
 * with assignment metadata. Replaces DelegadoOperativoMinOutputSchema.
 */
export const LiquidacionDelegadoEnGeneralOutputSchema = z.object({
  datos: LiquidacionDelegadoDatosOutputSchema,
  delegado: DelegadoBaseOutputSchema,
});

// LiquidacionComprobanteOutput — comprobante activo de una liquidacion
export const LiquidacionComprobanteOutputSchema = z.object({
  id: uuid(),
  tipo_comprobante: z.string().nullish(),
  serie: z.string().nullish(),
  numero: z.string().nullish(),
  fecha_emision: z.string().nullish(),
  monto: num().nullish(),
  activo: z.boolean(),
  motivo_reemplazo: z.string().nullish(),
});

// LiquidacionGeneralOutput — matches backend EXACTLY (rich fields), tolerant to nulls/strings
export const LiquidacionGeneralOutputSchema = z.object({
  id: uuid(),
  estado: z.string().nullish(), // PENDIENTE | PAGADA — Fase E state machine
  municipalidad: MunicipalidadOutputSchema.nullish(),
  usuario_creador: UsuarioCreadorOutputSchema.nullish(),
  fecha_registro: z.string(),
  expediente: z.string().nullish(),
  observacion: z.string().nullish(),
  numero_revision: z.coerce.number().int(),
  sub_total: num(),
  total: num(),
  retencion: z.boolean().optional(),
  legacy: z.boolean().optional(),
  codigo_cta: z.string().nullish(),
  igv: IgvOutputSchema.nullish(),
  uit: UitOutputSchema.nullish(),
  proyecto: ProyectoOutputSchema,
  denominacion_de_proyecto: z.string().nullish(),
  contacto: ContactoOutputSchema.nullish(),
  tipo_liquidacion: TipoLiquidacionOutputSchema.nullish(),
  delegados: z.array(LiquidacionDelegadoEnGeneralOutputSchema).default([]),
  comprobantes: z.array(LiquidacionComprobanteOutputSchema).default([]),
  eliminado: z.boolean().optional(),
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
export type MunicipalOutput = z.infer<typeof MunicipalidadOutputSchema>;
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
export type LiquidacionDelegadoEnGeneralOutput = z.infer<
  typeof LiquidacionDelegadoEnGeneralOutputSchema
>;
export type DelegadoBaseOutput = z.infer<typeof DelegadoBaseOutputSchema>;
export type LiquidacionDelegadoDatosOutput = z.infer<
  typeof LiquidacionDelegadoDatosOutputSchema
>;
export type LiquidacionComprobanteOutput = z.infer<
  typeof LiquidacionComprobanteOutputSchema
>;

// ── Input schema for creating/replacing a comprobante ─────────────────────────

/** Full enum — used for backend compatibility and output display */
export const TIPO_COMPROBANTE_ENUM = [
  "FACTURA",
  "BOLETA",
  "NOTA_CREDITO",
  "NOTA_DEBITO",
] as const;

/** UI-only enum — restricted to the two types users can create via the form */
export const TIPO_COMPROBANTE_UI_ENUM = ["FACTURA", "BOLETA"] as const;

export type TipoComprobante = (typeof TIPO_COMPROBANTE_ENUM)[number];

/**
 * Schema for creating/replacing a comprobante.
 * - tipo_comprobante is restricted to FACTURA | BOLETA in the UI.
 * - serie is required (refine) when tipo is FACTURA or BOLETA.
 * - monto is NOT collected in the frontend form.
 */
export const CrearComprobanteInputSchema = z
  .object({
    tipo_comprobante: z
      .enum(TIPO_COMPROBANTE_UI_ENUM)
      .describe("Tipo: FACTURA o BOLETA"),
    serie: z.string().optional(),
    numero: z.string().optional(),
    fecha_emision: z.string().optional().describe("YYYY-MM-DD"),
    /** motivo_reemplazo is required (refine) when an active comprobante already exists */
    motivo_reemplazo: z.string().optional(),
  })
  .superRefine((data, ctx) => {
    if (
      data.tipo_comprobante === "FACTURA" ||
      data.tipo_comprobante === "BOLETA"
    ) {
      if (!data.serie || data.serie.trim().length === 0) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "La serie es requerida para facturas y boletas",
          path: ["serie"],
        });
      }
    }
  });

export type CrearComprobanteInput = z.infer<typeof CrearComprobanteInputSchema>;
