import { describe, expect, it } from "vitest";
import { handleApiError } from "./error-handler";

function apiError(data: unknown, status = 400) {
  return { response: { data, status } };
}

describe("handleApiError", () => {
  it("prioritizes the explicit message from the API error envelope", () => {
    const error = apiError({
      success: false,
      error: {
        code: "CONFLICT",
        message: "La liquidación ya existe.",
        details: { non_field_errors: "Este detalle no debe reemplazarlo." },
      },
    });

    expect(handleApiError(error)).toMatchObject({
      message: "La liquidación ya existe.",
      status: 400,
    });
  });

  it("shows a global non_field_errors string without its key", () => {
    const error = apiError({
      error: {
        details: { non_field_errors: "No se puede completar la operación." },
      },
    });

    expect(handleApiError(error).message).toBe(
      "No se puede completar la operación.",
    );
  });

  it("flattens nested non_field_errors lists without adding labels", () => {
    const error = apiError({
      error: {
        details: {
          non_field_errors: [
            "La combinación ya existe.",
            ["Selecciona valores diferentes."],
          ],
        },
      },
    });

    expect(handleApiError(error).message).toBe(
      "La combinación ya existe.; Selecciona valores diferentes.",
    );
  });

  it("keeps real field paths while treating non_field_errors as global", () => {
    const error = apiError({
      error: {
        details: {
          email: ["Ingresa un correo válido."],
          persona: { documento: "El documento es obligatorio." },
          non_field_errors: { messages: ["Los datos están duplicados."] },
        },
      },
    });

    expect(handleApiError(error).message).toBe(
      "email: Ingresa un correo válido.; persona.documento: El documento es obligatorio.; Los datos están duplicados.",
    );
  });

  it("joins an array of messages carried by error.message", () => {
    const error = apiError({
      error: { message: ["Primero.", "Segundo."] },
    });

    expect(handleApiError(error).message).toBe("Primero.; Segundo.");
  });

  it("keeps the field labels of a validation error and exposes fieldErrors", () => {
    const error = apiError(
      {
        error: {
          code: "VALIDATION_ERROR",
          message: "Error de validación.",
          details: {
            email: "Ingresa un correo válido.",
            razon_social: "Este campo es requerido.",
          },
        },
      },
      422,
    );

    const result = handleApiError(error);

    expect(result.message).toContain("email: Ingresa un correo válido.");
    expect(result.message).toContain("razon_social: Este campo es requerido.");
    expect(result.fieldErrors).toEqual({
      email: "Ingresa un correo válido.",
      razon_social: "Este campo es requerido.",
    });
  });

  it("never turns a global validation error into a field error", () => {
    const error = apiError(
      {
        error: {
          code: "VALIDATION_ERROR",
          details: {
            non_field_errors: [
              "Los datos están duplicados.",
              "Selecciona valores diferentes.",
            ],
          },
        },
      },
      422,
    );

    const result = handleApiError(error);

    expect(result.message).toBe(
      "Los datos están duplicados.; Selecciona valores diferentes.",
    );
    expect(result.fieldErrors ?? {}).toEqual({});
    expect(result.message).not.toContain("non_field_errors");
  });

  it("flattens Django message_dict lists keeping the real field labels", () => {
    const error = apiError(
      {
        error: {
          code: "VALIDATION_ERROR",
          details: {
            non_field_errors: ["Los datos están duplicados."],
            email: ["Ingresa un correo válido."],
          },
        },
      },
      400,
    );

    const result = handleApiError(error);

    expect(result.message).toBe(
      "email: Ingresa un correo válido.; Los datos están duplicados.",
    );
    expect(result.fieldErrors).toEqual({ email: "Ingresa un correo válido." });
  });

  it("reads the Django Ninja default validation body", () => {
    const error = apiError(
      {
        detail: [
          {
            loc: ["body", "email"],
            msg: "Ingresa un correo válido.",
            type: "value_error",
          },
          {
            loc: ["body", "nombre"],
            msg: "Este campo es requerido.",
            type: "missing",
          },
        ],
      },
      422,
    );

    expect(handleApiError(error).message).toBe(
      "email: Ingresa un correo válido.; nombre: Este campo es requerido.",
    );
  });

  it("renders a plain string body without crashing", () => {
    expect(handleApiError(apiError("Service unavailable")).message).toBe(
      "Service unavailable",
    );
  });

  it("renders a numeric body without crashing", () => {
    expect(handleApiError(apiError(500)).message).toBe("500");
  });

  it("renders numeric and boolean detail values as text", () => {
    const numeric = apiError({
      error: { details: { non_field_errors: 42 } },
    });
    expect(handleApiError(numeric).message).toBe("42");

    const boolean = apiError({
      error: { details: { activo: true } },
    });
    expect(handleApiError(boolean).message).toBe("activo: true");
  });

  it("falls back to a readable message when the payload carries none", () => {
    expect(handleApiError(apiError({})).message).toBe(
      "Ocurrió un error al procesar la solicitud.",
    );
  });

  it("uses the envelope message of an internal error without details noise", () => {
    const error = apiError({
      error: {
        code: "INTERNAL_ERROR",
        message: "Ocurrió un error inesperado.",
      },
      success: false,
    });

    expect(handleApiError(error)).toMatchObject({
      message: "Ocurrió un error inesperado.",
      status: 400,
    });
  });
});
