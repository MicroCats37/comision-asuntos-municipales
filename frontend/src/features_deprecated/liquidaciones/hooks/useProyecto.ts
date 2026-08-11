/**
 * Hook para operaciones con proyectos.
 */
import { useMutation } from "@tanstack/react-query";
import type { z } from "zod";
import { notify } from "@/errors";
import { useApiCreate } from "@/hooks";
import type {
  EntidadSimple,
  ProyectoInput,
} from "../services/proyecto.service";
import {
  buscarProyecto,
  proyectoResponseSchema,
} from "../services/proyecto.service";

// Re-export types for convenience
export type {
  EntidadSimple,
  ProyectoResponse,
} from "../services/proyecto.service";

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

/**
 * Hook para buscar un proyecto por public_id usando GET /proyectos/buscar/{publicId}.
 * usa mutation en lugar de query para mantener API consistente con mutateAsync.
 */
export function useProyectoBuscar() {
  return useMutation({
    mutationFn: async (publicId: string) => {
      return buscarProyecto(publicId);
    },
    onError: (error: Error) => {
      notify.error(error.message || "Error al buscar el proyecto");
    },
  });
}
