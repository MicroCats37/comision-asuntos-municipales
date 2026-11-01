import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { useForm } from "react-hook-form";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CotizacionM2SmartField } from "../CotizacionM2SmartField";

const { post } = vi.hoisted(() => ({ post: vi.fn() }));

vi.mock("@/lib/api", () => ({
  default: { post },
}));

beforeEach(() => {
  vi.clearAllMocks();
});

function renderSmartField(legacy = false) {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });

  function Harness() {
    const methods = useForm({
      defaultValues: {
        area_solicitada: 10,
        tarifa_m2_id: "tarifa-1",
        fecha_registro: legacy ? "2023-06-15" : undefined,
      },
    });
    return (
      <CotizacionM2SmartField
        methods={methods}
        mode={legacy ? "legacy" : "create"}
      />
    );
  }

  return render(
    <QueryClientProvider client={queryClient}>
      <Harness />
    </QueryClientProvider>,
  );
}

describe("CotizacionM2SmartField", () => {
  it("cotiza con la fecha efectiva en modo legacy", async () => {
    post.mockResolvedValue({ data: { data: { subtotal: 10, total: 11.8 } } });

    renderSmartField(true);

    await waitFor(() => expect(post).toHaveBeenCalled());
    expect(post.mock.calls[0][0]).toBe(
      "/liquidaciones/habilitacion-urbana/cotizar?fecha=2023-06-15",
    );
  });

  it("shows the API message instead of the raw Axios error text", async () => {
    post.mockRejectedValue({
      response: {
        status: 400,
        data: {
          success: false,
          error: {
            code: "BUSINESS_ERROR",
            message: "No hay tarifas vigentes para habilitación urbana.",
          },
        },
      },
    });

    renderSmartField();

    await waitFor(
      () => {
        expect(
          screen.getByText("No hay tarifas vigentes para habilitación urbana."),
        ).toBeInTheDocument();
      },
      { timeout: 3000 },
    );

    expect(screen.queryByText(/Request failed with status code/i)).toBeNull();
  });
});
