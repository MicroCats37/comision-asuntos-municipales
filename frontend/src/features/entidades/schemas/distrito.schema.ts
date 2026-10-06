import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

export const DepartamentoSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});
export type DepartamentoData = z.infer<typeof DepartamentoSchema>;

export const ProvinciaSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});
export type ProvinciaData = z.infer<typeof ProvinciaSchema>;

/** Distrito desde ubigeo — GET /entidades/ubigeo/distritos */
export const DistritoSchema = z.object({
  id: z.string(),
  nombre: z.string(),
  ubigeo: z.string(),
  provincia: ProvinciaSchema,
  departamento: DepartamentoSchema,
});
export type DistritoData = z.infer<typeof DistritoSchema>;
export type DistritoOption = DistritoData;

export const DistritosResponseSchema = apiResponseSchema(
  z.object({
    items: z.array(DistritoSchema),
    total: z.number(),
  }),
);
export type DistritosResponse = z.infer<typeof DistritosResponseSchema>;
