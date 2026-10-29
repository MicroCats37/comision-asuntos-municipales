/**
 * Preview de cotización PO con estrategias (Edificaciones).
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la ejecución de
 * la suite queda reservada para el Módulo 8 de la verificación final.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { UseFormReturn } from "react-hook-form";
import { FormProvider, useForm } from "react-hook-form";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  ESTRATEGIA_NORMAL,
  ESTRATEGIA_TOTAL,
} from "../../schemas/liquidacion-po-estrategia.schema";
import { CotizacionPorcentajeSmartField } from "./CotizacionPorcentajeSmartField";

const { postMock } = vi.hoisted(() => ({ postMock: vi.fn() }));

vi.mock("@/lib/api", () => ({
  default: { post: postMock },
}));

// El debounce se neutraliza para que el preview sea determinista: el
// comportamiento de debounce/cancelación vive en los hooks compartidos
// (`useDebounce` + `useLatestRequestGuard`) y no se reimplementa aquí.
vi.mock("@/hooks/system/useDebounce", () => ({
  useDebounce: <T,>(value: T) => value,
}));

const QUOTE = {
  valor_declarado: 1000000,
  porcentaje_liquidacion: 0.0015,
  derecho_minimo: 0,
  derecho_maximo: null,
  porcentaje_minimo_uit: 0,
  derecho_aplicado_id: "derecho-1",
  estrategia_cotizacion: "TARIFA_HABILITADAS_PARTICIPANTES",
  count_habilitadas: 3,
  total_explicito: null,
  porcentaje_tarifa: 0.0005,
  acumulacion: {
    porcentaje_acumulado: 0.001,
    subtotal_acumulado: 1000,
  },
  detalles: [
    {
      tarifa_id: "tarifa-1",
      especialidad: { id: "esp-1", nombre: "Estructuras" },
      porcentaje_aplicado: 0.0005,
      subtotal: 500,
    },
  ],
  total_subtotal: 1500,
  total: 1770,
};

const TARIFAS_ESPERADAS = [
  { tarifa_porcentaje_obra_id: "tarifa-1", especialidad_id: "esp-1" },
];

function Harness({
  estrategia = ESTRATEGIA_NORMAL,
  mode = "create",
  liquidacionId,
}: {
  estrategia?: string;
  mode?: "create" | "edit";
  liquidacionId?: string;
}) {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  const methods = useForm<any>({
    defaultValues: {
      estrategia_cotizacion: estrategia,
      valor_declarado: 1000000,
      total_explicito: estrategia === ESTRATEGIA_TOTAL ? 177 : undefined,
      tarifa_unica_id: "tarifa-1",
      especialidades_seleccionadas: ["esp-1"],
      tipo_tramite: "OBRA_NUEVA",
    },
  });
  return (
    <QueryClientProvider client={client}>
      <FormProvider {...methods}>
        <CotizacionPorcentajeSmartField
          methods={methods}
          tipo="edificaciones"
          hasTipoTramite
          soportaEstrategia
          mode={mode}
          liquidacionId={liquidacionId}
        />
      </FormProvider>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  postMock.mockReset();
  postMock.mockResolvedValue({ data: { data: QUOTE } });
});

describe("CotizacionPorcentajeSmartField — payload del preview", () => {
  it("envía la union discriminada NORMAL_SELECCIONADAS en create", async () => {
    render(<Harness />);

    await waitFor(() => expect(postMock).toHaveBeenCalled());
    expect(postMock).toHaveBeenCalledWith(
      "/liquidaciones/edificaciones/cotizar",
      {
        liquidacion_especifica: {
          estrategia_cotizacion: ESTRATEGIA_NORMAL,
          tipo_tramite: "OBRA_NUEVA",
          datos: { valor_declarado: 1000000 },
          tarifas: TARIFAS_ESPERADAS,
        },
      },
    );
  });

  it("envía el valor informativo y el total final en TOTAL_EXPLICITO", async () => {
    render(<Harness estrategia={ESTRATEGIA_TOTAL} />);

    await waitFor(() => expect(postMock).toHaveBeenCalled());
    const [, body] = postMock.mock.calls[0];
    const especifica = body.liquidacion_especifica;
    expect(especifica.estrategia_cotizacion).toBe(ESTRATEGIA_TOTAL);
    expect(especifica.datos).toEqual({
      valor_declarado: 1000000,
      total_explicito: 177,
    });
  });

  it("envía el bloque liquidacion_tipo en modo edit", async () => {
    render(<Harness mode="edit" liquidacionId="liq-1" />);

    await waitFor(() => expect(postMock).toHaveBeenCalled());
    expect(postMock).toHaveBeenCalledWith(
      "/liquidaciones/edificaciones/liq-1/cotizar-edicion",
      {
        liquidacion_tipo: {
          estrategia_cotizacion: ESTRATEGIA_NORMAL,
          tipo_tramite: "OBRA_NUEVA",
          datos: { valor_declarado: 1000000 },
          tarifas: TARIFAS_ESPERADAS,
        },
      },
    );
  });
});

describe("CotizacionPorcentajeSmartField — render del preview", () => {
  it("muestra subtotal, IGV y total", async () => {
    render(<Harness />);

    await waitFor(() => expect(screen.getByText("S/ 1770.00")).toBeTruthy());
    expect(screen.getByText("S/ 1500.00")).toBeTruthy();
    // IGV = total - subtotal (resta de los dos valores devueltos).
    expect(screen.getByText("S/ 270.00")).toBeTruthy();
  });

  it("muestra el snapshot de H (habilitadas)", async () => {
    render(<Harness />);

    await waitFor(() => expect(screen.getByText("Habilitadas (H):")).toBeTruthy());
    expect(screen.getByText("3")).toBeTruthy();
  });

  it("muestra el detalle por participante", async () => {
    render(<Harness />);

    await waitFor(() =>
      expect(screen.getByText("Detalle por participante")).toBeTruthy(),
    );
    expect(screen.getByText("Estructuras")).toBeTruthy();
    expect(screen.getByText("S/ 500.00")).toBeTruthy();
  });

  it("muestra la proyección de acumulación sin sugerir que se persiste", async () => {
    render(<Harness />);

    await waitFor(() =>
      expect(screen.getByText("Acumulación (proyección)")).toBeTruthy(),
    );
    expect(screen.getByText("Subtotal acumulado:")).toBeTruthy();
    expect(screen.getByText("S/ 1000.00")).toBeTruthy();
    expect(
      screen.getByText("El preview no persiste la acumulación."),
    ).toBeTruthy();
  });

  it("muestra el nombre de la estrategia devuelta por el backend", async () => {
    render(<Harness />);

    await waitFor(() => expect(screen.getByText("Estrategia:")).toBeTruthy());
    expect(
      screen.getByText("Tarifa habilitadas con participantes"),
    ).toBeTruthy();
  });
});
