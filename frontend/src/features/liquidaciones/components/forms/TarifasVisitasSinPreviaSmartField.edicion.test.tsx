/**
 * Smart Field de tarifas/cotización de IO — semántica HISTÓRICA en edición.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la ejecución de
 * la suite queda reservada para la Fase 3 (verificación).
 *
 * Contrato cubierto (io-continuidad-visitas-ui-edit, Explorer D6):
 *  · En EDICIÓN la cotización va por `/{id}/cotizar-edicion`, que resuelve los
 *    valores históricos de `fecha_registro` — los mismos con los que el PATCH
 *    reprecia B. Con `/cotizar` (valores vigentes) el preview del panel de
 *    continuidad mentiría y la UI podría ofrecer una tarifa que el PATCH
 *    rechaza con 400.
 *  · En EDICIÓN las tarifas se LISTAN con `?fecha=fecha_registro` (tarifas
 *    vigentes a esa fecha), no con las vigentes de hoy.
 *  · En CREACIÓN el contrato vigente no cambia: `/cotizar` con el wrapper
 *    `liquidacion_especifica`.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, waitFor } from "@testing-library/react";
import { FormProvider, useForm } from "react-hook-form";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TarifasVisitasSinPreviaSmartField } from "./TarifasVisitasSinPreviaSmartField";

const { postMock, getMock } = vi.hoisted(() => ({
  postMock: vi.fn(),
  getMock: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  default: { post: postMock, get: getMock },
}));

// El debounce se neutraliza para que el preview sea determinista.
vi.mock("@/hooks/system/useDebounce", () => ({
  useDebounce: <T,>(value: T) => value,
}));

const QUOTE = {
  datos: {
    entrada: {
      datos: { cantidad_visitas: 3, categoria: "2" },
      tarifa: { tarifa_visitas_id: "tarifa-1" },
    },
    tarifa: { id: "tarifa-1", costo_por_visita: 250 },
    variables_financieras: {
      igv: { valor: 0.18 },
      uit: { valor: 5350 },
    },
  },
  calculo: { monto_bruto: 2500, subtotal: 2500, total: 2950 },
};

const TARIFAS = [{ id: "tarifa-1", costo_por_visita: 250, categoria: "2" }];

interface FormHarness {
  cantidad_visitas: number;
  categoria: string;
  tarifa_visitas_id: string;
}

function Harness({
  mode = "create",
  liquidacionId,
  fecha,
}: {
  mode?: "create" | "edit";
  liquidacionId?: string;
  fecha?: string;
}) {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  const methods = useForm<FormHarness>({
    defaultValues: {
      cantidad_visitas: 3,
      categoria: "2",
      tarifa_visitas_id: "tarifa-1",
    },
  });
  return (
    <QueryClientProvider client={client}>
      <FormProvider {...methods}>
        <TarifasVisitasSinPreviaSmartField
          methods={methods}
          onOpenInspector={() => undefined}
          mode={mode}
          liquidacionId={liquidacionId}
          fecha={fecha}
        />
      </FormProvider>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  postMock.mockReset();
  getMock.mockReset();
  postMock.mockResolvedValue({ data: { data: QUOTE } });
  getMock.mockResolvedValue({
    data: { success: true, data: { tarifas: TARIFAS } },
  });
});

describe("TarifasVisitasSinPreviaSmartField — cotización en edición", () => {
  it("usa /cotizar-edicion con el wrapper liquidacion_tipo", async () => {
    render(<Harness mode="edit" liquidacionId="liq-io-1" fecha="2026-01-15" />);

    await waitFor(() => expect(postMock).toHaveBeenCalled());
    expect(postMock).toHaveBeenCalledWith(
      "/liquidaciones/inspeccion-obra/liq-io-1/cotizar-edicion",
      {
        liquidacion_tipo: {
          modo_cotizacion: "NORMAL",
          datos: { cantidad_visitas: 3 },
          tarifa: { tarifa_visitas_id: "tarifa-1" },
        },
      },
    );
  });

  it("lista las tarifas vigentes a la fecha de registro (históricas)", async () => {
    render(
      <Harness
        mode="edit"
        liquidacionId="liq-io-1"
        fecha="2026-01-15T10:30:00Z"
      />,
    );

    await waitFor(() => expect(getMock).toHaveBeenCalled());
    const [url] = getMock.mock.calls[0];
    expect(url).toBe(
      "/liquidaciones/inspeccion-obra/tarifas/vigentes?fecha=2026-01-15",
    );
  });
});

describe("TarifasVisitasSinPreviaSmartField — cotización en creación", () => {
  it("mantiene el contrato vigente: /cotizar con liquidacion_especifica", async () => {
    render(<Harness mode="create" />);

    await waitFor(() => expect(postMock).toHaveBeenCalled());
    expect(postMock).toHaveBeenCalledWith(
      "/liquidaciones/inspeccion-obra/cotizar",
      {
        liquidacion_especifica: {
          modo_cotizacion: "NORMAL",
          datos: { cantidad_visitas: 3 },
          tarifa: { tarifa_visitas_id: "tarifa-1" },
        },
      },
    );
  });
});
