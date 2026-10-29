import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { z } from "zod";

import { LiquidacionFormShell } from "./LiquidacionFormShell";

/**
 * Réplica del layout real de `AppFormModal`:
 * - `headerActions` se renderiza FUERA del `FormProvider` (vive en el header
 *   del modal, por encima del body con el form).
 * - el body (children) sí se renderiza DENTRO del `FormProvider`.
 *
 * Esa es exactamente la razón del puente `NumeroRevisionWatcher`.
 */
vi.mock("@/components-app/forms/AppFormModal", async () => {
  const { FormProvider, useForm } = await import("react-hook-form");
  return {
    AppFormModal: ({
      headerActions,
      children,
      initialData,
    }: {
      headerActions?: ReactNode;
      children: (props: { methods: unknown }) => ReactNode;
      initialData?: Record<string, unknown>;
    }) => {
      const methods = useForm({ defaultValues: initialData });
      return (
        <>
          {headerActions}
          <FormProvider {...methods}>{children({ methods })}</FormProvider>
        </>
      );
    },
  };
});

vi.mock("@/errors", () => ({
  notify: { success: vi.fn() },
}));

const sourceItem = {
  liquidacion_general: {
    id: "liquidacion-id",
    sub_total: 10,
    total: 10,
    numero_revision: 3,
  },
};

describe("LiquidacionFormShell — número de revisión vivo", () => {
  it("muestra en el badge el valor del campo numero_revision del formulario", async () => {
    render(
      <LiquidacionFormShell
        open
        onOpenChange={vi.fn()}
        mode="edit"
        sourceItem={sourceItem}
        schema={z.object({ numero_revision: z.number() })}
        initialData={{ numero_revision: 3 }}
        eyebrow="Test"
        icon={<span />}
        titlePrefix="Edit"
        primaryLabel="Save"
        primaryLoadingLabel="Saving"
        primaryLoading={false}
        renderBody={({ methods }) => (
          <button
            type="button"
            onClick={() => methods.setValue("numero_revision", 5)}
          >
            Cambiar revisión
          </button>
        )}
      />,
    );

    await waitFor(() => expect(screen.getByText("#3")).toBeInTheDocument());
  });

  it("refleja al instante el cambio del número de revisión en la cabecera", async () => {
    render(
      <LiquidacionFormShell
        open
        onOpenChange={vi.fn()}
        mode="edit"
        sourceItem={sourceItem}
        schema={z.object({ numero_revision: z.number() })}
        initialData={{ numero_revision: 3 }}
        eyebrow="Test"
        icon={<span />}
        titlePrefix="Edit"
        primaryLabel="Save"
        primaryLoadingLabel="Saving"
        primaryLoading={false}
        renderBody={({ methods }) => (
          <button
            type="button"
            onClick={() => methods.setValue("numero_revision", 5)}
          >
            Cambiar revisión
          </button>
        )}
      />,
    );

    await waitFor(() => expect(screen.getByText("#3")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "Cambiar revisión" }));

    await waitFor(() => expect(screen.getByText("#5")).toBeInTheDocument());
    expect(screen.queryByText("#3")).not.toBeInTheDocument();
  });

  it("mantiene la revisión fija (1) cuando el formulario no tiene el campo (Inspección de Obra)", async () => {
    render(
      <LiquidacionFormShell
        open
        onOpenChange={vi.fn()}
        mode="edit"
        sourceItem={{
          ...sourceItem,
          liquidacion_general: {
            ...sourceItem.liquidacion_general,
            numero_revision: 1,
          },
        }}
        schema={z.object({ cantidad_visitas: z.number() })}
        initialData={{ cantidad_visitas: 2 }}
        eyebrow="Test"
        icon={<span />}
        titlePrefix="Edit"
        primaryLabel="Save"
        primaryLoadingLabel="Saving"
        primaryLoading={false}
        renderBody={() => null}
      />,
    );

    await waitFor(() => expect(screen.getByText("#1")).toBeInTheDocument());
  });
});
