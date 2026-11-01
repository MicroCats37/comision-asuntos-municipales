/**
 * Mutaciones de RH Trimestral (Repartición Estacional) — endpoint e invalidación.
 *
 * Cubre el PATCH de edición y el DELETE (soft-delete): ambos deben apuntar al
 * recurso correcto y invalidar el listado de reparticiones.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

type UpdateProps = {
  url?: string;
  method?: string;
  options?: { onSuccess?: () => void };
};

type DeleteProps = {
  baseUrl?: string;
  options?: { onSuccess?: () => void };
};

const captured: {
  update?: UpdateProps;
  remove?: DeleteProps;
} = {};

vi.mock("@/hooks", () => ({
  useApiUpdate: (props: UpdateProps) => {
    captured.update = { ...props };
    return { mutateAsync: vi.fn(), isPending: false };
  },
  useApiDelete: (props: DeleteProps) => {
    captured.remove = { ...props };
    return { mutateAsync: vi.fn(), isPending: false };
  },
}));

import { useActualizarRHReparticionEstacional } from "./useActualizarRHReparticionEstacional";
import { useEliminarRHReparticionEstacional } from "./useEliminarRHReparticionEstacional";

function createWrapper(client: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
  };
}

describe("useActualizarRHReparticionEstacional — PATCH de la trimestral", () => {
  it("apunta al recurso de la repartición con método PATCH", () => {
    renderHook(() => useActualizarRHReparticionEstacional("reparticion-1"), {
      wrapper: createWrapper(new QueryClient()),
    });

    expect(captured.update?.url).toBe(
      "/finanzas/reparticiones-estacionales/reparticion-1",
    );
    expect(captured.update?.method).toBe("PATCH");
  });

  it("invalida el listado de reparticiones al editar", () => {
    const client = new QueryClient();
    const spy = vi.spyOn(client, "invalidateQueries");

    renderHook(() => useActualizarRHReparticionEstacional("reparticion-1"), {
      wrapper: createWrapper(client),
    });
    captured.update?.options?.onSuccess?.();

    expect(spy).toHaveBeenCalledWith({
      queryKey: ["finanzas", "reparticiones-estacionales"],
    });
  });
});

describe("useEliminarRHReparticionEstacional — DELETE de la trimestral", () => {
  it("apunta al recurso de la repartición", () => {
    renderHook(() => useEliminarRHReparticionEstacional(), {
      wrapper: createWrapper(new QueryClient()),
    });

    expect(captured.remove?.baseUrl).toBe(
      "/finanzas/reparticiones-estacionales",
    );
  });

  it("invalida el listado de reparticiones al eliminar", () => {
    const client = new QueryClient();
    const spy = vi.spyOn(client, "invalidateQueries");

    renderHook(() => useEliminarRHReparticionEstacional(), {
      wrapper: createWrapper(client),
    });
    captured.remove?.options?.onSuccess?.();

    expect(spy).toHaveBeenCalledWith({
      queryKey: ["finanzas", "reparticiones-estacionales"],
    });
  });
});
