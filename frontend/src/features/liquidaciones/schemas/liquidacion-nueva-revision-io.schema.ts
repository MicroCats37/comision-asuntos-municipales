/**
 * Zod schema para NUEVA REVISIÓN de Inspección de Obra (primera-revisión desde previa).
 * Schema PROPIO y reducido del endpoint /nueva-liquidacion/primera-revision-desde-previa.
 *
 * Se hereda de la previa (NO viene en el input): proyecto, municipalidad, entidad,
 * expediente, observacion, retencion.
 * Se edita: cantidad_visitas, categoria, tarifa_visitas_id, inspector_id.
 */
import { z } from "zod";

export const nuevaRevisionInspeccionObraFormSchema = z.object({
  // ID de la liquidación previa (obligatorio, se usa como base)
  liquidacion_previa_id: z.string().min(1, "Falta la liquidación previa"),
  // Datos específicos de Visitas
  cantidad_visitas: z.coerce.number().int().min(1, "Mínimo 1 visita"),
  categoria: z.string().min(1, "Selecciona una categoría"),
  // Tarifa
  tarifa_visitas_id: z.string().min(1, "Selecciona una tarifa"),
  // Inspector asignado
  inspector_id: z.string().min(1, "Selecciona un inspector"),
});

export type NuevaRevisionInspeccionObraFormData = z.infer<
  typeof nuevaRevisionInspeccionObraFormSchema
>;
