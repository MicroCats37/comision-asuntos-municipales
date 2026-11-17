/**
 * Detalle de IO — bloque de continuidad de visitas.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la ejecución de
 * la suite queda reservada para la Fase 5 (verificación final).
 *
 * Contrato cubierto (io-continuidad-visitas-impacto, Fase 4):
 *  · El bloque de continuidad se muestra SOLO cuando existe.
 *  · Sin continuidad, el detalle es idéntico al vigente.
 *  · Cuando existe, muestra los tres importes separados: valor completo,
 *    crédito de la previa y total a cobrar.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { VisitasDatosOut } from "../../schemas/liquidacion-visitas.schema";
import { formatCurrency } from "../liquidacion-ui";
import { LiquidacionDetalleInspeccionObraSection } from "./LiquidacionDetalleInspeccionObraSection";

function baseTipo(overrides: Partial<VisitasDatosOut> = {}): VisitasDatosOut {
  return {
    id: "tipo-1",
    cantidad_visitas: 10,
    porcentaje_uit: 0.001,
    categoria: "2",
    tarifa_aplicada_id: null,
    inspectores: [],
    registros_pago: [],
    ...overrides,
  };
}

const continuidad = {
  id: "cont-1",
  liquidacion_previa_id: "previa-1",
  monto_acumulado: 2500,
  total_acumulado: 2950,
  subtotal_credito: 2000,
  total_credito: 2360,
  visitas_previas_totales: 10,
  visitas_previas_pendientes: 8,
  categoria_previa: "2",
  observacion: null,
};

describe("LiquidacionDetalleInspeccionObraSection — continuidad", () => {
  it("no muestra el bloque de continuidad cuando la IO no tiene continuidad", () => {
    render(
      <LiquidacionDetalleInspeccionObraSection liquidacionTipo={baseTipo()} />,
    );

    expect(
      screen.queryByText("Continuidad de visitas"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Valor completo")).not.toBeInTheDocument();
    expect(screen.queryByText("Total a cobrar")).not.toBeInTheDocument();
    // El resto del detalle vigente sigue igual.
    expect(screen.getByText("Cant. Visitas")).toBeInTheDocument();
    expect(screen.getByText("Inspectores asignados")).toBeInTheDocument();
  });

  it("muestra valor completo, crédito de la previa y total a cobrar", () => {
    render(
      <LiquidacionDetalleInspeccionObraSection
        liquidacionTipo={baseTipo({ continuidad })}
      />,
    );

    expect(screen.getByText("Continuidad de visitas")).toBeInTheDocument();

    const filaValorCompleto = screen.getByText("Valor completo").parentElement;
    expect(filaValorCompleto).toHaveTextContent(formatCurrency(2500));
    expect(filaValorCompleto).toHaveTextContent(formatCurrency(2950));

    const filaCredito = screen.getByText("Crédito de la previa").parentElement;
    expect(filaCredito).toHaveTextContent(formatCurrency(2000));
    expect(filaCredito).toHaveTextContent(formatCurrency(2360));

    // Total a cobrar = valor completo − crédito (bruto y neto por separado).
    const filaTotalACobrar = screen.getByText("Total a cobrar").parentElement;
    expect(filaTotalACobrar).toHaveTextContent(formatCurrency(2950 - 2360));
    expect(filaTotalACobrar).toHaveTextContent(formatCurrency(2500 - 2000));
  });

  it("muestra las visitas pendientes y la categoría de la previa", () => {
    render(
      <LiquidacionDetalleInspeccionObraSection
        liquidacionTipo={baseTipo({ continuidad })}
      />,
    );

    expect(
      screen.getByText("Visitas pendientes de la previa:"),
    ).toBeInTheDocument();
    expect(screen.getByText("Categoría previa:")).toBeInTheDocument();
  });
});
