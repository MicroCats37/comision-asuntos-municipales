/**
 * Zod schemas for Delegados Vigentes por Especialidad de Revision.
 * Endpoint: GET /liquidaciones/delegados/vigentes-por-especialidad?especialidad_revision_id=&fecha=
 *
 * Backend: DelegadosVigentesOut{ delegados: list[DelegadoVigentePorEspecialidadOut{id, nombre_completo, cip, tipo, especialidad: EspecialidadRevisionOpcionOut{id, nombre}}] }
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";
import { EspecialidadRevisionOptionSchema } from "./especialidades-revision.schema";

// ── DelegadoVigentePorEspecialidad ─────────────────────────────────────────────

export const DelegadoVigentePorEspecialidadSchema = z.object({
  id: z.string(),
  nombre_completo: z.string(),
  cip: z.string(),
  tipo: z.string(),
  especialidad: EspecialidadRevisionOptionSchema,
});
export type DelegadoVigentePorEspecialidad = z.infer<
  typeof DelegadoVigentePorEspecialidadSchema
>;

// ── DelegadosVigentesPorEspecialidadResponse ───────────────────────────────────

export const DelegadosVigentesPorEspecialidadResponseSchema = apiResponseSchema(
  z.object({
    delegados: z.array(DelegadoVigentePorEspecialidadSchema),
  }),
);
export type DelegadosVigentesPorEspecialidadResponse = z.infer<
  typeof DelegadosVigentesPorEspecialidadResponseSchema
>;
