/**
 * Zod schema for Edificaciones creation form.
 * General fields (proyecto, trámite, contacto) vienen del base compartido.
 */
import { z } from "zod";
import {
  contactoInlineSchema,
  generalFormSchema,
  proyectoFormSchema,
} from "./liquidacion-form-base.schema";
import { TipoTramiteEdificacionesSchema } from "./tramite.schema";

export const edificacionesFormSchema = z.object({
  ...proyectoFormSchema.shape,
  ...generalFormSchema.shape,
  // Especifica fields (motor PorcentajeObra)
  valor_declarado: z.number().positive("El valor declarado debe ser positivo"),
  /** Tipo de trámite de edificaciones — requerido, default OBRA_NUEVA */
  tipo_tramite: TipoTramiteEdificacionesSchema.default("OBRA_NUEVA"),
  // Smart Field outputs — set by Smart Fields via setValue
  /** ID de la única tarifa vigente de porcentaje de obra */
  tarifa_unica_id: z.string().optional(),
  /** IDs de especialidades seleccionadas por el usuario — al menos una */
  especialidades_seleccionadas: z
    .array(z.string())
    .min(1, "Selecciona al menos una especialidad")
    .optional(),
  // Contacto principal (singular, managed via ContactoFormModal)
  contacto: contactoInlineSchema.optional(),
});

export type EdificacionesFormData = z.infer<typeof edificacionesFormSchema>;
