import { describe, expect, it } from "vitest";
import type { ZodNumber } from "zod";
import { m2FormSchema } from "./liquidacion-m2-form.schema";
import { visitasFormSchema } from "./liquidacion-visitas-form.schema";

const cases: Array<{
  schema: ZodNumber;
  required: string;
  invalid: string;
  positive: string;
}> = [
  {
    schema: m2FormSchema.shape.area_solicitada,
    required: "El área solicitada es requerida",
    invalid: "El área solicitada debe ser un número válido",
    positive: "El área solicitada debe ser positiva",
  },
  {
    schema: visitasFormSchema.shape.cantidad_visitas,
    required: "La cantidad de visitas es requerida",
    invalid: "La cantidad de visitas debe ser un número válido",
    positive: "La cantidad de visitas debe ser positiva",
  },
];

describe.each(cases)("numeric form schema", (messages) => {
  it("distinguishes required, invalid and non-positive values", () => {
    expect(messages.schema.safeParse(undefined).error?.issues[0].message).toBe(
      messages.required,
    );
    expect(messages.schema.safeParse("1").error?.issues[0].message).toBe(
      messages.invalid,
    );
    expect(messages.schema.safeParse(0).error?.issues[0].message).toBe(
      messages.positive,
    );
  });
});
