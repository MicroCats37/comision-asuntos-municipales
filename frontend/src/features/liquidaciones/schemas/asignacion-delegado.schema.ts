import { z } from "zod";

/** Asignación de delegado a una liquidación (metadata por delegado). */
export const AsignacionDelegadoSchema = z.object({
  delegado_id: z.string(),
  periodo: z.number().int().optional().nullable(),
  mes: z.number().int().optional().nullable(),
  dictamen_revision: z.string().optional().nullable(),
  fecha_presentacion: z.string().optional().nullable(),
  fecha_revision: z.string().optional().nullable(),
});
export type Asignacion = z.infer<typeof AsignacionDelegadoSchema>;

/** Payload del formulario de gestión de delegados. */
export const GestionarDelegadosSchema = z.object({
  asignaciones: z.array(AsignacionDelegadoSchema),
});
export type GestionarDelegadosData = z.infer<typeof GestionarDelegadosSchema>;
