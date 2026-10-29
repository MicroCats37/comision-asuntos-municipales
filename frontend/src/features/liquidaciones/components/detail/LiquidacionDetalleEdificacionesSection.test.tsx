/**
 * Contexto de estrategia PO en el detalle de Edificaciones.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la ejecución de
 * la suite queda reservada para el Módulo 8 de la verificación final.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { EdificacionesDetalleDatos } from "./LiquidacionDetalleEdificacionesSection";
import { LiquidacionDetalleEdificacionesSection } from "./LiquidacionDetalleEdificacionesSection";

function baseTipo(
  overrides: Partial<EdificacionesDetalleDatos> = {},
): EdificacionesDetalleDatos {
  return {
    id: "tipo-1",
    valor_declarado: 1_000_000,
    porcentaje_liquidacion: 0.0015,
    tipo_tramite: "OBRA_NUEVA",
    derecho_minimo: 500,
    derecho_maximo: 50_000,
    porcentaje_minimo_uit: 0.1,
    derecho_aplicado_id: null,
    detalles: [],
    ...overrides,
  };
}

describe("LiquidacionDetalleEdificacionesSection — presentación pública", () => {
  it("oculta estrategia, H, porcentaje de tarifa y acumulación", () => {
    render(
      <LiquidacionDetalleEdificacionesSection
        liquidacionTipo={baseTipo({
          estrategia_cotizacion: "TARIFA_HABILITADAS_PARTICIPANTES",
          count_habilitadas: 3,
          porcentaje_tarifa: 0.0005,
          acumulacion: {
            porcentaje_acumulado: 0.001,
            subtotal_acumulado: 1000,
          },
        })}
      />,
    );

    expect(screen.queryByText("Estrategia")).not.toBeInTheDocument();
    expect(screen.queryByText("Habilitadas (H)")).not.toBeInTheDocument();
    expect(screen.queryByText("% Tarifa")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Acumulación (informativa)"),
    ).not.toBeInTheDocument();
  });

  it("no muestra explicaciones internas de acumulación", () => {
    render(
      <LiquidacionDetalleEdificacionesSection
        liquidacionTipo={baseTipo({
          estrategia_cotizacion: "TARIFA_HABILITADAS_PARTICIPANTES",
          count_habilitadas: 3,
          acumulacion: {
            porcentaje_acumulado: 0.001,
            subtotal_acumulado: 1000,
          },
        })}
      />,
    );

    expect(
      screen.queryByText(/La acumulación es informativa/i),
    ).not.toBeInTheDocument();
  });

  it("omite H y % de tarifa en NORMAL_SELECCIONADAS", () => {
    render(
      <LiquidacionDetalleEdificacionesSection
        liquidacionTipo={baseTipo({
          estrategia_cotizacion: "NORMAL_SELECCIONADAS",
          count_habilitadas: 3,
          porcentaje_tarifa: 0.0005,
        })}
      />,
    );

    expect(screen.queryByText("Estrategia")).not.toBeInTheDocument();
    expect(screen.queryByText("Habilitadas (H)")).not.toBeInTheDocument();
    expect(screen.queryByText("% Tarifa")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Acumulación (informativa)"),
    ).not.toBeInTheDocument();
  });

  it("oculta también el contexto de TOTAL_EXPLICITO", () => {
    render(
      <LiquidacionDetalleEdificacionesSection
        liquidacionTipo={baseTipo({
          valor_declarado: null,
          porcentaje_liquidacion: null,
          estrategia_cotizacion: "TOTAL_EXPLICITO",
          count_habilitadas: 3,
          acumulacion: {
            porcentaje_acumulado: null,
            subtotal_acumulado: 100,
          },
        })}
      />,
    );

    expect(screen.queryByText("Total explícito")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Acumulación (informativa)"),
    ).not.toBeInTheDocument();
  });

  it("no renderiza el bloque de estrategia cuando el motor no la expone", () => {
    render(
      <LiquidacionDetalleEdificacionesSection
        liquidacionTipo={baseTipo()}
      />,
    );

    expect(screen.queryByText("Estrategia")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Acumulación (informativa)"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/La acumulación es informativa/i),
    ).not.toBeInTheDocument();

    // Los parámetros legacy del motor porcentaje siguen intactos.
    expect(screen.getByText("Valor declarado")).toBeInTheDocument();
    expect(screen.getByText("% Liq.")).toBeInTheDocument();
    expect(screen.getByText("Der. Mín.")).toBeInTheDocument();
    expect(screen.getByText("Der. Máx.")).toBeInTheDocument();
    expect(screen.getByText("% Mín. UIT")).toBeInTheDocument();
  });
});
