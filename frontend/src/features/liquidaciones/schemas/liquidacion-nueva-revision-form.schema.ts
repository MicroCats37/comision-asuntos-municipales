/**
 * Zod schema para NUEVA REVISIÓN de Edificaciones.
 * Schema PROPIO y reducido del endpoint /nueva-revision.
 *
 * Se hereda de la previa (NO viene en el input): valor_declarado, municipalidad_id, proyecto.
 * Se edita: expediente, observacion, retencion, contacto, tarifas.
 */
import { z } from "zod";
import { contactoInlineSchema } from "./liquidacion-form-base.schema";

export const nuevaRevisionEdificacionesFormSchema = z.object({
  // ID de la liquidación previa (obligatorio, se usa como base)
  liquidacion_previa_id: z.string().min(1, "Falta la liquidación previa"),
  // Solo estos campos se editan de liquidacion_general
  expediente: z.string().min(1, "Requerido"),
  observacion: z.string().optional(),
  retencion: z.boolean().optional(),
  // Contacto principal (singular)
  contacto: contactoInlineSchema.optional(),
  // Smart Field outputs — set by Smart Fields via setValue
  /** ID de la única tarifa vigente de porcentaje de obra */
  tarifa_unica_id: z.string().optional(),
  /** IDs de especialidades seleccionadas — al menos una */
  especialidades_seleccionadas: z.array(z.string()).min(1, "Selecciona al menos una especialidad"),
});

export type NuevaRevisionEdificacionesFormData = z.infer<typeof nuevaRevisionEdificacionesFormSchema>;
