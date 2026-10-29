import { describe, expect, it } from "vitest";
import { edificacionesFormSchema } from "./liquidacion-edificaciones-form.schema";
import { numeroRevisionFormSchema } from "./liquidacion-form-base.schema";
import { habilitacionUrbanaFormSchema } from "./liquidacion-habilitacion-urbana-form.schema";
import { impactoVialFormSchema } from "./liquidacion-impacto-vial-form.schema";
import { mecanicaSuelosFormSchema } from "./liquidacion-mecanica-suelos-form.schema";
import { taludesFormSchema } from "./liquidacion-taludes-form.schema";
import { visitasFormSchema } from "./liquidacion-visitas-form.schema";

/** Los CINCO tipos con revisión editable (contrato `NumeroRevisionRequeridoMixin`). */
const SCHEMAS_CON_REVISION = [
  edificacionesFormSchema,
  habilitacionUrbanaFormSchema,
  mecanicaSuelosFormSchema,
  taludesFormSchema,
  impactoVialFormSchema,
];

const mensajesDe = (resultado: {
  success: boolean;
  error?: { issues: { message: string }[] };
}) => resultado.error?.issues.map((issue) => issue.message) ?? [];

describe("numero_revision — schema compartido de formularios", () => {
  it("exige el número de revisión en los cinco tipos con revisión editable", () => {
    for (const schema of SCHEMAS_CON_REVISION) {
      expect(schema.shape).toHaveProperty("numero_revision");

      const resultado = schema.shape.numero_revision.safeParse(undefined);
      expect(resultado.success).toBe(false);
      expect(mensajesDe(resultado)).toContain(
        "El número de revisión es requerido",
      );
    }
  });

  it("acepta 1, 3 y 5", () => {
    for (const valor of [1, 3, 5]) {
      expect(
        numeroRevisionFormSchema.shape.numero_revision.safeParse(valor).success,
      ).toBe(true);
    }
  });

  it("rechaza los números fuera del conjunto permitido", () => {
    for (const valor of [0, 2, 4, 6, -1]) {
      const resultado =
        numeroRevisionFormSchema.shape.numero_revision.safeParse(valor);
      expect(resultado.success).toBe(false);
      expect(mensajesDe(resultado)).toContain(
        "El número de revisión debe ser 1, 3 o 5",
      );
    }
  });

  it("rechaza valores no enteros", () => {
    const resultado =
      numeroRevisionFormSchema.shape.numero_revision.safeParse(2.5);
    expect(resultado.success).toBe(false);
    expect(mensajesDe(resultado)).toContain(
      "El número de revisión debe ser un entero",
    );
  });

  it("rechaza valores no numéricos", () => {
    const resultado =
      numeroRevisionFormSchema.shape.numero_revision.safeParse("3");
    expect(resultado.success).toBe(false);
    expect(mensajesDe(resultado)).toContain(
      "El número de revisión debe ser un número válido",
    );
  });

  it("mantiene a Inspección de Obra fuera del contrato de revisión", () => {
    // IO es revision-less: su schema no expone el campo y su liquidación
    // permanece fija en revisión 1.
    expect(visitasFormSchema.shape).not.toHaveProperty("numero_revision");
  });
});
