/**
 * Hook para crear/upsert proyectista.
 * Usa useApiCreate genérico del proyecto.
 */

import { z } from "zod";
import { useApiCreate } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import type { ProyectistaInput } from "../types/proyectista";

/** Data payload schema */
const proyectistaPayloadSchema = z.object({
  id: z.string(),
  nombres: z.string(),
  apellidos: z.string(),
  cip: z.string().nullable(),
  dni: z.string().nullable(),
  cap: z.string().nullable(),
  creado: z.boolean(),
});

/** Full envelope schema using shared helper */
const proyectistaUpsertResponseSchema = apiResponseSchema(
  proyectistaPayloadSchema,
);

export function useProyectistaUpsert() {
  const mutation = useApiCreate<
    z.infer<typeof proyectistaUpsertResponseSchema>,
    ProyectistaInput
  >({
    url: "/proyectistas/",
    schema: proyectistaUpsertResponseSchema,
  });

  return mutation;
}
