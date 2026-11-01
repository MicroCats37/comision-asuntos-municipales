import { fireEvent, render, screen } from "@testing-library/react";
import { useForm, useWatch } from "react-hook-form";
import { describe, expect, it } from "vitest";
import { DenominacionField } from "./LiquidacionFormBodyBase";

interface FormValues {
  denominacion: string;
}

function DenominacionHarness() {
  const methods = useForm<FormValues>({
    defaultValues: { denominacion: "" },
  });
  const value = useWatch({
    control: methods.control,
    name: "denominacion",
  });

  return (
    <>
      <DenominacionField control={methods.control as never} />
      <output data-testid="denominacion-value">{value}</output>
    </>
  );
}

describe("DenominacionField", () => {
  it("uses an expanding textarea and preserves uppercase normalization", () => {
    render(<DenominacionHarness />);
    const textarea = screen.getByLabelText("Denominación");

    expect(textarea.tagName).toBe("TEXTAREA");
    expect(textarea).toHaveClass("field-sizing-content");
    expect(textarea).toHaveAttribute("maxlength", "500");

    fireEvent.change(textarea, {
      target: { value: "proyecto residencial\nsegunda etapa" },
    });

    expect(textarea).toHaveValue("PROYECTO RESIDENCIAL\nSEGUNDA ETAPA");
    expect(screen.getByTestId("denominacion-value")).toHaveTextContent(
      "PROYECTO RESIDENCIAL SEGUNDA ETAPA",
    );
  });
});
