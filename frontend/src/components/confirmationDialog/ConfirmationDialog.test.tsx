/**
 * ConfirmationDialog — behaviour matrix of the shared destructive primitive.
 *
 * These tests are WRITTEN but NOT executed in this phase: the consolidated
 * execution belongs to the final verification module.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";
import { ConfirmationDialog } from "./ConfirmationDialog";

type DialogProps = ComponentProps<typeof ConfirmationDialog>;

const TOK = "CIP-100001";

/** Typed rule with the RH mensual wording. */
const regla = (expectedText: string) => ({
  expectedText,
  label: "CIP del delegado",
  prompt: `Para confirmar, escribe el CIP ${expectedText}`,
});

function renderDialog(overrides: Partial<DialogProps> = {}) {
  const props: DialogProps = {
    open: true,
    onOpenChange: vi.fn(),
    title: "Eliminar recibo de delegado",
    confirmLabel: "Eliminar",
    onConfirm: vi.fn(),
    ...overrides,
  };
  const view = render(<ConfirmationDialog {...props} />);
  return { ...view, props };
}

const input = () => screen.getByRole("textbox");
const confirmar = () => screen.getByRole("button", { name: "Eliminar" });
const formulario = () => input().closest("form") as HTMLFormElement;

describe("ConfirmationDialog", () => {
  it.each([
    ["sin regla", undefined],
    ["con texto esperado en blanco", { expectedText: "   " }],
  ])("%s: no hay input y el click confirma una sola vez", (_caso, rule) => {
    const { props } = renderDialog({ typedConfirmation: rule });

    expect(screen.queryByRole("textbox")).toBeNull();
    expect(confirmar()).toBeEnabled();

    fireEvent.click(confirmar());
    expect(props.onConfirm).toHaveBeenCalledTimes(1);
  });

  it("con regla: input + prompt y confirm deshabilitado", () => {
    renderDialog({ typedConfirmation: regla(TOK) });

    expect(input()).toBeInTheDocument();
    expect(
      screen.getByText(`Para confirmar, escribe el CIP ${TOK}`),
    ).toBeInTheDocument();
    expect(confirmar()).toBeDisabled();
  });

  it("el valor correcto (trim + case-insensitive) habilita el confirm", () => {
    renderDialog({ typedConfirmation: regla(TOK) });

    fireEvent.change(input(), { target: { value: ` ${TOK.toLowerCase()} ` } });

    expect(confirmar()).toBeEnabled();
  });

  it("un valor distinto no habilita ni confirma, y Enter marca el error", () => {
    const { props } = renderDialog({ typedConfirmation: regla(TOK) });

    fireEvent.change(input(), { target: { value: "CIP-1000010" } });
    expect(confirmar()).toBeDisabled();
    fireEvent.click(confirmar());
    fireEvent.submit(formulario());

    expect(props.onConfirm).not.toHaveBeenCalled();
    expect(input()).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "El código no coincide",
    );
  });

  it("el valor se reinicia cuando cambia el texto esperado", () => {
    const { props, rerender } = renderDialog({
      typedConfirmation: regla(TOK),
    });

    fireEvent.change(input(), { target: { value: TOK } });
    props.typedConfirmation = regla("CIP-200002");
    rerender(<ConfirmationDialog {...props} />);

    expect(input()).toHaveValue("");
    expect(confirmar()).toBeDisabled();
  });

  it("Enter con el valor correcto confirma una sola vez", () => {
    const { props } = renderDialog({ typedConfirmation: regla(TOK) });

    fireEvent.change(input(), { target: { value: TOK } });
    fireEvent.submit(formulario());

    expect(props.onConfirm).toHaveBeenCalledTimes(1);
  });

  it("Escape nunca confirma", () => {
    const { props } = renderDialog({ typedConfirmation: regla(TOK) });

    fireEvent.keyDown(document, { key: "Escape" });

    expect(props.onConfirm).not.toHaveBeenCalled();
  });

  it("el input y el dialogo exponen sus nombres accesibles", () => {
    renderDialog({ typedConfirmation: regla(TOK) });

    expect(input()).toHaveAccessibleName("CIP del delegado");
    expect(input()).toHaveAccessibleDescription(
      `Para confirmar, escribe el CIP ${TOK}`,
    );
    expect(screen.getByRole("dialog")).toHaveAccessibleName(
      "Eliminar recibo de delegado",
    );
  });
});
