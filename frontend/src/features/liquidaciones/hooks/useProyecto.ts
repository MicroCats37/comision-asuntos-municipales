/**
 * Hook para operaciones con proyectos.
 */
import { useApiCreate } from "@/hooks";
import { z } from "zod";
import type { EntidadSimple, ProyectoInput } from "../services/proyecto.service";
import { proyectoResponseSchema } from "../services/proyecto.service";

// Re-export types for convenience
export type { EntidadSimple } from "../services/proyecto.service";
export type { ProyectoResponse } from "../services/proyecto.service";

export function useProyectoCrear() {
  const mutation = useApiCreate<
    z.infer<typeof proyectoResponseSchema>,
    ProyectoInput
  >({
    url: "/proyectos/",
    schema: proyectoResponseSchema,
  });

  return mutation;
}

export function useProyectoBuscar() {
  const mutation = useApiCreate<
    z.infer<typeof proyectoResponseSchema>,
    string
  >({
    url: "/proyectos/buscar/",
    schema: proyectoResponseSchema,
  });

  return mutation;
}
