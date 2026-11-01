import { act, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { z } from "zod";
import { GenericForm } from "./GenericForm";

const schema = z.object({ email: z.string() });
type FormValues = z.infer<typeof schema>;

function apiError(data: unknown, status = 422) {
  return { response: { data, status } };
}

/**
 * Renders the form and exposes the submit handler so the test can await the
 * resulting promise (the form rethrows the submission error on purpose).
 */
function renderForm(onSubmit: (data: FormValues) => Promise<unknown>) {
  let submit: (() => Promise<void>) | undefined;
  let banner: { type: "success" | "error"; message: string } | null = null;

  const view = render(
    <GenericForm<FormValues> schema={schema} onSubmit={onSubmit}>
      {({ methods, onSubmit: formSubmit, submissionMessage }) => {
        // El render prop tipa `onSubmit` como `() => void`, pero en runtime
        // devuelve la promesa de React Hook Form (necesaria para capturar el
        // error de submit que el form relanza).
        submit = formSubmit as unknown as () => Promise<void>;
        banner = submissionMessage;
        const emailError = methods.formState.errors.email?.message;
        return (
          <>
            <input aria-label="Email" {...methods.register("email")} />
            {emailError ? (
              <span data-testid="email-error">{emailError}</span>
            ) : null}
          </>
        );
      }}
    </GenericForm>,
  );

  return {
    view,
    submit: async () => {
      await act(async () => {
        await submit?.().catch(() => undefined);
      });
    },
    getBanner: () => banner,
  };
}

describe("GenericForm messages", () => {
  it("shows the API success message in the banner instead of a generic text", async () => {
    const form = renderForm(async () => ({
      success: true,
      message: "Persona natural creada correctamente.",
    }));

    await form.submit();

    expect(form.getBanner()).toEqual({
      type: "success",
      message: "Persona natural creada correctamente.",
    });
  });

  it("attaches server field errors to the matching input", async () => {
    const form = renderForm(async () => {
      throw apiError({
        error: {
          code: "VALIDATION_ERROR",
          details: {
            email: "Ingresa un correo válido.",
            non_field_errors: "Revisa los datos del formulario.",
          },
        },
      });
    });

    await form.submit();

    expect(form.getBanner()).toEqual({
      type: "error",
      message:
        "email: Ingresa un correo válido.; Revisa los datos del formulario.",
    });
    expect(screen.getByTestId("email-error")).toHaveTextContent(
      "Ingresa un correo válido.",
    );
    // The global error must never become an input error.
    expect(screen.queryByText("Revisa los datos del formulario.")).toBeNull();
  });

  it("never renders the global error key", async () => {
    const form = renderForm(async () => {
      throw apiError({
        error: {
          code: "VALIDATION_ERROR",
          details: { non_field_errors: ["Revisa los datos del formulario."] },
        },
      });
    });

    await form.submit();

    expect(form.getBanner()?.message).not.toContain("non_field_errors");
    expect(form.getBanner()?.message).toBe("Revisa los datos del formulario.");
  });
});
