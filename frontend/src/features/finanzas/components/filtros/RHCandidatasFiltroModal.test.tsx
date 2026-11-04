/**
 * RHCandidatasFiltroModal — filtros de candidatas RH (Inspector y Delegado).
 *
 * Cubre los filtros nuevos: N.º de documento de entidad y comprobante
 * vigente (serie + número), y que el conteo de filtros activos los incluya.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  countActiveFiltros,
  RHCandidatasFiltroModal,
} from "./RHCandidatasFiltroModal";

describe("RHCandidatasFiltroModal", () => {
  it("expone los filtros de documento y de comprobante vigente", () => {
    render(
      <RHCandidatasFiltroModal open onOpenChange={vi.fn()} onApply={vi.fn()} />,
    );

    expect(
      screen.getByLabelText("N° Documento Entidad"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Comprobante — Serie")).toBeInTheDocument();
    expect(screen.getByLabelText("Comprobante — Número")).toBeInTheDocument();
  });

  it("envía los valores de los filtros nuevos al aplicar", async () => {
    const onApply = vi.fn();
    render(
      <RHCandidatasFiltroModal
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
    expect(onApply).toHaveBeenCalledWith({
      documento: "20456789012",
      comprobante_serie: "F001",
      comprobante_numero: "000123",
    });
  });

  it("cuenta los filtros nuevos como filtros activos", () => {
    expect(
      countActiveFiltros({
        documento: "20456789012",
        comprobante_serie: "F001",
        comprobante_numero: "000123",
      }),
    ).toBe(3);
    expect(countActiveFiltros({})).toBe(0);
  });
});
