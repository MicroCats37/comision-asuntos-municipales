/**
 * Zod schemas para formulario de liquidaciones edificaciones.
 */
import { z } from "zod";
import { tipoTramiteEdificacionesSchema } from "./liquidacion.schema";

export const liquidacionEdificacionFormSchema = z.object({
  municipalidad_id: z.string().uuid("Debe seleccionar una municipalidad"),
  tipo_tramite: tipoTramiteEdificacionesSchema,
  valor_proyecto: z.number().positive("El valor del proyecto debe ser positivo"),
  observacion: z.string().optional(),
  revisiones_ids: z.array(z.string()),
  proyectistas_ids: z.array(z.string()),
  proyecto_public_id: z.string().min(1, "Debe seleccionar un proyecto"),
});

export type LiquidacionEdificacionFormSchema = z.infer<typeof liquidacionEdificacionFormSchema>;

// Schema for submit (excludes internal fields like proyecto that gets converted to public_id)
export const liquidacionEdificacionSubmitSchema = z.object({
  proyecto_public_id: z.string().min(1, "Debe seleccionar un proyecto"),
  municipalidad_id: z.string().uuid("Debe seleccionar una municipalidad"),
  tipo_tramite: tipoTramiteEdificacionesSchema,
  valor_proyecto: z.number().positive("El valor del proyecto debe ser positivo"),
  observacion: z.string().optional(),
  revisiones_ids: z.array(z.string()).default([]),
  proyectistas_ids: z.array(z.string()).default([]),
});

export type LiquidacionEdificacionSubmitSchema = z.infer<typeof liquidacionEdificacionSubmitSchema>;
