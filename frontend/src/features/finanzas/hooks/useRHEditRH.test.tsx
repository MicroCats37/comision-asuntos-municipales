/**
 * Mutaciones PATCH de los RH mensuales (modo edición) — endpoint e invalidación.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase (la ejecución
 * consolidada es la fase final de verificación).
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

const captured: {
  delegado?: UpdateProps;
  inspector?: UpdateProps;
} = {};

vi.mock("@/hooks", () => ({
  useApiCreate: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useApiUpdate: (props: UpdateProps) => {
    // El bucket se crea en la primera llamada: `captured` arranca sin claves,
    // por lo que leer `captured.delegado` antes de asignarlo devuelve undefined.
    const key = props.url?.includes("recibos-inspectores")
      ? "inspector"
      : "delegado";
    captured[key] = { ...props };
    return { mutateAsync: vi.fn(), isPending: false };
  },
}));

import { useActualizarRHDelegado } from "./useRHDelegadoMensual";
import { useActualizarRHInspector } from "./useRHInspectorMensual";

function createWrapper(client: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
  };
}

describe("useActualizarRHDelegado — PATCH del RH mensual de delegado", () => {
  it("apunta al recurso del recibo con método PATCH", () => {
    renderHook(() => useActualizarRHDelegado("rh-delegado-1"), {
      wrapper: createWrapper(new QueryClient()),
    });

    expect(captured.delegado?.url).toBe(
      "/finanzas/recibos-delegados/rh-delegado-1",
    );
    expect(captured.delegado?.method).toBe("PATCH");
  });

  it("invalida el listado de recibos de delegado al sincronizar", () => {
    const client = new QueryClient();
    const spy = vi.spyOn(client, "invalidateQueries");

    renderHook(() => useActualizarRHDelegado("rh-delegado-1"), {
      wrapper: createWrapper(client),
    });
    captured.delegado?.options?.onSuccess?.();

    expect(spy).toHaveBeenCalledWith({
      queryKey: ["finanzas", "recibos-delegados"],
    });
  });
});

describe("useActualizarRHInspector — PATCH del RH mensual de inspector", () => {
  it("apunta al recurso del recibo con método PATCH", () => {
    renderHook(() => useActualizarRHInspector("rh-inspector-1"), {
      wrapper: createWrapper(new QueryClient()),
    });

    expect(captured.inspector?.url).toBe(
      "/finanzas/recibos-inspectores/rh-inspector-1",
    );
    expect(captured.inspector?.method).toBe("PATCH");
  });

  it("invalida el listado de recibos de inspector al sincronizar", () => {
    const client = new QueryClient();
    const spy = vi.spyOn(client, "invalidateQueries");

    renderHook(() => useActualizarRHInspector("rh-inspector-1"), {
      wrapper: createWrapper(client),
    });
    captured.inspector?.options?.onSuccess?.();

    expect(spy).toHaveBeenCalledWith({
      queryKey: ["finanzas", "recibos-inspectores"],
    });
  });
});
