import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { configureToast } from "@/errors";
import { useGenericCreateMutation } from "../../cache/useGenericCreateMutation";
import { useApiCreate } from "../useApiCreate";
import { useApiDelete } from "../useApiDelete";
import { useApiUpdate } from "../useApiUpdate";

const { post, request, del } = vi.hoisted(() => ({
  post: vi.fn(),
  request: vi.fn(),
  del: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  default: {
    post,
    request,
    delete: del,
  },
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

describe("generic mutation hooks surface the backend success message", () => {
  it("shows exactly one toast with the envelope message on create", async () => {
    post.mockResolvedValue({
      data: {
        success: true,
        data: { id: 1 },
        message: "Recibo creado correctamente.",
      },
    });

    const { result } = renderHook(
      () => useApiCreate<{ success: boolean }, { name: string }>({ url: "/x" }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      await result.current.mutateAsync({ name: "ana" });
    });

    expect(successSpy).toHaveBeenCalledTimes(1);
    expect(successSpy).toHaveBeenCalledWith("Recibo creado correctamente.");
  });

  it("shows the nested message when the endpoint does not expose a top-level one", async () => {
    post.mockResolvedValue({
      data: {
        success: true,
        data: { id: 1, message: "Recibo de delegado eliminado correctamente." },
      },
    });

    const { result } = renderHook(
      () => useApiCreate<{ success: boolean }, { name: string }>({ url: "/x" }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      await result.current.mutateAsync({ name: "ana" });
    });

    expect(successSpy).toHaveBeenCalledTimes(1);
    expect(successSpy).toHaveBeenCalledWith(
      "Recibo de delegado eliminado correctamente.",
    );
  });

  it("does not toast when the endpoint answers without a message", async () => {
    post.mockResolvedValue({ data: { success: true, data: { id: 1 } } });

    const { result } = renderHook(
      () => useApiCreate<{ success: boolean }, { name: string }>({ url: "/x" }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      await result.current.mutateAsync({ name: "ana" });
    });

    expect(successSpy).not.toHaveBeenCalled();
  });

  it("shows the message on update", async () => {
    request.mockResolvedValue({
      data: {
        success: true,
        data: { id: 1 },
        message: "Actualizado correctamente.",
      },
    });

    const { result } = renderHook(
      () =>
        useApiUpdate<{ success: boolean }, { name: string }>({
          url: "/x",
          method: "PATCH",
        }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      await result.current.mutateAsync({ name: "ana" });
    });

    expect(successSpy).toHaveBeenCalledTimes(1);
    expect(successSpy).toHaveBeenCalledWith("Actualizado correctamente.");
  });

  it("shows the nested message on delete and returns the envelope", async () => {
    del.mockResolvedValue({
      data: {
        success: true,
        data: {
          id: 7,
          message: "Recibo de inspector eliminado correctamente.",
        },
      },
    });

    const { result } = renderHook(
      () =>
        useApiDelete<{ success: boolean; data: { id: number } }, string>({
          baseUrl: "/x",
        }),
      { wrapper: createWrapper() },
    );

    let payload: unknown;
    await act(async () => {
      payload = await result.current.mutateAsync("7");
    });

    expect(successSpy).toHaveBeenCalledTimes(1);
    expect(successSpy).toHaveBeenCalledWith(
      "Recibo de inspector eliminado correctamente.",
    );
    expect(payload).toEqual({
      success: true,
      data: { id: 7, message: "Recibo de inspector eliminado correctamente." },
    });
  });

  it("keeps the success toast even when the caller provides its own onSuccess", async () => {
    post.mockResolvedValue({
      data: {
        success: true,
        data: { id: 1 },
        message: "Institución creada correctamente.",
      },
    });
    const onSuccess = vi.fn();

    const { result } = renderHook(
      () =>
        useGenericCreateMutation<{ id: number }, { name: string }>({
          queryKey: ["entidades"],
          url: "/x",
          options: { onSuccess },
        }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      await result.current.mutateAsync({ name: "ana" });
    });

    expect(onSuccess).toHaveBeenCalledTimes(1);
    expect(successSpy).toHaveBeenCalledTimes(1);
    expect(successSpy).toHaveBeenCalledWith(
      "Institución creada correctamente.",
    );
  });

  it("reports the API error message instead of the raw Axios text", async () => {
    post.mockRejectedValue({
      response: {
        status: 400,
        data: {
          success: false,
          error: {
            code: "BUSINESS_ERROR",
            message: "No hay tarifas vigentes para edificaciones.",
          },
        },
      },
    });

    const { result } = renderHook(
      () => useApiCreate<{ success: boolean }, { name: string }>({ url: "/x" }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      await expect(
        result.current.mutateAsync({ name: "ana" }),
      ).rejects.toThrow();
    });

    await waitFor(() => expect(errorSpy).toHaveBeenCalledTimes(1));
    expect(errorSpy).toHaveBeenCalledWith(
      "No hay tarifas vigentes para edificaciones.",
    );
    expect(errorSpy).not.toHaveBeenCalledWith(
      expect.stringContaining("Request failed with status code"),
    );
  });
});
