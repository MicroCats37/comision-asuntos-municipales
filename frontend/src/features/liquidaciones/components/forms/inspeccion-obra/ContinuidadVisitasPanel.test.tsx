/**
 * PANEL de continuidad de visitas (IO) — comportamiento del formulario.
 *
 * El panel es el MODO ACTIVO "Continuar" del SmartField de tarifas: el modo
 * (y el bloque) los abre el SmartField, no el panel. Estos tests cubren el
 * CONTENIDO del panel: referencia histórica, bruto declarado editable y el
 * RESUMEN DEL COBRO renderizado con las cifras del SERVIDOR.
 *
 * Contrato cubierto (io-continuidad-visitas-impacto, io-continuidad-visitas-ui,
 * io-continuity-server-quote / AS-6):
 *  · El panel NO hace aritmética monetaria: muestra EXACTAMENTE el bloque
 *    `continuidad` que devuelve el servidor (valor completo, crédito y
 *    diferencia, netos y brutos).
 *  · El único dato que el usuario declara es el BRUTO pagado en la IO previa
 *    (`total_pagado_previa`).
 *  · La previa puede venir del listado de IO existente o ingresarse manual.
 */
import { render, screen } from "@testing-library/react";
import { FormProvider, useForm } from "react-hook-form";
import { describe, expect, it } from "vitest";
import { formatCurrencyTrimmed } from "@/utils/number-formatter";
import type { LiquidacionInspeccionObraListItem } from "../../../schemas/liquidacion-inspeccion-obra.schema";
import type {
  ContinuidadVisitasFormData,
  VisitasFormData,
} from "../../../schemas/liquidacion-visitas-form.schema";
import {
  ContinuidadVisitasPanel,
  type CotizacionContinuidad,
  deriveContinuidadDefaults,
} from "./ContinuidadVisitasPanel";

/**
 * Bloque `continuidad` del SERVIDOR.
 *
 * Las cifras están elegidas para que cualquier cálculo en el cliente dé un
 * resultado DISTINTO: `50 × 1.18 = 59.00` (no 59.01) y
 * `354.00 − 59.01 = 294.99`. Si el panel los recalculara, los tests fallarían.
 */
const COTIZACION: CotizacionContinuidad = {
  total_pagado_previa: 59,
  valor_completo_neto: 300,
  valor_completo_bruto: 354,
  credito_neto: 50,
  credito_bruto: 59.01,
  diferencia_neto: 250,
  diferencia_bruto: 294.99,
  igv_porcentaje: 0.18,
};

const PREVIA = {
  liquidacion_general: {
    id: "io-previa-1",
    expediente: "EXP-PREVIA-1",
    sub_total: 2500,
    total: 2950,
    comprobantes: [
      { id: "comp-1", monto: 59, activo: true },
      { id: "comp-2", monto: 100, activo: false },
    ],
  },
  liquidacion_especifica: { id: "esp-1", numero: 1 },
  liquidacion_tipo: {
    id: "lcv-1",
    cantidad_visitas: 10,
    categoria: "2",
    registros_pago: [
      { id: "rp-1", inspecciones_pagadas: 2, periodo: 2026, mes: 1 },
    ],
  },
} as unknown as LiquidacionInspeccionObraListItem;

function Harness({
  previa,
  cotizacion,
  continuidad,
}: {
  previa?: LiquidacionInspeccionObraListItem | null;
  cotizacion?: CotizacionContinuidad | null;
  continuidad?: ContinuidadVisitasFormData;
}) {
  const methods = useForm<VisitasFormData>({
    defaultValues: { continuidad },
  });
  return (
    <FormProvider {...methods}>
      <ContinuidadVisitasPanel
        methods={methods}
        previa={previa ?? null}
        cotizacion={cotizacion ?? null}
      />
    </FormProvider>
  );
}

describe("ContinuidadVisitasPanel — resumen del cobro (cifras del servidor)", () => {
  it("muestra valor completo, crédito de la previa y total a cobrar del servidor", () => {
    render(
      <Harness
        previa={PREVIA}
        cotizacion={COTIZACION}
        continuidad={deriveContinuidadDefaults(PREVIA)}
      />,
    );

    // Valor completo de B: neto y con IGV (cifras del servidor).
    expect(
      screen.getByText("Valor completo (B):").parentElement,
    ).toHaveTextContent(formatCurrencyTrimmed(300, 2));
    expect(
      screen.getByText("Valor completo con IGV:").parentElement,
    ).toHaveTextContent(formatCurrencyTrimmed(354, 2));

    // Crédito: EXACTAMENTE el del servidor (59.01), no `50 × 1.18 = 59.00`.
    expect(
      screen.getByText("Crédito de la previa:").parentElement,
    ).toHaveTextContent(formatCurrencyTrimmed(50, 2));
    expect(
      screen.getByText("Crédito con IGV:").parentElement,
    ).toHaveTextContent(formatCurrencyTrimmed(59.01, 2));

    // Total a cobrar: la diferencia DEL SERVIDOR (bruto y neto separados).
    expect(screen.getByText("Total a cobrar:").parentElement).toHaveTextContent(
      formatCurrencyTrimmed(294.99, 2),
    );
    expect(
      screen.getByText("Total a cobrar (neto):").parentElement,
    ).toHaveTextContent(formatCurrencyTrimmed(250, 2));
  });

  it("no recalcula el crédito ni la diferencia en el cliente", () => {
    render(
      <Harness
        previa={PREVIA}
        cotizacion={COTIZACION}
        continuidad={deriveContinuidadDefaults(PREVIA)}
      />,
    );

    // Si el panel multiplicara el crédito neto por (1 + igv) mostraría
    // "− S/ 59" (50 × 1.18); el servidor devolvió 59.01.
    expect(
      screen.getByText("Crédito con IGV:").parentElement,
    ).toHaveTextContent(/− S\/ 59\.01$/);
    // Y si restara valor completo − crédito con el IGV inferido, mostraría
    // "S/ 295" en vez de 294.99.
    expect(screen.getByText("Total a cobrar:").parentElement).toHaveTextContent(
      /S\/ 294\.99$/,
    );
  });

  it("muestra guiones mientras el servidor no devuelve el bloque de continuidad", () => {
    render(
      <Harness
        previa={PREVIA}
        cotizacion={null}
        continuidad={deriveContinuidadDefaults(PREVIA)}
      />,
    );

    expect(
      screen.getByText("Valor completo (B):").parentElement,
    ).toHaveTextContent("—");
    expect(screen.getByText("Total a cobrar:").parentElement).toHaveTextContent(
      "—",
    );
  });
});

describe("ContinuidadVisitasPanel — el dato declarado es el bruto", () => {
  it("el campo editable es el total pagado en la liquidación previa", () => {
    render(
      <Harness
        previa={PREVIA}
        cotizacion={COTIZACION}
        continuidad={deriveContinuidadDefaults(PREVIA)}
      />,
    );

    const input = screen.getByLabelText(
      "Total pagado en la liquidación previa (con IGV)",
    );
    expect(input).toBeInTheDocument();
    // El prefill propuesto es la suma de los comprobantes ACTIVOS de la previa.
    expect(input).toHaveValue(formatCurrencyTrimmed(59, 2));
  });

  it("el total cobrado de la previa es solo una sugerencia de prefill", () => {
    render(
      <Harness
        previa={PREVIA}
        cotizacion={COTIZACION}
        continuidad={deriveContinuidadDefaults(PREVIA)}
      />,
    );

    // Solo los comprobantes ACTIVOS (59), no el inactivo (100).
    expect(
      screen.getByText("Total cobrado (sugerencia):").parentElement,
    ).toHaveTextContent(formatCurrencyTrimmed(59, 2));
  });

  it("permite ingresar solo el monto sin una previa", () => {
    render(
      <Harness
        cotizacion={COTIZACION}
        continuidad={{
          total_pagado_previa: 59,
        }}
      />,
    );

    expect(
      screen.getByText(/Opcional: selecciona una IO anterior/i),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Total pagado en la liquidación previa (con IGV)"),
    ).toBeInTheDocument();
  });

  it("no muestra el límite de crédito del cliente (lo valida el servidor)", () => {
    render(
      <Harness
        previa={PREVIA}
        cotizacion={COTIZACION}
        continuidad={deriveContinuidadDefaults(PREVIA)}
      />,
    );

    expect(
      screen.queryByText(/no puede superar el valor completo/i),
    ).not.toBeInTheDocument();
  });
});
