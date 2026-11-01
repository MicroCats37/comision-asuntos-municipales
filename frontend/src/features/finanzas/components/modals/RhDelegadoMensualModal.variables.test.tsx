/**
 * RhDelegadoMensualModal — encabezados con los porcentajes cotizados.
 *
 * Cubre que la tabla de cotización del delegado muestre en sus encabezados
 * los porcentajes cotizados de Renta CIP, Aporte CODEMU y Fondo Común.
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
import type { ReciboHonorarioDelegadoMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";

const mocks = vi.hoisted(() => ({
  cotizar: vi.fn(),
  rowsByDetalleId: new Map<string, unknown>([
    [
      "detalle-1",
      {
        id: "detalle-1",
        imp_bruto: 1000,
        delegado_liquidacion: {
          id: "asignacion-1",
          liquidacion: {
            id: "lg-1",
            expediente: "EXP-001",
            numero_revision: 2,
            numero: 77,
            municipalidad: {
              id: "municipalidad-1",
              nombre: "Municipalidad Uno",
            },
            tipo_liquidacion: {
              id: "tipo-1",
              codigo: "EDIFICACION",
              nombre: "Edificación",
            },
          },
          especialidad: { id: "esp-1", nombre: "Arquitectura" },
        },
      },
    ],
  ]),
}));

vi.mock("@/features/finanzas/hooks/useRHEditDelegadoDetalleRows", () => ({
  useRHEditDelegadoDetalleRows: () => ({
    rowsByDetalleId: mocks.rowsByDetalleId,
    isLoading: false,
  }),
}));

vi.mock("@/features/finanzas/hooks/useRHDelegadoMensual", () => ({
  useCotizarRHDelegado: () => ({ cotizar: mocks.cotizar, isPending: false }),
  useCrearRHDelegado: () => ({ crear: vi.fn(), isPending: false }),
  useActualizarRHDelegado: () => ({ actualizar: vi.fn(), isPending: false }),
}));

vi.mock("@/features/finanzas/hooks/useCandidatasDelegado", () => ({
  useCandidatasDelegado: () => ({
    data: null,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
}));

vi.mock("@/features/liquidaciones/hooks/useLiquidacionGeneralDetalle", () => ({
  useLiquidacionGeneralDetalle: () => ({ data: undefined, isLoading: false }),
}));

vi.mock(
  "@/features/finanzas/components/fields/DelegadoOperacionSmartField",
  () => ({
    DelegadoOperacionSmartField: () => null,
  }),
);

vi.mock("@/features/liquidaciones/components/detail", () => ({
  composeDetalleSections: () => null,
  getTipoDetalleSection: () => null,
  LiquidacionDetalleModal: () => null,
}));

vi.mock("@/errors", () => ({
  notify: { error: vi.fn(), success: vi.fn() },
}));

import { RhDelegadoMensualModal } from "./RhDelegadoMensualModal";

const rh = {
  id: "rh-delegado-1",
  periodo: 2026,
  mes: 10,
  fecha_registro: "2026-10-31T10:00:00",
  delegado: {
    id: "delegado-1",
    cip: "100001",
    dni: "100001",
    nombre_completo: "Delegado Uno",
  },
  totales: {
    sub_total: 1000,
    renta_cip: 250,
    aporte_codemu: 50,
    fondo_comun: 100,
    neto_honorario: 600,
  },
  detalles: [
    {
      liquidacion_delegado_id: "asignacion-1",
      detalle_id: "detalle-1",
      expediente: "EXP-001",
      numero_revision: 2,
      total_liquidacion: 1200,
      sub_total_liquidacion: 1000,
      numero_rh: "RH-001",
      imp_bruto: 1000,
      renta_cip: 250,
      aporte_codemu: 50,
      fondo_comun: 100,
      neto_honorario: 600,
      periodo: 2026,
      mes: 10,
      dictamen_revision: "APROBADO",
      fecha_presentacion: "2026-10-05",
      fecha_revision: "2026-10-10",
      liquidacion_especifica_numero: 77,
    },
  ],
  variables_calculo: {
    tasa_renta_cip: 0.25,
    tasa_aporte_codemu: 0.05,
    tasa_fondo_comun: 0.1,
  },
  delegado_operacion_id: "operacion-1",
  delegado_operacion_context: {
    id: "operacion-1",
    municipalidad_id: "municipalidad-1",
    municipalidad_nombre: "Municipalidad Uno",
    tipo_liquidacion_id: "tipo-1",
    tipo_liquidacion_codigo: "EDIFICACION",
    tipo_liquidacion_nombre: "Edificación",
    especialidad_id: "esp-1",
    especialidad_nombre: "Arquitectura",
    tipo: "TITULAR",
  },
} as unknown as ReciboHonorarioDelegadoMensual;

const cotizarResult = {
  delegado: {
    id: "delegado-1",
    nombre_completo: "Delegado Uno",
    cip: "100001",
  },
  periodo: 2026,
  mes: 10,
  items: [{ exp_liqui: "EXP-001", imp_bruto: 1000 }],
  totales: {
    sub_total: 1000,
    renta_cip: 250,
    aporte_codemu: 50,
    fondo_comun: 100,
    neto_honorario: 600,
  },
  variables_calculo: {
    tasa_renta_cip: 0.25,
    tasa_aporte_codemu: 0.05,
    tasa_fondo_comun: 0.1,
  },
};

/** Lleva el wizard hasta el paso 3 (previsualización de la cotización). */
async function irAlPasoResumen() {
  render(
    <RhDelegadoMensualModal open onOpenChange={vi.fn()} editContext={{ rh }} />,
  );

  fireEvent.click(screen.getByRole("button", { name: /Cotizar \(1\)/ }));

  await waitFor(() => expect(mocks.cotizar).toHaveBeenCalled());
  await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());
}

describe("RhDelegadoMensualModal — porcentajes en los encabezados", () => {
  beforeEach(() => {
    mocks.cotizar.mockReset();
    mocks.cotizar.mockResolvedValue({ data: cotizarResult });
  });

  it("muestra el porcentaje cotizado de Renta CIP en el encabezado", async () => {
    await irAlPasoResumen();

    const tabla = within(screen.getByRole("table"));

    expect(tabla.getByText("Renta CIP (25%)")).toBeInTheDocument();
  });

  it("muestra el porcentaje cotizado de Aporte CODEMU en el encabezado", async () => {
    await irAlPasoResumen();

    const tabla = within(screen.getByRole("table"));

    expect(tabla.getByText("Aporte Codemu (5%)")).toBeInTheDocument();
  });

  it("muestra el porcentaje cotizado de Fondo Común en el encabezado", async () => {
    await irAlPasoResumen();

    const tabla = within(screen.getByRole("table"));

    expect(tabla.getByText("Fondo Común (10%)")).toBeInTheDocument();
  });

  it("muestra la fracción como porcentaje y nunca como 0.25%", async () => {
    await irAlPasoResumen();

    expect(screen.queryByText(/Renta CIP \(0\.25%\)/)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/Aporte Codemu \(0\.05%\)/),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/Fondo Común \(0\.1%\)/)).not.toBeInTheDocument();
  });
});
