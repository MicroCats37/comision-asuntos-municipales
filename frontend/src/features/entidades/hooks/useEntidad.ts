/**
 * Hook para crear/upsert entidad.
 * Usa useApiCreate genérico del proyecto.
 */

import type { z } from "zod";
import { useApiCreate, useApiQuery } from "@/hooks";
import {
  EntidadBuscarResponseSchema,
  EntidadResponseSchema,
} from "../schemas/entidad.schema";
import type {
  EntidadInstitucion,
  EntidadPersonaNatural,
  EntidadResult,
} from "../types/entidad";

export function useInstitucionUpsert() {
  const mutation = useApiCreate<
    z.infer<typeof EntidadResponseSchema>,
    EntidadInstitucion
  >({
    url: "/entidades/instituciones",
    schema: EntidadResponseSchema,
  });

  return mutation;
}

export function usePersonaNaturalUpsert() {
  const mutation = useApiCreate<
    z.infer<typeof EntidadResponseSchema>,
    EntidadPersonaNatural
  >({
    url: "/entidades/personas-naturales",
    schema: EntidadResponseSchema,
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
    z.infer<typeof EntidadBuscarResponseSchema>,
    EntidadResult | null
  >({
    queryKey: ["entidades", "buscar", numero_documento],
    url: numero_documento ? "/entidades/buscar" : null,
    schema: EntidadBuscarResponseSchema,
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
