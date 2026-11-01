import { render, screen } from "@testing-library/react";
import { useForm } from "react-hook-form";
import { describe, expect, it } from "vitest";
import { LegacyRegistroFields } from "./LegacyRegistroFields";

function Harness() {
  const methods = useForm({
    defaultValues: { numero: undefined, fecha_registro: "" },
  });
  return <LegacyRegistroFields methods={methods} />;
}

describe("LegacyRegistroFields", () => {
  it("renderiza la identidad histórica sobre React Hook Form", () => {
    render(<Harness />);

    expect(screen.getByLabelText(/Número histórico/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Fecha de registro/i)).toBeInTheDocument();
  });
});
