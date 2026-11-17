/**
 * Smart Field de tarifas/cotización de IO — COMPOSICIÓN DE MODOS.
 *
 * El SmartField es el dueño de los modos de cotización de IO (patrón
 * PO/Edificaciones): monta el selector de modo en su cabecera y compone el
 * PANEL ACTIVO.
 *
 * Contrato cubierto (io-continuidad-visitas-ui, io-continuity-server-quote):
 *  · El selector de modo (Normal / Continuar) vive en la cabecera del
 *    SmartField y escribe en el form.
 *  · `Normal` conserva la UI y el payload vigentes: la cotización por valor
 *    completo, sin panel de continuidad.
 *  · `Continuar` renderiza el panel de continuidad (referencia histórica,
 *    crédito y diferencia) DENTRO del SmartField — no como tarjeta aparte.
 *  · El payload de la cotización lleva el DISCRIMINADOR `modo_cotizacion` y,
 *    en Continuar, el BRUTO declarado (`continuidad.total_pagado_previa`).
 *  · El panel renderiza las cifras del bloque `continuidad` del SERVIDOR.
 *  · Volver a `Normal` descarta el bloque de continuidad (no viaja en el
 *    payload).
 *  · Con continuidad PERSISTIDA el selector queda bloqueado: la liquidación
 *    cobra la diferencia y el modo "Normal" sería una vista falsa.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { UseFormReturn } from "react-hook-form";
import { FormProvider, useForm, useWatch } from "react-hook-form";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  MODO_COTIZACION_IO_CONTINUAR,
  MODO_COTIZACION_IO_NORMAL,
  type ModoCotizacionIO,
} from "../../schemas/liquidacion-io-modo-cotizacion.schema";
import type { ContinuidadVisitasOut } from "../../schemas/liquidacion-visitas.schema";
import type { ContinuidadVisitasFormData } from "../../schemas/liquidacion-visitas-form.schema";
import { TarifasVisitasSinPreviaSmartField } from "./TarifasVisitasSinPreviaSmartField";

const { postMock, getMock } = vi.hoisted(() => ({
  postMock: vi.fn(),
  getMock: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  default: { post: postMock, get: getMock },
}));

// El debounce se neutraliza para que el preview sea determinista.
vi.mock("@/hooks/system/useDebounce", () => ({
  useDebounce: <T,>(value: T) => value,
}));

const QUOTE = {
  datos: {
    entrada: {
      datos: { cantidad_visitas: 3, categoria: "2" },
      tarifa: { tarifa_visitas_id: "tarifa-1" },
    },
    tarifa: { id: "tarifa-1", costo_por_visita: 250 },
    variables_financieras: {
      igv: { valor: 0.18 },
      uit: { valor: 5350 },
    },
  },
  calculo: { monto_bruto: 2500, subtotal: 2500, total: 2950 },
  modo_cotizacion: "NORMAL",
  continuidad: null,
};

/** Respuesta del servidor en modo CONTINUAR (cifras autoritativas). */
const QUOTE_CONTINUAR = {
  ...QUOTE,
  modo_cotizacion: "CONTINUAR",
  calculo: { monto_bruto: 2500, subtotal: 2500, total: 2950 },
  continuidad: {
    total_pagado_previa: 212.6,
    valor_completo_neto: 2500,
    valor_completo_bruto: 2950,
    credito_neto: 180.17,
    credito_bruto: 212.6,
    diferencia_neto: 2319.83,
    diferencia_bruto: 2737.4,
    igv_porcentaje: 0.18,
  },
};

const TARIFAS = [{ id: "tarifa-1", costo_por_visita: 250, categoria: "2" }];

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

interface FormHarness {
  cantidad_visitas: number;
  categoria: string;
  tarifa_visitas_id: string;
  modo_cotizacion?: ModoCotizacionIO;
  continuidad?: ContinuidadVisitasFormData;
}

function Probe({ methods }: { methods: UseFormReturn<FormHarness> }) {
  const continuidad = useWatch({
    control: methods.control,
    name: "continuidad",
  });
  return <pre data-testid="bloque">{JSON.stringify(continuidad ?? null)}</pre>;
}

function Harness({
  modoCotizacion = MODO_COTIZACION_IO_NORMAL,
  continuidad,
  modo = "create",
  liquidacionId,
  soportaModoContinuidad = true,
  continuidadPersistida = null,
}: {
  modoCotizacion?: ModoCotizacionIO;
  continuidad?: ContinuidadVisitasFormData;
  modo?: "create" | "edit";
  liquidacionId?: string;
  soportaModoContinuidad?: boolean;
  continuidadPersistida?: ContinuidadVisitasOut | null;
}) {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  const methods = useForm<FormHarness>({
    defaultValues: {
      cantidad_visitas: 3,
      categoria: "2",
      tarifa_visitas_id: "tarifa-1",
      modo_cotizacion: modoCotizacion,
      continuidad,
    },
  });
  return (
    <QueryClientProvider client={client}>
      <FormProvider {...methods}>
        <TarifasVisitasSinPreviaSmartField
          methods={methods}
          onOpenInspector={() => undefined}
          mode={modo}
          liquidacionId={liquidacionId}
          soportaModoContinuidad={soportaModoContinuidad}
          continuidadPersistida={continuidadPersistida}
        />
        <Probe methods={methods} />
      </FormProvider>
    </QueryClientProvider>
  );
}

function bloqueContinuidad(): Record<string, unknown> | null {
  const raw = screen.getByTestId("bloque").textContent ?? "null";
  return JSON.parse(raw) as Record<string, unknown> | null;
}

beforeEach(() => {
  postMock.mockReset();
  getMock.mockReset();
  postMock.mockResolvedValue({ data: { data: QUOTE } });
  getMock.mockResolvedValue({
    data: { success: true, data: { tarifas: TARIFAS } },
  });
});

describe("TarifasVisitasSinPreviaSmartField — selector de modo", () => {
  it("monta el selector Normal / Continuar en la cabecera del SmartField", () => {
    render(<Harness />);

    const selector = screen.getByRole("radiogroup", {
      name: /Modo de cotización/i,
    });
    expect(selector).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /^Normal$/ })).toBeInTheDocument();
    expect(
      screen.getByRole("radio", { name: /^Continuar$/ }),
    ).toBeInTheDocument();
  });

  it("no monta el selector cuando el motor no admite el modo", () => {
    render(<Harness soportaModoContinuidad={false} />);

    expect(
      screen.queryByRole("radiogroup", { name: /Modo de cotización/i }),
    ).not.toBeInTheDocument();
  });
});

describe("TarifasVisitasSinPreviaSmartField — panel del modo activo", () => {
  it("en Normal conserva la cotización por valor completo y no muestra el panel", async () => {
    render(<Harness />);

    await waitFor(() =>
      expect(screen.getByText("Total a Pagar:")).toBeInTheDocument(),
    );
    expect(
      screen.queryByText("Continuidad de visitas"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Total a cobrar:")).not.toBeInTheDocument();
  });

  it("en Continuar renderiza el panel de continuidad dentro del SmartField", async () => {
    render(<Harness />);

    await waitFor(() =>
      expect(screen.getByText("Total a Pagar:")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("radio", { name: /^Continuar$/ }));

    await waitFor(() =>
      expect(screen.getByText("Continuidad de visitas")).toBeInTheDocument(),
    );
    // El panel de continuidad REEMPLAZA al resumen normal: son modos
    // excluyentes, no dos tarjetas apiladas.
    expect(screen.queryByText("Total a Pagar:")).not.toBeInTheDocument();
    expect(screen.getByText("Valor completo (B):")).toBeInTheDocument();
    expect(screen.getByText("Total a cobrar:")).toBeInTheDocument();
  });

  it("volver a Normal descarta el bloque de continuidad", async () => {
    render(<Harness />);

    fireEvent.click(screen.getByRole("radio", { name: /^Continuar$/ }));
    await waitFor(() =>
      expect(screen.getByText("Continuidad de visitas")).toBeInTheDocument(),
    );
    // Entrar en "Continuar" abre el bloque (ingreso manual: sin previa).
    expect(bloqueContinuidad()).not.toBeNull();

    fireEvent.click(screen.getByRole("radio", { name: /^Normal$/ }));

    await waitFor(() => expect(bloqueContinuidad()).toBeNull());
    expect(
      screen.queryByText("Continuidad de visitas"),
    ).not.toBeInTheDocument();
  });
});

describe("TarifasVisitasSinPreviaSmartField — payload mode-aware", () => {
  it("en Normal envía el discriminador NORMAL y ningún bloque de continuidad", async () => {
    render(<Harness />);

    await waitFor(() => expect(postMock).toHaveBeenCalled());
    expect(postMock).toHaveBeenCalledWith(
      "/liquidaciones/inspeccion-obra/cotizar",
      {
        liquidacion_especifica: {
          modo_cotizacion: "NORMAL",
          datos: { cantidad_visitas: 3 },
          tarifa: { tarifa_visitas_id: "tarifa-1" },
        },
      },
    );
  });

  it("en Continuar envía el discriminador CONTINUAR con el bruto declarado", async () => {
    render(
      <Harness
        modoCotizacion={MODO_COTIZACION_IO_CONTINUAR}
        continuidad={{ total_pagado_previa: 212.6 }}
      />,
    );

    await waitFor(() => expect(postMock).toHaveBeenCalled());
    expect(postMock).toHaveBeenCalledWith(
      "/liquidaciones/inspeccion-obra/cotizar",
      {
        liquidacion_especifica: {
          modo_cotizacion: "CONTINUAR",
          datos: { cantidad_visitas: 3 },
          tarifa: { tarifa_visitas_id: "tarifa-1" },
          continuidad: { total_pagado_previa: 212.6 },
        },
      },
    );
  });

  it("sin bruto declarado NO cotiza en modo Continuar (el backend lo rechaza)", async () => {
    render(<Harness modoCotizacion={MODO_COTIZACION_IO_CONTINUAR} />);

    await waitFor(() =>
      expect(screen.getByText("Continuidad de visitas")).toBeInTheDocument(),
    );
    expect(postMock).not.toHaveBeenCalled();
  });

  it("re-cotiza cuando el usuario cambia el bruto declarado", async () => {
    render(
      <Harness
        modoCotizacion={MODO_COTIZACION_IO_CONTINUAR}
        continuidad={{ total_pagado_previa: 212.6 }}
      />,
    );

    await waitFor(() => expect(postMock).toHaveBeenCalled());
    const llamadasAntes = postMock.mock.calls.length;

    fireEvent.change(
      screen.getByLabelText("Total pagado en la liquidación previa (con IGV)"),
      { target: { value: "300" } },
    );

    await waitFor(() =>
      expect(postMock.mock.calls.length).toBeGreaterThan(llamadasAntes),
    );
    expect(postMock).toHaveBeenLastCalledWith(
      "/liquidaciones/inspeccion-obra/cotizar",
      {
        liquidacion_especifica: {
          modo_cotizacion: "CONTINUAR",
          datos: { cantidad_visitas: 3 },
          tarifa: { tarifa_visitas_id: "tarifa-1" },
          continuidad: { total_pagado_previa: 300 },
        },
      },
    );
  });
});

describe("TarifasVisitasSinPreviaSmartField — el panel renderiza las cifras del servidor", () => {
  it("muestra el bloque `continuidad` de la respuesta, sin recalcularlo", async () => {
    postMock.mockResolvedValue({ data: { data: QUOTE_CONTINUAR } });

    render(
      <Harness
        modoCotizacion={MODO_COTIZACION_IO_CONTINUAR}
        continuidad={{ total_pagado_previa: 212.6 }}
      />,
    );

    await waitFor(() =>
      expect(
        screen.getByText("Total a cobrar:").parentElement,
      ).toHaveTextContent("S/ 2 737.4"),
    );

    // Cifras EXACTAMENTE del servidor (no un recálculo del cliente).
    expect(
      screen.getByText("Valor completo (B):").parentElement,
    ).toHaveTextContent("S/ 2 500");
    expect(
      screen.getByText("Crédito de la previa:").parentElement,
    ).toHaveTextContent("S/ 180.17");
    expect(
      screen.getByText("Total a cobrar (neto):").parentElement,
    ).toHaveTextContent("S/ 2 319.83");
  });
});

describe("TarifasVisitasSinPreviaSmartField — edición con continuidad persistida", () => {
  it("bloquea el selector y muestra la referencia histórica", async () => {
    render(
      <Harness
        modo="edit"
        liquidacionId="liq-io-1"
        modoCotizacion={MODO_COTIZACION_IO_CONTINUAR}
        continuidad={{
          liquidacion_previa_id: "io-previa-1",
          visitas_previas_totales: 10,
          visitas_previas_pendientes: 2,
          categoria_previa: "2",
          subtotal_credito: 500,
          observacion: "Observación persistida",
        }}
        continuidadPersistida={CONTINUIDAD_PERSISTIDA}
      />,
    );

    await waitFor(() =>
      expect(screen.getByText("Continuidad de visitas")).toBeInTheDocument(),
    );

    // La liquidación cobra la diferencia: el modo "Normal" (valor completo)
    // sería una vista falsa → el selector queda bloqueado.
    expect(screen.getByRole("radio", { name: /^Normal$/ })).toBeDisabled();
    expect(screen.getByRole("radio", { name: /^Continuar$/ })).toBeDisabled();
    expect(
      screen.getByText("Liquidación previa (referencia histórica)"),
    ).toBeInTheDocument();
  });
});
