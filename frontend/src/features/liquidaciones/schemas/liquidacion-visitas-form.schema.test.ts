import { describe, expect, it } from "vitest";
import { visitasFormSchema } from "./liquidacion-visitas-form.schema";

describe("visitasFormSchema category", () => {
  it.each(["1", "2", "3", "4"])("accepts canonical category %s", (value) => {
    expect(visitasFormSchema.shape.categoria.safeParse(value).success).toBe(
      true,
    );
  });

  it.each(["C1", "C2", "C3", "C4"])("rejects legacy category %s", (value) => {
    expect(visitasFormSchema.shape.categoria.safeParse(value).success).toBe(
      false,
    );
  });
});
