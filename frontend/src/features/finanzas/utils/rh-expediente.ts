/**
 * Utilidades del `expediente` editable del wizard RH mensual (paso 2).
 *
 * Reglas del flujo (contrato de la capability `rh-mensual-browse-edit`):
 * - El `expediente` se edita SÓLO en la grid de SELECCIONADAS. Las candidatas
 *   y la previsualización (paso 3) son de solo lectura.
 * - El `expediente` viaja DENTRO del payload del RH (creación y edición): el
 *   backend lo persiste en la MISMA transacción que la mutación del RH. El
 *   frontend NO emite ningún `PATCH /liquidaciones/generales/{id}`.
 * - El valor es POR liquidación: nunca metadata compartida de la asignación.
 * - Un valor vacío es una limpieza (el backend no acepta NULL hoy).
 *
 * Este módulo es puro: no depende de React ni del cliente HTTP.
 */

/**
 * Resuelve el valor de `expediente` a enviar por item del payload del RH.
 *
 * Prioridad: borrador del wizard → valor persistido de la liquidación → `""`.
 * - El borrador manda: es el valor que el usuario editó (`""` = limpiar).
 * - Sin borrador se envía el valor persistido: el backend lo compara con el
 *   suyo y lo trata como no-op (no escribe nada, no dispara el guard de PAGADA).
 * - Sin valor persistido se envía `""`: el backend lo compara con el suyo
 *   (vacío) y tampoco escribe nada.
 */
export function resolveExpedienteToSend(
  draft: string | undefined,
  persisted?: string | null,
): string {
  return draft ?? persisted ?? "";
}
