/**
 * contacto-utils — Helpers de transformación para el campo `contacto`.
 *
 * Convierte la forma del backend (ContactoOutput — `ContactoOutputSchema`)
 * a la forma del form (ContactoInline — `contactoInlineSchema.optional()`).
 *
 * Usado por los 6 modales al construir `initialData` para que el smart field
 * `<ContactoSmartField />` muestre el contacto existente en modo edit / nueva-revision.
 */
import type { ContactoInline } from "../schemas/liquidacion-form-base.schema";

export function toContactoInline(
  raw: unknown,
): ContactoInline | undefined {
  if (!raw || typeof raw !== "object") return undefined;
  const c = raw as Record<string, unknown>;
  if (typeof c.nombres !== "string" || c.nombres.length === 0) return undefined;
  const result: ContactoInline = { nombres: c.nombres };
  if (typeof c.apellidos === "string") result.apellidos = c.apellidos;
  if (typeof c.dni === "string") result.dni = c.dni;
  if (typeof c.cargo === "string") result.cargo = c.cargo;
  if (typeof c.telefono === "string") result.telefono = c.telefono;
  if (typeof c.celular === "string") result.celular = c.celular;
  if (typeof c.email === "string") result.email = c.email;
  return result;
}