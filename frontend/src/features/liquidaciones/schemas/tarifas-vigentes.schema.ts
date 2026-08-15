import { z } from "zod";

// ── Motor porcentaje (PorcentajeObra: edificaciones, taludes, impacto-vial) ───

export const TarifasVigentesPorcentajeSchema = z.object({
  tarifas: z.array(
    z.object({
      id: z.string(),
      porcentaje_liquidacion: z.number(),
    }),
  ),
  especialidades_disponibles: z.array(
    z.object({
      id: z.string(),
      codigo: z.string().nullable(),
      nombre: z.string(),
    }),
  ),
});
export type TarifasVigentesPorcentajeData = z.infer<
  typeof TarifasVigentesPorcentajeSchema
>;

// ── Motor m2 (Habilitación Urbana, Mecánica de Suelos) ───────────────────────

export const TarifasVigentesM2Schema = z.object({
  tarifa_vigente: z
    .object({
      datos: z.object({ id: z.string(), costo_por_m2: z.number() }).nullable(),
    })
    .nullable(),
  derecho_vigente: z
    .object({
      datos: z
        .object({
          id: z.string(),
          derecho_minimo: z.number(),
          derecho_maximo: z.number(),
        })
        .nullable(),
    })
    .nullable(),
});
export type TarifasVigentesM2Data = z.infer<typeof TarifasVigentesM2Schema>;

// ── Motor visitas (Inspección de Obra) ───────────────────────────────────────

export const TarifasVigentesVisitasSchema = z.object({
  tarifas: z.array(
    z.object({
      id: z.string(),
      costo_por_visita: z.number(),
      categoria: z.string(),
      // No presentes en todos los backends — opcionales defensivos
      visitas_minimas: z.number().optional(),
      habilitada: z.boolean().optional(),
    }),
  ),
});
export type TarifasVigentesVisitasData = z.infer<
  typeof TarifasVigentesVisitasSchema
>;
