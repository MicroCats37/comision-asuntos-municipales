import { zodResolver } from "@hookform/resolvers/zod";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useForm } from "react-hook-form";
import { describe, expect, it } from "vitest";
import { z } from "zod";
import { InputSearchableSelect } from "./InputSearchableSelect";

/**
 * Un select opcional se declara en Zod como `z.string().optional()`. Si al
 * deseleccionar el input emite `null`, la validación falla con
 * "Invalid input: expected string, received null".
 */
const filtroSchema = z.object({
  distrito_id: z.string().optional(),
});

function Harness() {
  const { control, register, formState, watch } = useForm({
    resolver: zodResolver(filtroSchema),
    defaultValues: { distrito_id: "d1" },
  });
  const valor = watch("distrito_id");

  return (
    <form>
      <InputSearchableSelect
        field={{
          name: "distrito_id",
          label: "Distrito",
          type: "searchable-select",
          options: [{ value: "d1", label: "Miraflores" }],
        }}
        control={control as never}
        error={formState.errors.distrito_id}
        register={register as never}
        id="distrito"
      />
      <span data-testid="valor">
        {valor === null ? "null" : String(valor ?? "")}
      </span>
    </form>
  );
}

describe("InputSearchableSelect", () => {
  it("deja el campo vacío (no null) al deseleccionar", async () => {
    render(<Harness />);

    fireEvent.click(screen.getByLabelText("Limpiar selección"));

    await waitFor(() => {
      expect(screen.getByTestId("valor").textContent).toBe("");
    });
  });

  it("no muestra el error de validación al deseleccionar", async () => {
    render(<Harness />);

    fireEvent.click(screen.getByLabelText("Limpiar selección"));

    await waitFor(() => {
      expect(
        screen.queryByText(/expected string, received null/i),
      ).not.toBeInTheDocument();
    });
  });
});
