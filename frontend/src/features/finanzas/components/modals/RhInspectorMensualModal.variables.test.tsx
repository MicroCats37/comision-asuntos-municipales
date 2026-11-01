/**
 * RhInspectorMensualModal — visibilidad de las variables financieras.
 *
 * Cubre las columnas calculadas por item (Sub Total, Descuento, Honorarios),
 * el encabezado de Descuento con el porcentaje cotizado y la conversión
 * fracción → porcentaje EXACTA UNA VEZ (0.20 → 20%, nunca 0.20%).
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase (la ejecución
 * consolidada es la fase final de verificación).
 */
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  cotizar: vi.fn(),
  refetch: vi.fn(),
}));

vi.mock("@/features/finanzas/hooks/useRHInspectorMensual", () => ({
  useCotizarRHInspector: () => ({ cotizar: mocks.cotizar, isPending: false }),
  useCrearRHInspector: () => ({ crear: vi.fn(), isPending: false }),
  useActualizarRHInspector: () => ({ actualizar: vi.fn(), isPending: false }),
}));

vi.mock("@/features/finanzas/hooks/useCandidatasInspector", () => ({
  useCandidatasInspector: () => ({
    data: {
      inspector_id: "inspector-1",
      inspector_nombre: "Inspector Uno",
      inspector_cip: "100001",
      inspector_dni: "100001",
      periodo: "2026-10",
      candidatos: [
        {
          liquidacion_inspector_id: "li-1",
          liquidacion_categoria_visitas_id: "lcv-1",
          liquidacion_general_id: "lg-1",
          expediente: "EXP-001",
          numero_revision: 1,
          fecha_registro: "2026-10-01",
          inspector_nombre: "Inspector Uno",
          inspector_cip: "100001",
          inspector_dni: "100001",
          especialidad_nombre: "Arquitectura",
          nombre_propietario: "Propietario Uno",
          cantidad_visitas: 4,
          inspecciones_pagadas: 1,
          saldo_disponible: 3,
          costo_por_inspeccion: 500,
          total_liquidacion: 2000,
          sub_total_liquidacion: 1000,
        },
      ],
      total: 1,
    },
    isLoading: false,
    isError: false,
    refetch: mocks.refetch,
  }),
}));

vi.mock("@/features/liquidaciones/hooks/useLiquidacionGeneralDetalle", () => ({
  useLiquidacionGeneralDetalle: () => ({ data: undefined, isLoading: false }),
}));

vi.mock("@/features/liquidaciones/components/detail", () => ({
  composeDetalleSections: () => null,
  getTipoDetalleSection: () => null,
  LiquidacionDetalleModal: () => null,
}));

vi.mock("@/errors", () => ({
  notify: { error: vi.fn(), success: vi.fn() },
}));

import {
  isFutureInspectorPeriod,
  RhInspectorMensualModal,
} from "./RhInspectorMensualModal";

const cotizarResult = {
  inspector: {
    id: "inspector-1",
    nombre_completo: "Inspector Uno",
    cip: "100001",
    dni: "100001",
  },
  periodo: 2026,
  mes: 10,
  items: [
    {
      exp_liqui: "EXP-001",
      liquidacion_inspector_id: "li-1",
      liquidacion_categoria_visitas_id: "lcv-1",
      nombre_propietario: "Propietario Uno",
      importe_bruto: 2000,
      inspecciones_programadas: 4,
      inspecciones_liquidadas: 2,
      inspecciones_pagadas_hasta_mes_anterior: 1,
      costo_por_inspeccion: 500,
      monto_contribuido: 1000,
      saldo_disponible: 3,
      saldo_restante: 1,
      sub_total: 1000,
      descuento: 200,
      honorarios: 800,
      tasa_descuento_aplicada: 0.2,
    },
  ],
  totales: {
    sub_total: 1000,
    descuento: 200,
    honorarios: 800,
    tasa_descuento_aplicada: 0.2,
  },
  escala_descuento_id: "escala-1",
  variables_calculo: {
    escala_id: "escala-1",
    escala_nombre: "Escala 2026",
    rango_aplicado: {
      monto_minimo: 8000,
      monto_maximo: 15000,
      porcentaje_descuento: 0.2,
    },
  },
};

/** Lleva el wizard hasta el paso 3 (previsualización de la cotización). */
async function irAlPasoResumen() {
  render(<RhInspectorMensualModal open onOpenChange={vi.fn()} />);

  fireEvent.change(screen.getByPlaceholderText("Ej. 12345"), {
    target: { value: "100001" },
  });
  fireEvent.click(screen.getByRole("button", { name: /Buscar Candidatas/ }));

  await waitFor(() => expect(screen.getByText("EXP-001")).toBeInTheDocument());

  fireEvent.click(screen.getByText("EXP-001"));
  fireEvent.click(screen.getByRole("button", { name: /Cotizar \(1\)/ }));

  await waitFor(() => expect(mocks.cotizar).toHaveBeenCalled());
  await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());
}

describe("RhInspectorMensualModal — variables financieras de la cotización", () => {
  beforeEach(() => {
    mocks.cotizar.mockReset();
    mocks.cotizar.mockResolvedValue({ data: cotizarResult });
    mocks.refetch.mockReset();
    mocks.refetch.mockResolvedValue({ data: undefined });
  });

  it("muestra las columnas calculadas por item", async () => {
    await irAlPasoResumen();

    const tabla = within(screen.getByRole("table"));

    expect(tabla.getByText("Sub Total")).toBeInTheDocument();
    expect(tabla.getByText("Honorarios")).toBeInTheDocument();
    expect(tabla.getByText("Descuento (20%)")).toBeInTheDocument();
  });

  it("detecta períodos posteriores al mes actual", () => {
    const now = new Date(2026, 9, 30);

    expect(isFutureInspectorPeriod(2026, 11, now)).toBe(true);
    expect(isFutureInspectorPeriod(2027, 1, now)).toBe(true);
    expect(isFutureInspectorPeriod(2026, 10, now)).toBe(false);
    expect(isFutureInspectorPeriod(2026, 9, now)).toBe(false);
  });

  it("actualiza las liquidadas y el saldo de la fila seleccionada", async () => {
    render(<RhInspectorMensualModal open onOpenChange={vi.fn()} />);

    fireEvent.change(screen.getByPlaceholderText("Ej. 12345"), {
      target: { value: "100001" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Buscar Candidatas/ }));
    await waitFor(() =>
      expect(screen.getByText("EXP-001")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByText("EXP-001"));

    expect(screen.getByTestId("selected-liquidated-lcv-1")).toHaveTextContent(
      "2",
    );
    expect(screen.getByTestId("selected-balance-lcv-1")).toHaveTextContent("2");

    fireEvent.change(document.getElementById("sel-cant-lcv-1") as HTMLElement, {
      target: { value: "2" },
    });

    expect(screen.getByTestId("selected-liquidated-lcv-1")).toHaveTextContent(
      "3",
    );
    expect(screen.getByTestId("selected-balance-lcv-1")).toHaveTextContent("1");
  });

  it("muestra el subtotal, el descuento y los honorarios de cada item", async () => {
    await irAlPasoResumen();

    const fila = screen.getByText("EXP-001").closest("tr");
    expect(fila).not.toBeNull();

    const celdas = within(fila as HTMLElement);
    // El monto contribuido y el sub total cotizado comparten valor.
    expect(celdas.getAllByText("S/ 1000.00")).toHaveLength(2);
    expect(celdas.getByText("- S/ 200.00")).toBeInTheDocument();
    expect(celdas.getByText("S/ 800.00")).toBeInTheDocument();
  });

  it("muestra el porcentaje cotizado en el encabezado de Descuento", async () => {
    await irAlPasoResumen();

    const tabla = within(screen.getByRole("table"));

    expect(tabla.getByText("Descuento (20%)")).toBeInTheDocument();
    expect(tabla.queryByText("Descuento (0.20%)")).not.toBeInTheDocument();
  });

  it("convierte la tasa fraccionaria a porcentaje una sola vez en el pie", async () => {
    await irAlPasoResumen();

    expect(screen.getByText(/Descuento \(20\.00%\)/)).toBeInTheDocument();
    expect(screen.queryByText(/0\.20%/)).not.toBeInTheDocument();
  });

  it("muestra la tasa de descuento del resumen como porcentaje", async () => {
    await irAlPasoResumen();

    expect(screen.getByText("20.00%")).toBeInTheDocument();
    expect(screen.queryByText("0.20%")).not.toBeInTheDocument();
  });
});
