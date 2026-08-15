import { z } from "zod";

export const TramiteAccionSchema = z.enum(["PRIMERA_REVISION", "REVISION"]);
export type TramiteAccion = z.infer<typeof TramiteAccionSchema>;

export const TipoTramiteEdificacionesSchema = z.enum([
  "OBRA_NUEVA",
  "DEMOLICION",
  "AMPLIACION",
  "REMODELACION",
  "MODIFICACION_LICENCIA",
  "REINTEGRO",
  "PROYECTO_CON_PLANTAS_TIPICAS",
]);
export type TipoTramiteEdificaciones = z.infer<
  typeof TipoTramiteEdificacionesSchema
>;
