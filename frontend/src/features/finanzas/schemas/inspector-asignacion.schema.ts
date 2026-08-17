/**
 * Zod schemas for Inspectores Asignaciones — mirrors backend LiquidacionInspectorAsignacionOut.
 * Endpoint: GET /liquidaciones/inspectores/inspectores-asignaciones
 */
import { z } from "zod";
import { TipoLiquidacionMinimalSchema } from "./tipo-liquidacion-minimal.schema";

const uuid = () => z.string();

export { TipoLiquidacionMinimalSchema as tipoLiquidacionMinimalSchema } from "./tipo-liquidacion-minimal.schema";

export const liquidacionInspectorLiquidacionSchema = z.object({
  id: uuid(),
  expediente: z.string().nullish(),
  numero_revision: z.coerce.number().int(),
  sub_total: z.number().nullish(),
  total: z.number().nullish(),
  municipalidad_nombre: z.string().nullish(),
  proyecto_denominacion: z.string().nullish(),
  tipo_liquidacion: TipoLiquidacionMinimalSchema.nullish(),
});

export const inspectorAsignacionInspectorSchema = z.object({
  id: uuid(),
  cip: z.string(),
  dni: z.string(),
  nombre_completo: z.string(),
});

export const especialidadRevisionInspectorSchema = z.object({
  id: uuid(),
  nombre: z.string(),
});

/** LiquidacionInspectorAsignacionOut — matches backend schema exactly */
export const liquidacionInspectorAsignacionSchema = z.object({
  id: uuid(),
  liquidacion_id: uuid(),
  inspector_id: uuid(),
  especialidad_revision: especialidadRevisionInspectorSchema.nullish(),
  liquidacion: liquidacionInspectorLiquidacionSchema.nullish(),
  inspector: inspectorAsignacionInspectorSchema.nullish(),
  periodo: z.string().nullish(),
  dictamen_revision: z.string().nullish(),
  fecha_presentacion: z.string().nullish(),
  fecha_revision: z.string().nullish(),
});

export type LiquidacionInspectorAsignacion = z.infer<
  typeof liquidacionInspectorAsignacionSchema
>;
