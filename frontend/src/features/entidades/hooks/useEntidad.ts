/**
 * Hook para crear/upsert entidad.
 * Usa useApiCreate genérico del proyecto.
 */
import { useApiCreate, useApiQuery } from "@/hooks";
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";
import type { EntidadInstitucion, EntidadPersonaNatural, EntidadResult } from "../types/entidad";

/** Shared data payload schema for entidad */
const entidadDataPayloadSchema = z.object({
  id: z.string(),
  tipo_documento: z.string(),
  numero_documento: z.string(),
  razon_social: z.string().nullable(),
  nombres: z.string().nullable(),
  apellidos: z.string().nullable(),
  nombre_completo: z.string(),
  direccion: z.string().nullable(),
  distrito_id: z.string().nullable(),
  activo: z.boolean(),
});

/** Full envelope schema for upsert response (includes 'creado' field) */
const entidadUpsertPayloadSchema = entidadDataPayloadSchema.extend({
  creado: z.boolean(),
});

const entidadResponseSchema = apiResponseSchema(entidadUpsertPayloadSchema);
const entidadBuscarResponseSchema = apiResponseSchema(entidadDataPayloadSchema);

export function useInstitucionUpsert() {
  const mutation = useApiCreate<
    z.infer<typeof entidadResponseSchema>,
    EntidadInstitucion
  >({
    url: "/entidades/instituciones",
    schema: entidadResponseSchema,
  });

  return mutation;
}

export function usePersonaNaturalUpsert() {
  const mutation = useApiCreate<
    z.infer<typeof entidadResponseSchema>,
    EntidadPersonaNatural
  >({
    url: "/entidades/personas-naturales",
    schema: entidadResponseSchema,
  });

  return mutation;
}

interface UseEntidadBuscarProps {
  numero_documento: string;
  enabled?: boolean;
}

export function useEntidadBuscar({
  numero_documento,
  enabled = true,
}: UseEntidadBuscarProps) {
  return useApiQuery<
    z.infer<typeof entidadBuscarResponseSchema>,
    EntidadResult | null
  >({
    queryKey: ["entidades", "buscar", numero_documento],
    url: numero_documento ? "/entidades/buscar" : null,
    schema: entidadBuscarResponseSchema,
    params: numero_documento ? { numero_documento } : undefined,
    queryOptions: {
      enabled: enabled && !!numero_documento,
      select: (data) => {
        if (!data.data) return null;
        return data.data as EntidadResult;
      },
    },
  });
}
