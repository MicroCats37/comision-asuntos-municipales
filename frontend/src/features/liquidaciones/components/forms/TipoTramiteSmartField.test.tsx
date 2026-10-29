import { render, screen, waitFor } from "@testing-library/react";
import type { UseFormReturn } from "react-hook-form";
import { FormProvider, useForm, useWatch } from "react-hook-form";
import { describe, expect, it } from "vitest";

import { TipoTramiteSmartField } from "./TipoTramiteSmartField";

function DenominacionProbe({
  methods,
}: {
  // biome-ignore lint/suspicious/noExplicitAny: RHF generics pattern matches the existing smart fields
  methods: UseFormReturn<any>;
}) {
  const denominacion = useWatch({
    control: methods.control,
    name: "denominacion",
  });
  return <span data-testid="denominacion">{String(denominacion ?? "")}</span>;
}

function Harness({ numeroRevision }: { numeroRevision: number }) {
  // biome-ignore lint/suspicious/noExplicitAny: RHF generics pattern matches the existing smart fields
  const methods = useForm<any>({
    defaultValues: {
      tipo_tramite: "OBRA_NUEVA",
      denominacion: "",
      numero_revision: numeroRevision,
    },
  });

  return (
    <FormProvider {...methods}>
      <TipoTramiteSmartField methods={methods} />
      <DenominacionProbe methods={methods} />
    </FormProvider>
  );
}

describe("TipoTramiteSmartField — número de revisión vivo", () => {
  it("usa el número de revisión del formulario (1 → sin ordinal)", async () => {
    render(<Harness numeroRevision={1} />);

    await waitFor(() =>
      expect(screen.getByTestId("denominacion")).toHaveTextContent(
        "OBRA NUEVA",
      ),
    );
  });

  it("usa el número de revisión del formulario (3 → ordinal 3RA)", async () => {
    render(<Harness numeroRevision={3} />);

    await waitFor(() =>
      expect(screen.getByTestId("denominacion")).toHaveTextContent(
        "OBRA NUEVA 3RA REVISIÓN",
      ),
    );
  });

  it("usa el número de revisión del formulario (5 → ordinal 5TA)", async () => {
    render(<Harness numeroRevision={5} />);

    await waitFor(() =>
      expect(screen.getByTestId("denominacion")).toHaveTextContent(
        "OBRA NUEVA 5TA REVISIÓN",
      ),
    );
  });
});
