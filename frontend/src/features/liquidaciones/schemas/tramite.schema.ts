import { z } from "zod";

export const TramiteAccionSchema = z.enum(["PRIMERA_REVISION", "REVISION"]);
export type TramiteAccion = z.infer<typeof TramiteAccionSchema>;

export const TipoTramiteEdificacionesSchema = z.enum(
  [
    "OBRA_NUEVA",
    "DEMOLICION",
    "AMPLIACION",
    "REMODELACION",
    "MODIFICACION_LICENCIA",
    "REINTEGRO",
    "VARIACION_PROYECTO_APROBADO",
    "PROYECTO_CON_PLANTAS_TIPICAS",
  ],
  { message: "Selecciona un tipo de trámite" },
);
export type TipoTramiteEdificaciones = z.infer<
  typeof TipoTramiteEdificacionesSchema
>;
