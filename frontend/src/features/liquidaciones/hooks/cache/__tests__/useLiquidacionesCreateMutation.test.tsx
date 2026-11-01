import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { configureToast } from "@/errors";
import { useLiquidacionesCreateMutation } from "../useLiquidacionesCreateMutation";

const { post } = vi.hoisted(() => ({ post: vi.fn() }));

vi.mock("@/lib/api", () => ({
  default: { post },
}));

const successSpy = vi.fn();
const errorSpy = vi.fn();

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  configureToast(errorSpy, successSpy);
});

describe("useLiquidacionesCreateMutation", () => {
  it("surfaces the backend success message of a liquidacion creation", async () => {
    post.mockResolvedValue({
      data: {
        success: true,
        message: "Liquidación de edificación creada correctamente.",
        data: { liquidacion_general: { id: "abc" } },
      },
    });

    const { result } = renderHook(
      () =>
        useLiquidacionesCreateMutation<{ area: number }>({
          tipoQueryKey: ["liquidaciones", "edificaciones"],
          url: "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      await result.current.mutateAsync({ area: 10 });
    });

    expect(successSpy).toHaveBeenCalledTimes(1);
    expect(successSpy).toHaveBeenCalledWith(
      "Liquidación de edificación creada correctamente.",
    );
  });

  it("does not toast when the endpoint answers without a message", async () => {
    post.mockResolvedValue({
      data: {
        success: true,
        data: { liquidacion_general: { id: "abc" } },
      },
    });

    const { result } = renderHook(
      () =>
        useLiquidacionesCreateMutation<{ area: number }>({
          tipoQueryKey: ["liquidaciones", "edificaciones"],
          url: "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      await result.current.mutateAsync({ area: 10 });
    });

    expect(successSpy).not.toHaveBeenCalled();
  });
});
