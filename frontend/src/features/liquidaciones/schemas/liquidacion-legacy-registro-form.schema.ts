import { z, type ZodType } from "zod";

export const legacyRegistroFieldsSchema = z.object({
  numero: z
    .number({ error: "El número histórico es requerido" })
    .int("El número histórico debe ser un entero")
    .positive("El número histórico debe ser mayor que cero")
    .max(2147483647, "El número histórico excede el máximo permitido"),
  fecha_registro: z
    .string({ error: "La fecha de registro es requerida" })
    .min(1, "La fecha de registro es requerida")
    .date("La fecha de registro no es válida"),
});

export type LegacyRegistroFormData = z.infer<
  typeof legacyRegistroFieldsSchema
>;

export function withLegacyRegistroFields<T>(schema: ZodType<T>): ZodType<T> {
  return schema.and(legacyRegistroFieldsSchema) as ZodType<T>;
}
