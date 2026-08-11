/**
 * Step-level Zod schemas for the Liquidacion stepper.
 * Each step validates the fields relevant to that step.
 */
import { z } from "zod";
import { tipoTramiteEdificacionesSchema } from "./liquidacion.schema";
import { contactoInlineSchema } from "./liquidacion-edificaciones-form.schema";

// ── Step 1: Proyecto ─────────────────────────────────────────────────────────
// No schema needed — proyecto selection is validated via proyecto_public_id hidden field

// ── Step 2: Liquidación + Delegados ─────────────────────────────────────────

export const step2LiquidacionSchema = z.object({
  municipalidad_id: z.string().uuid("Debe seleccionar una municipalidad"),
  tipo_tramite: tipoTramiteEdificacionesSchema,
  valor_proyecto: z
    .number()
    .positive("El valor del proyecto debe ser positivo"),
  expediente: z.string().optional(),
  valor_base_calculo: z.number().optional(),
  observacion: z.string().optional(),
});

export type Step2LiquidacionData = z.infer<typeof step2LiquidacionSchema>;

// ── Step 3: Proyectistas + Contactos ────────────────────────────────────────

export const step3PersonasSchema = z.object({
  proyectistas: z.array(
    z.object({
      cip: z
        .string()
        .regex(/^\d{3,6}$/, "El CIP debe tener entre 3 y 6 dígitos"),
      especialidad_id: z.string().uuid("Debe seleccionar una especialidad"),
      descripcion: z.string().optional(),
    }),
  ),
  contactos: z.array(contactoInlineSchema),
});

export type Step3PersonasData = z.infer<typeof step3PersonasSchema>;

// ── Step 4: Cotización ───────────────────────────────────────────────────────
// No extra validation — cotización is auto-calculated from Step 2 values

// ── Step 5: Confirmación ─────────────────────────────────────────────────────
// No schema — confirmation just displays data already validated in steps 2-3

// ── Full form schema (for final submit) ──────────────────────────────────────
// Re-export the full schema from the main liquidacion schema file

export { liquidacionEdificacionFormSchema } from "./liquidacion-edificaciones-form.schema";
