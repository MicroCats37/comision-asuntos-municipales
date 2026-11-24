/**
 * Selector de estrategia de cotización y campo monetario por estrategia.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la ejecución de
 * la suite queda reservada para el Módulo 8 de la verificación final.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import type { UseFormReturn } from "react-hook-form";
import { FormProvider, useForm, useWatch } from "react-hook-form";
import { beforeAll, describe, expect, it, vi } from "vitest";
import {
  ESTRATEGIA_HABILITADAS,
  ESTRATEGIA_NORMAL,
  ESTRATEGIA_TOTAL,
  ESTRATEGIA_TOTAL_SELECCIONADAS,
} from "../../schemas/liquidacion-po-estrategia.schema";
import {
  EstrategiaCotizacionField,
  EstrategiaValorField,
} from "./EstrategiaCotizacionField";

/** Radix Select llama a `scrollIntoView`, que jsdom no implementa. */
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

function Probe({ methods }: { methods: UseFormReturn<any> }) {
  const estrategia = useWatch({
    control: methods.control,
    name: "estrategia_cotizacion",
  });
  const valor = useWatch({ control: methods.control, name: "valor_declarado" });
  const total = useWatch({ control: methods.control, name: "total_explicito" });
  return (
    <>
      <span data-testid="estrategia">{String(estrategia ?? "")}</span>
      <span data-testid="valor">{String(valor ?? "")}</span>
      <span data-testid="total">{String(total ?? "")}</span>
    </>
  );
}

function Harness({ children }: { children?: ReactNode }) {
  const methods = useForm<any>({
    defaultValues: {
      estrategia_cotizacion: ESTRATEGIA_NORMAL,
      valor_declarado: 1000000,
      total_explicito: undefined,
    },
  });
  return (
    <FormProvider {...methods}>
      <EstrategiaCotizacionField methods={methods} />
      <Probe methods={methods} />
      {children}
    </FormProvider>
  );
}

function ValorHarness({
  estrategia,
}: {
  estrategia: typeof ESTRATEGIA_NORMAL | typeof ESTRATEGIA_TOTAL;
}) {
  const methods = useForm<any>({
    defaultValues: { estrategia_cotizacion: estrategia },
  });
  return (
    <FormProvider {...methods}>
      <EstrategiaValorField
        methods={methods}
        defaultValorDeclarado={1000000}
        defaultTotalExplicito={177}
      />
    </FormProvider>
  );
}

async function seleccionarEstrategia(nombre: RegExp) {
  fireEvent.click(
    screen.getByRole("combobox", { name: "Estrategia de cotización" }),
  );

  const opcion = await screen.findByRole("option", { name: nombre });
  fireEvent.click(opcion);
}

describe("EstrategiaCotizacionField — selector accesible", () => {
  it("expone las cuatro estrategias disponibles", async () => {
    render(<Harness />);

    fireEvent.click(
      screen.getByRole("combobox", { name: "Estrategia de cotización" }),
    );

    const opciones = await screen.findAllByRole("option");
    expect(opciones).toHaveLength(4);
    expect(
      screen.getByRole("option", { name: /Normal - seleccionadas/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: /1 o 2 especialidades/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: /Plantas típicas/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: /Raros/i }),
    ).toBeInTheDocument();
  });

  it("marca como seleccionada la estrategia vigente", () => {
    render(<Harness />);

    expect(
      screen.getByRole("combobox", { name: "Estrategia de cotización" }),
    ).toHaveTextContent("Normal - seleccionadas");
  });
});

describe("EstrategiaCotizacionField — conserva los datos aplicables", () => {
  it("al pasar a TOTAL_EXPLICITO conserva el valor declarado", async () => {
    render(<Harness />);
    expect(screen.getByTestId("valor")).toHaveTextContent("1000000");

    await seleccionarEstrategia(/Plantas típicas/i);

    await waitFor(() =>
      expect(screen.getByTestId("estrategia")).toHaveTextContent(
        ESTRATEGIA_TOTAL,
      ),
    );
    expect(screen.getByTestId("valor")).toHaveTextContent("1000000");
  });

  it("al pasar a TARIFA_HABILITADAS borra el total explícito residual", async () => {
    render(<Harness />);

    await seleccionarEstrategia(/1 o 2 especialidades/i);

    await waitFor(() =>
      expect(screen.getByTestId("estrategia")).toHaveTextContent(
        ESTRATEGIA_HABILITADAS,
      ),
    );
    await waitFor(() =>
      expect(screen.getByTestId("total")).toHaveTextContent(""),
    );
  });

  it("al volver a NORMAL_SELECCIONADAS conserva el valor declarado", async () => {
    render(<Harness />);

    await seleccionarEstrategia(/Plantas típicas/i);
    expect(screen.getByTestId("valor")).toHaveTextContent("1000000");

    await seleccionarEstrategia(/Normal - seleccionadas/i);

    await waitFor(() =>
      expect(screen.getByTestId("estrategia")).toHaveTextContent(
        ESTRATEGIA_NORMAL,
      ),
    );
    expect(screen.getByTestId("valor")).toHaveTextContent("1000000");
  });

  it("al pasar a Raros conserva el valor declarado", async () => {
    render(<Harness />);

    await seleccionarEstrategia(/Raros/i);

    await waitFor(() =>
      expect(screen.getByTestId("estrategia")).toHaveTextContent(
        ESTRATEGIA_TOTAL_SELECCIONADAS,
      ),
    );
    expect(screen.getByTestId("valor")).toHaveTextContent("1000000");
  });
});

describe("EstrategiaValorField — campos por estrategia", () => {
  it("muestra el valor declarado en NORMAL_SELECCIONADAS", () => {
    render(<ValorHarness estrategia={ESTRATEGIA_NORMAL} />);

    expect(screen.getByLabelText(/Valor Declarado/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Total Final/)).not.toBeInTheDocument();
  });

  it("muestra el valor de la obra y el total final en TOTAL_EXPLICITO", () => {
    render(<ValorHarness estrategia={ESTRATEGIA_TOTAL} />);

    expect(screen.getByLabelText(/Valor de la obra/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Total final/i)).toBeInTheDocument();
  });
});
