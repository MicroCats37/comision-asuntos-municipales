/**
 * PANEL de continuidad de visitas (IO) — comportamiento en EDICIÓN.
 *
 * El panel es el MODO ACTIVO "Continuar" del SmartField de tarifas. Estos
 * tests cubren la parte EDITABLE del panel: la rehidratación del registro
 * persistido, el discriminador de la OPERACIÓN (`mantener` / `activar`) y la
 * desactivación con confirmación explícita.
 *
 * Contrato cubierto (io-continuidad-visitas-ui-edit, io-continuity-server-quote):
 *  · El registro persistido se rehidrata: la referencia a la liquidación previa
 *    (A) se muestra en SOLO LECTURA y la UI nunca la reprecia.
 *  · Editar el bloque marca la operación de continuidad (`modo: "mantener"`).
 *  · Desactivar exige CONFIRMACIÓN EXPLICITA: sin confirmar, el formulario no
 *    lleva `modo: "desactivar"`.
 *  · Una IO sin continuidad persistida opera en `modo: "activar"`.
 *  · El campo editable es el BRUTO declarado; el resumen muestra las cifras
 *    del SERVIDOR.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import type { UseFormReturn } from "react-hook-form";
import { FormProvider, useForm } from "react-hook-form";
import { describe, expect, it } from "vitest";
import { formatCurrencyTrimmed } from "@/utils/number-formatter";
import type { ContinuidadVisitasOut } from "../../../schemas/liquidacion-visitas.schema";
import type { VisitasFormData } from "../../../schemas/liquidacion-visitas-form.schema";
import {
  ContinuidadVisitasPanel,
  type CotizacionContinuidad,
  deriveContinuidadEditDefaults,
} from "./ContinuidadVisitasPanel";

/** Bloque `continuidad` del servidor (cotización histórica de edición). */
const COTIZACION_HISTORICA: CotizacionContinuidad = {
  total_pagado_previa: 590,
  valor_completo_neto: 2500,
  valor_completo_bruto: 2950,
  credito_neto: 500,
  credito_bruto: 590,
  diferencia_neto: 2000,
  diferencia_bruto: 2360,
  igv_porcentaje: 0.18,
};

const CONTINUIDAD_PERSISTIDA: ContinuidadVisitasOut = {
  id: "cont-1",
  liquidacion_previa_id: "io-previa-1",
  monto_acumulado: 2500,
  total_acumulado: 2950,
  subtotal_credito: 500,
  total_credito: 590,
  visitas_previas_totales: 10,
  visitas_previas_pendientes: 2,
  categoria_previa: "2",
  observacion: "Observación persistida",
};

function Observador({ methods }: { methods: UseFormReturn<VisitasFormData> }) {
  const continuidad = methods.watch("continuidad");
  return (
    <pre data-testid="estado">
      {JSON.stringify(continuidad ?? null, null, 0)}
    </pre>
  );
}

function Harness({
  continuidadPersistida,
  cotizacion,
}: {
  continuidadPersistida?: ContinuidadVisitasOut | null;
  cotizacion?: CotizacionContinuidad | null;
}) {
  const methods = useForm<VisitasFormData>({
    defaultValues: {
      continuidad: continuidadPersistida
        ? deriveContinuidadEditDefaults(continuidadPersistida)
        : undefined,
    },
  });
  return (
    <FormProvider {...methods}>
      <ContinuidadVisitasPanel
        methods={methods}
        mode="edit"
        continuidadPersistida={continuidadPersistida ?? null}
        cotizacion={cotizacion ?? null}
      />
      <Observador methods={methods} />
    </FormProvider>
  );
}

function estadoContinuidad(): Record<string, unknown> | null {
  const raw = screen.getByTestId("estado").textContent ?? "null";
  return JSON.parse(raw) as Record<string, unknown> | null;
}

describe("ContinuidadVisitasPanel — edición con continuidad persistida", () => {
  it("rehidrata el panel y muestra la referencia histórica en solo lectura", () => {
    render(
      <Harness
        continuidadPersistida={CONTINUIDAD_PERSISTIDA}
        cotizacion={COTIZACION_HISTORICA}
      />,
    );

    expect(
      screen.getByText("Liquidación previa (referencia histórica)"),
    ).toBeInTheDocument();
    expect(screen.getByText("Solo lectura")).toBeInTheDocument();
    expect(screen.getByText("io-previa-1")).toBeInTheDocument();

    // Sin continuidad persistida no hay registro que apagar: el panel ofrece
    // la desactivación (con confirmación) y NUNCA la activación.
    expect(
      screen.queryByRole("button", { name: /^Activar continuidad$/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Desactivar continuidad/i }),
    ).toBeInTheDocument();
  });

  it("no envía operación de continuidad mientras el usuario no toque el bloque", () => {
    render(
      <Harness
        continuidadPersistida={CONTINUIDAD_PERSISTIDA}
        cotizacion={COTIZACION_HISTORICA}
      />,
    );

    expect(estadoContinuidad()?.modo).toBeUndefined();
  });

  it("marca `mantener` cuando el usuario edita el bruto declarado", () => {
    render(
      <Harness
        continuidadPersistida={CONTINUIDAD_PERSISTIDA}
        cotizacion={COTIZACION_HISTORICA}
      />,
    );

    fireEvent.change(
      screen.getByLabelText("Total pagado en la liquidación previa (con IGV)"),
      { target: { value: "750" } },
    );

    const estado = estadoContinuidad();
    expect(estado?.modo).toBe("mantener");
    expect(estado?.total_pagado_previa).toBe(750);
  });

  it("muestra el resumen con las cifras del servidor: valor completo, crédito y total a cobrar", () => {
    render(
      <Harness
        continuidadPersistida={CONTINUIDAD_PERSISTIDA}
        cotizacion={COTIZACION_HISTORICA}
      />,
    );

    expect(
      screen.getByText("Valor completo (B):").parentElement,
    ).toHaveTextContent(formatCurrencyTrimmed(2500, 2));
    expect(
      screen.getByText("Crédito de la previa:").parentElement,
    ).toHaveTextContent(formatCurrencyTrimmed(500, 2));
    expect(screen.getByText("Total a cobrar:").parentElement).toHaveTextContent(
      formatCurrencyTrimmed(2360, 2),
    );
  });

  it("el bruto vigente del crédito se rehidrata como bruto declarado", () => {
    render(
      <Harness
        continuidadPersistida={CONTINUIDAD_PERSISTIDA}
        cotizacion={COTIZACION_HISTORICA}
      />,
    );

    // El `total_credito` persistido (590) es el bruto que el servidor ya
    // derivó: se propone como dato declarado para que la cotización de
    // edición use el MISMO IGV histórico.
    expect(estadoContinuidad()?.total_pagado_previa).toBe(590);
    expect(
      screen.getByLabelText("Total pagado en la liquidación previa (con IGV)"),
    ).toHaveValue(formatCurrencyTrimmed(590, 2));
  });
});

describe("ContinuidadVisitasPanel — desactivación con confirmación explícita", () => {
  it("pide confirmación antes de desactivar y no marca el modo al cancelar", () => {
    render(
      <Harness
        continuidadPersistida={CONTINUIDAD_PERSISTIDA}
        cotizacion={COTIZACION_HISTORICA}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: /Desactivar continuidad/i }),
    );

    // Aviso de efecto comercial antes de permitir el apagado.
    expect(
      screen.getByText(/se elimina el crédito de la previa/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Confirmar desactivación/i }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^Cancelar$/i }));

    // Cancelar NO deja el modo `desactivar` pendiente.
    expect(estadoContinuidad()?.modo).toBeUndefined();
  });

  it("marca `desactivar` solo después de la confirmación explícita", () => {
    render(
      <Harness
        continuidadPersistida={CONTINUIDAD_PERSISTIDA}
        cotizacion={COTIZACION_HISTORICA}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: /Desactivar continuidad/i }),
    );
    fireEvent.click(
      screen.getByRole("button", { name: /Confirmar desactivación/i }),
    );

    expect(estadoContinuidad()?.modo).toBe("desactivar");
    expect(
      screen.getByText(/La continuidad se desactivará al guardar/i),
    ).toBeInTheDocument();
  });

  it("permite volver a mantener la continuidad tras confirmar el apagado", () => {
    render(
      <Harness
        continuidadPersistida={CONTINUIDAD_PERSISTIDA}
        cotizacion={COTIZACION_HISTORICA}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: /Desactivar continuidad/i }),
    );
    fireEvent.click(
      screen.getByRole("button", { name: /Confirmar desactivación/i }),
    );
    fireEvent.click(
      screen.getByRole("button", { name: /Mantener continuidad/i }),
    );

    expect(estadoContinuidad()?.modo).toBeUndefined();
  });
});

describe("ContinuidadVisitasPanel — edición sin continuidad persistida", () => {
  it("marca `activar` cuando el usuario edita el bloque", () => {
    render(<Harness cotizacion={COTIZACION_HISTORICA} />);

    // Abrir el panel NO es una operación: el modo sigue sin definirse.
    // (El MoneyInput registra el campo vacío: `total_pagado_previa` = "")
    expect(estadoContinuidad()).toEqual({ total_pagado_previa: "" });

    fireEvent.change(
      screen.getByLabelText("Total pagado en la liquidación previa (con IGV)"),
      { target: { value: "120" } },
    );

    expect(estadoContinuidad()?.modo).toBe("activar");
    expect(estadoContinuidad()?.total_pagado_previa).toBe(120);
  });
});
