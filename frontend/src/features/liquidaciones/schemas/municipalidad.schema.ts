import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

/** Municipalidad (opción para select) — GET /entidades/municipalidades */
export const MunicipalidadSchema = z.object({
  id: z.string(),
  nombre: z.string(),
  codigo: z.string().nullable(),
  provincia: z
    .object({
      id: z.string(),
      nombre: z.string(),
    })
    .nullable(),
  distrito: z
    .object({
      id: z.string(),
      nombre: z.string(),
    })
    .nullable(),
});
export type MunicipalidadData = z.infer<typeof MunicipalidadSchema>;

/** Envelope: la API puede devolver la lista directa o `{ items: [...] }`. */
export const MunicipalidadesResponseSchema = apiResponseSchema(
  z.union([
    z.array(MunicipalidadSchema),
    z.object({ items: z.array(MunicipalidadSchema) }),
  ]),
);
export type MunicipalidadesResponse = z.infer<
  typeof MunicipalidadesResponseSchema
>;
