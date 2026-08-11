/**
 * Hook para obtener distritos con filtros.
 * Usa useApiQuery genérico del proyecto.
 */
import { useApiQuery } from "@/hooks";
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

/** Nested schemas for distrito payload */
const departamentoSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});

const provinciaSchema = z.object({
  id: z.string(),
  nombre: z.string(),
  departamento: departamentoSchema,
});

/** Data payload schema for distrito items */
const distritoPayloadSchema = z.object({
  id: z.string(),
  nombre: z.string(),
  ubigeo: z.string(),
  provincia: provinciaSchema,
  departamento: departamentoSchema,
});

/** Full envelope schema using shared helper */
const distritoResponseSchema = apiResponseSchema(
  z.object({
    items: z.array(distritoPayloadSchema),
    total: z.number(),
  }),
);

export interface DistritoOption {
  id: string;
  nombre: string;
  ubigeo: string;
  provincia: {
    id: string;
    nombre: string;
    departamento: {
      id: string;
      nombre: string;
    };
  };
  departamento: {
    id: string;
    nombre: string;
  };
}

interface UseDistritosProps {
  search?: string;
  provincia_id?: string;
  departamento_id?: string;
  enabled?: boolean;
}

export function useDistritos({
  search,
  provincia_id,
  departamento_id,
  enabled = true,
}: UseDistritosProps = {}) {
  // Build params, excluding undefined values
  const params: Record<string, unknown> = {};
  if (search) params.search = search;
  if (provincia_id) params.provincia_id = provincia_id;
  if (departamento_id) params.departamento_id = departamento_id;

  const queryKey = params
    ? ["distritos", params]
    : ["distritos"];

  return useApiQuery<
    z.infer<typeof distritoResponseSchema>,
    DistritoOption[]
  >({
    queryKey,
    url: "/entidades/ubigeo/distritos",
    schema: distritoResponseSchema,
    params: Object.keys(params).length > 0 ? params : undefined,
    queryOptions: {
      enabled,
      select: (data) => {
        if (!data.data?.items) return [];
        return data.data.items;
      },
    },
  });
}
