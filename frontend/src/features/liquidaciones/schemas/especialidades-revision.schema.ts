/**
 * Zod schemas for Especialidades de Revision.
 * Endpoints:
 *   GET /liquidaciones/especialidades-revision
 *
 * Backend: EspecialidadesRevisionOut{ especialidades: list[EspecialidadRevisionOpcionOut{id, nombre}] }
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

// ── EspecialidadRevisionOption ────────────────────────────────────────────────

export const EspecialidadRevisionOptionSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});
export type EspecialidadRevisionOption = z.infer<
  typeof EspecialidadRevisionOptionSchema
>;

// ── EspecialidadesRevisionResponse ────────────────────────────────────────────

export const EspecialidadesRevisionResponseSchema = apiResponseSchema(
  z.object({
    especialidades: z.array(EspecialidadRevisionOptionSchema),
  }),
);
export type EspecialidadesRevisionResponse = z.infer<
  typeof EspecialidadesRevisionResponseSchema
>;
