import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

export const ProvinciaBasicSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});
export type ProvinciaBasicData = z.infer<typeof ProvinciaBasicSchema>;

export const DepartamentoBasicSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});
export type DepartamentoBasicData = z.infer<typeof DepartamentoBasicSchema>;

/** Distrito desde ubigeo — GET /entidades/ubigeo/distritos */
export const DistritoSchema = z.object({
  id: z.string(),
  nombre: z.string(),
  ubigeo: z.string(),
  provincia: ProvinciaBasicSchema,
  departamento: DepartamentoBasicSchema,
});
export type DistritoData = z.infer<typeof DistritoSchema>;

export const DistritosResponseSchema = apiResponseSchema(
  z.object({
    items: z.array(DistritoSchema),
    total: z.number(),
  }),
);
export type DistritosResponse = z.infer<typeof DistritosResponseSchema>;

/** Vista aplanada para selects de distritos. */
export type DistritoOption = {
  id: string;
  nombre: string;
  provinciaNombre: string;
  departamentoNombre: string;
};
