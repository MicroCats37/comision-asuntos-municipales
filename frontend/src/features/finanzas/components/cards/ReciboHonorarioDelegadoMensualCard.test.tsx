/**
 * Acción Editar sobre la card de RH mensual de delegado.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase (la ejecución
 * consolidada es la fase final de verificación).
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ReciboHonorarioDelegadoMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";
import { ReciboHonorarioDelegadoMensualCard } from "./ReciboHonorarioDelegadoMensualCard";

vi.mock("@/features/finanzas/pdf/printRhDelegadoMensual", () => ({
  printRhDelegadoMensual: vi.fn(),
}));

const item = {
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
  detalles: [],
  variables_calculo: {
    tasa_renta_cip: 0.25,
    tasa_aporte_codemu: 0.05,
    tasa_fondo_comun: 0.1,
  },
} as unknown as ReciboHonorarioDelegadoMensual;

describe("ReciboHonorarioDelegadoMensualCard — acción Editar", () => {
  it("expone la acción Editar y entrega el recibo al handler", () => {
    const onEdit = vi.fn();

    render(<ReciboHonorarioDelegadoMensualCard item={item} onEdit={onEdit} />);
    fireEvent.click(screen.getByRole("button", { name: "Editar recibo" }));

    expect(onEdit).toHaveBeenCalledTimes(1);
    expect(onEdit).toHaveBeenCalledWith(item);
  });

  it("no expone la acción Editar cuando no hay handler", () => {
    render(<ReciboHonorarioDelegadoMensualCard item={item} />);

    expect(
      screen.queryByRole("button", { name: "Editar recibo" }),
    ).not.toBeInTheDocument();
  });
});
