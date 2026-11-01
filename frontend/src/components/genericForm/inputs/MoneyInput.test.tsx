import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Ruler } from "lucide-react";
import { useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";
import { describe, expect, it } from "vitest";
import { MoneyInput } from "./MoneyInput";

interface FormValues {
  amount?: number;
}

function MoneyInputHarness({
  error,
  icon,
}: {
  error?: string;
  icon?: typeof Ruler;
}) {
  const methods = useForm<FormValues>({
    defaultValues: { amount: undefined },
  });
  const value = useWatch({ control: methods.control, name: "amount" });

  useEffect(() => {
    if (error) methods.setError("amount", { message: error });
  }, [error, methods]);

  return (
    <>
      <MoneyInput
        name="amount"
        label="Amount"
        control={methods.control}
        icon={icon}
      />
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
    fireEvent.change(input, { target: { value: "12." } });
    expect(input).toHaveValue("12.");
    expect(screen.getByTestId("domain-value")).toHaveTextContent("number:12");

    fireEvent.change(input, { target: { value: "12.05" } });
    expect(input).toHaveValue("12.05");
    expect(screen.getByTestId("domain-value")).toHaveTextContent(
      "number:12.05",
    );
  });

  it("formats thousands only after leaving the input", () => {
    render(<MoneyInputHarness />);
    const input = screen.getByLabelText("Amount");

    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "4000000.45" } });
    expect(input).toHaveValue("4000000.45");

    fireEvent.blur(input);
    expect(input).toHaveValue("S/ 4 000 000.45");

    fireEvent.focus(input);
    expect(input).toHaveValue("4000000.45");
  });

  it("limits values to ten integer digits and two decimals", () => {
    render(<MoneyInputHarness />);
    const input = screen.getByLabelText("Amount");

    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "123456789012.345" } });

    expect(input).toHaveValue("1234567890.34");
    expect(screen.getByTestId("domain-value")).toHaveTextContent(
      "number:1234567890.34",
    );
  });

  it("renders a caller-provided icon", () => {
    const { container } = render(<MoneyInputHarness icon={Ruler} />);

    expect(container.querySelector(".lucide-ruler")).toBeInTheDocument();
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
