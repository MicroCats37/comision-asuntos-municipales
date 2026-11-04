/**
 * LiquidacionFiltroModal — filtros del listado de liquidaciones.
 *
 * Cubre:
 * - se retiraron "Creado Por" y "N° Revisiones" del panel;
 * - el panel expone "N° Documento Entidad" y los campos del comprobante
 *   vigente (serie + número);
 * - al aplicar, el payload NO lleva `creado_por` ni `numero_revisiones`.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

/** El panel consume los catálogos de municipalidades y distritos. */
vi.mock("../../hooks/useMunicipalidades", () => ({
  useMunicipalidades: () => ({ data: [], isLoading: false }),
}));

vi.mock("../../hooks/useDistritos", () => ({
  useDistritos: () => ({ data: [], isLoading: false }),
}));

import { LiquidacionFiltroModal } from "./LiquidacionFiltroModal";

describe("LiquidacionFiltroModal", () => {
  it("no muestra los controles de creador ni de número de revisiones", () => {
    render(
      <LiquidacionFiltroModal
        open
        onOpenChange={vi.fn()}
        onApply={vi.fn()}
      />,
    );

    expect(screen.queryByText("Creado Por")).not.toBeInTheDocument();
    expect(screen.queryByText("N° Revisiones")).not.toBeInTheDocument();
  });

  it("expone los filtros de documento y de comprobante vigente", () => {
    render(
      <LiquidacionFiltroModal
        open
        onOpenChange={vi.fn()}
        onApply={vi.fn()}
      />,
    );

    expect(screen.getByText("N° Documento Entidad")).toBeInTheDocument();
    expect(screen.getByText("Comprobante — Serie")).toBeInTheDocument();
    expect(screen.getByText("Comprobante — Número")).toBeInTheDocument();
  });

  it("envía los filtros nuevos y omite los retirados", async () => {
    const onApply = vi.fn();
    render(
      <LiquidacionFiltroModal
        open
        onOpenChange={vi.fn()}
        onApply={onApply}
      />,
    );

    fireEvent.change(screen.getByLabelText("N° Documento Entidad"), {
      target: { value: "20456789012" },
    });
    fireEvent.change(screen.getByLabelText("Comprobante — Serie"), {
      target: { value: "F001" },
    });
    fireEvent.change(screen.getByLabelText("Comprobante — Número"), {
      target: { value: "000123" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Aplicar Filtros" }));

    await waitFor(() => expect(onApply).toHaveBeenCalled());
    const payload = onApply.mock.calls[0][0];
    expect(payload.documento).toBe("20456789012");
    expect(payload.comprobante_serie).toBe("F001");
    expect(payload.comprobante_numero).toBe("000123");
    expect(payload).not.toHaveProperty("creado_por");
    expect(payload).not.toHaveProperty("numero_revisiones");
  });
});
