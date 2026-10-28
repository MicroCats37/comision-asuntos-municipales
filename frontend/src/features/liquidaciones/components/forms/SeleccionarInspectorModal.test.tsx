import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SeleccionarInspectorModal } from "./SeleccionarInspectorModal";

vi.mock("../../hooks/useInspectoresVigentes", () => ({
  useInspectoresVigentes: () => ({
    data: [
      {
        id: "inspector-3",
        inspector_operacion_id: "operacion-3",
        nombre_completo: "Inspector Categoria Tres",
        cip: "100003",
        numero_registro: "REG-3",
        categoria: "3",
        especialidad: { nombre: "Arquitectura" },
      },
      {
        id: "inspector-4",
        inspector_operacion_id: "operacion-4",
        nombre_completo: "Inspector Categoria Cuatro",
        cip: "100004",
        numero_registro: "REG-4",
        categoria: "4",
        especialidad: { nombre: "Arquitectura" },
      },
    ],
    isLoading: false,
  }),
}));

describe("SeleccionarInspectorModal", () => {
  it("filters inspectors with category badges independently from tariffs", () => {
    render(
      <SeleccionarInspectorModal
        open
        onOpenChange={vi.fn()}
        fallbackTipoLiquidacionCodigo="EDIFICACION"
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByText("Inspector Categoria Tres")).toBeInTheDocument();
    expect(screen.getByText("Inspector Categoria Cuatro")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "3" }));
    expect(screen.getByText("Inspector Categoria Tres")).toBeInTheDocument();
    expect(
      screen.queryByText("Inspector Categoria Cuatro"),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Todas" }));
    expect(screen.getByText("Inspector Categoria Cuatro")).toBeInTheDocument();
  });
});
