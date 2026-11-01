/**
 * Hooks para cotización, creación y sincronización (PATCH) de RH Mensual de Inspector.
 * Endpoints:
 *   POST  /finanzas/recibos-inspectores/cotizar
 *   POST  /finanzas/recibos-inspectores/crear
 *   PATCH /finanzas/recibos-inspectores/{rh_id}
 */
import { useQueryClient } from "@tanstack/react-query";
import { useApiCreate, useApiUpdate } from "@/hooks";
import type {
  RHInspectorActualizarIn,
  RHInspectorCotizar,
  RHInspectorCotizarIn,
} from "../schemas/rh-inspector-mensual.schema";
import { RHInspectorCotizarResponseSchema } from "../schemas/rh-inspector-mensual.schema";

const cotizarResponseSchema = RHInspectorCotizarResponseSchema;
type CotizarResponseType = {
  success: boolean;
  data: RHInspectorCotizar | null;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  } | null;
};

const crearResponseSchema = RHInspectorCotizarResponseSchema;
type CrearResponseType = CotizarResponseType;

export function useCotizarRHInspector() {
  const mutation = useApiCreate<CotizarResponseType, RHInspectorCotizarIn>({
    url: "/finanzas/recibos-inspectores/cotizar",
    schema: cotizarResponseSchema,
    options: {
      onSuccess: () => {
        // Cotizar no invalida queries — solo prepara preview
      },
    },
  });

  return {
    ...mutation,
    cotizar: mutation.mutateAsync,
  };
}

/** Cotiza una edición sin contar el propio RH dentro del saldo consumido. */
export function useCotizarEdicionRHInspector(rhId: string) {
  const mutation = useApiCreate<CotizarResponseType, RHInspectorActualizarIn>({
    url: `/finanzas/recibos-inspectores/${rhId}/cotizar`,
    schema: cotizarResponseSchema,
  });

  return {
    ...mutation,
    cotizar: mutation.mutateAsync,
  };
}

export function useCrearRHInspector() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<CrearResponseType, RHInspectorCotizarIn>({
    url: "/finanzas/recibos-inspectores/crear",
    schema: crearResponseSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: ["finanzas", "recibos-inspectores"],
        });
      },
    },
  });

  return {
    ...mutation,
    crear: mutation.mutateAsync,
  };
}

/**
 * Sincroniza el conjunto final de detalles de un RH mensual de inspector.
 *
 * El `items` del payload ES el conjunto final: las filas con `detalle_id` se
 * conservan, las que no lo tienen se agregan y las persistidas ausentes se
 * retiran. Cualquier RH del inspector es editable.
 */
export function useActualizarRHInspector(rhId: string) {
  const queryClient = useQueryClient();

  const mutation = useApiUpdate<CrearResponseType, RHInspectorActualizarIn>({
    url: `/finanzas/recibos-inspectores/${rhId}`,
    method: "PATCH",
    schema: crearResponseSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: ["finanzas", "recibos-inspectores"],
        });
      },
    },
  });

  return {
    ...mutation,
    actualizar: mutation.mutateAsync,
  };
}
