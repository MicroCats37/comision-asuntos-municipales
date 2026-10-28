import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import type { UseFormReturn } from "react-hook-form";
import { describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { GenericForm } from "./GenericForm";

const schema = z.object({ name: z.string(), city: z.string().optional() });
type FormValues = z.infer<typeof schema>;

function FormHarness({ initialData }: { initialData?: Partial<FormValues> }) {
  return (
    <GenericForm<FormValues>
      schema={schema}
      initialData={initialData}
      onSubmit={vi.fn()}
    >
      {({ methods }) => (
        <>
          <input aria-label="Name" {...methods.register("name")} />
          <input aria-label="City" {...methods.register("city")} />
        </>
      )}
    </GenericForm>
  );
}

function AutoFilledName({ methods }: { methods: UseFormReturn<FormValues> }) {
  useEffect(() => {
    methods.setValue("name", "auto-selected");
  }, [methods]);

  return <input aria-label="Name" {...methods.register("name")} />;
}

describe("GenericForm initial data", () => {
  it("does not wipe a dirty field for deep-equal or later initial data", async () => {
    const view = render(<FormHarness initialData={{ name: "server" }} />);
    const input = screen.getByLabelText("Name");
    expect(input).toHaveValue("server");

    fireEvent.change(input, { target: { value: "user edit" } });
    view.rerender(<FormHarness initialData={{ name: "server" }} />);
    expect(input).toHaveValue("user edit");

    view.rerender(<FormHarness initialData={{ name: "server refresh" }} />);
    await waitFor(() => expect(input).toHaveValue("user edit"));
  });

  it("hydrates pristine fields when async initial data arrives", async () => {
    const view = render(<FormHarness />);
    expect(screen.getByLabelText("Name")).toHaveValue("");

    view.rerender(<FormHarness initialData={{ name: "late data" }} />);
    await waitFor(() =>
      expect(screen.getByLabelText("Name")).toHaveValue("late data"),
    );
  });

  it("updates pristine fields without replacing dirty fields", async () => {
    const view = render(
      <FormHarness initialData={{ name: "server", city: "Lima" }} />,
    );

    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "user edit" },
    });
    view.rerender(
      <FormHarness initialData={{ name: "server refresh", city: "Cusco" }} />,
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Name")).toHaveValue("user edit");
      expect(screen.getByLabelText("City")).toHaveValue("Cusco");
    });
  });

  it("does not overwrite a child auto-selection after mount", async () => {
    render(
      <GenericForm<FormValues>
        schema={schema}
        initialData={{ name: "server" }}
        onSubmit={vi.fn()}
      >
        {({ methods }) => <AutoFilledName methods={methods} />}
      </GenericForm>,
    );

    await waitFor(() =>
      expect(screen.getByLabelText("Name")).toHaveValue("auto-selected"),
    );
  });
});
