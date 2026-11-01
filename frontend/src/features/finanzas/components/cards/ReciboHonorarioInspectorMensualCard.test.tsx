/**
 * Acción Editar sobre la card de RH mensual de inspector.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase (la ejecución
 * consolidada es la fase final de verificación).
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ReciboHonorarioInspectorMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";
import { ReciboHonorarioInspectorMensualCard } from "./ReciboHonorarioInspectorMensualCard";

vi.mock("@/features/finanzas/pdf/printRhInspectorMensual", () => ({
  printRhInspectorMensual: vi.fn(),
}));

const item = {
  id: "rh-inspector-1",
  periodo: 2026,
  mes: 10,
  fecha_registro: "2026-10-31T10:00:00",
  inspector: {
    id: "inspector-1",
    cip: "200002",
    dni: "200002",
    nombre_completo: "Inspector Dos",
  },
  totales: {
    inspecciones_programadas: 5,
    inspecciones_liquidadas: 2,
    inspecciones_pagadas_hasta_mes_anterior: 1,
    saldo_restante: 2,
    sub_total: 1000,
    descuento: 200,
    honorarios: 800,
    tasa_descuento_aplicada: 0.2,
  },
  detalles: [],
  variables_calculo: {
    escala_id: "escala-1",
    escala_nombre: "Escala 2026",
    rango_aplicado: {
      monto_minimo: 0,
      monto_maximo: 10000,
      porcentaje_descuento: 0.2,
    },
  },
} as unknown as ReciboHonorarioInspectorMensual;

describe("ReciboHonorarioInspectorMensualCard — acción Editar", () => {
  it("expone la acción Editar y entrega el recibo al handler", () => {
    const onEdit = vi.fn();

    render(<ReciboHonorarioInspectorMensualCard item={item} onEdit={onEdit} />);
    fireEvent.click(screen.getByRole("button", { name: /editar/i }));

    expect(onEdit).toHaveBeenCalledTimes(1);
    expect(onEdit).toHaveBeenCalledWith(item);
  });

  it("no expone la acción Editar cuando no hay handler", () => {
    render(<ReciboHonorarioInspectorMensualCard item={item} />);

    expect(
      screen.queryByRole("button", { name: /editar/i }),
    ).not.toBeInTheDocument();
  });
});
