import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";
import { describe, expect, it } from "vitest";
import { MoneyInput } from "./MoneyInput";

interface FormValues {
  amount?: number;
}

function MoneyInputHarness({ error }: { error?: string }) {
  const methods = useForm<FormValues>({
    defaultValues: { amount: undefined },
  });
  const value = useWatch({ control: methods.control, name: "amount" });

  useEffect(() => {
    if (error) methods.setError("amount", { message: error });
  }, [error, methods]);

  return (
    <>
      <MoneyInput name="amount" label="Amount" control={methods.control} />
      <output data-testid="domain-value">
        {value === undefined ? "undefined" : `${typeof value}:${value}`}
      </output>
    </>
  );
}

describe("MoneyInput", () => {
  it("keeps partial decimals in the display while emitting numbers", () => {
    render(<MoneyInputHarness />);
    const input = screen.getByLabelText("Amount");

    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "S/ 12." } });
    expect(input).toHaveValue("S/ 12.");
    expect(screen.getByTestId("domain-value")).toHaveTextContent("number:12");

    fireEvent.change(input, { target: { value: "S/ 12.05" } });
    expect(input).toHaveValue("S/ 12.05");
    expect(screen.getByTestId("domain-value")).toHaveTextContent(
      "number:12.05",
    );
  });

  it("maps an empty display to undefined instead of zero", () => {
    render(<MoneyInputHarness />);
    const input = screen.getByLabelText("Amount");

    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "S/ 9" } });
    fireEvent.change(input, { target: { value: "" } });

    expect(input).toHaveValue("");
    expect(screen.getByTestId("domain-value")).toHaveTextContent("undefined");
  });

  it("renders the actual RHF error", async () => {
    render(<MoneyInputHarness error="Amount is required" />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Amount is required",
    );
    await waitFor(() =>
      expect(screen.getByLabelText("Amount")).toHaveAttribute(
        "aria-invalid",
        "true",
      ),
    );
    expect(screen.getByLabelText("Amount")).toHaveClass("border-destructive");
  });
});
