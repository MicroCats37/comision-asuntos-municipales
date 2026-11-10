/**
 * rh-expediente — resolución del valor de `expediente` a enviar en el payload
 * del RH mensual (paso 2).
 *
 * Cubre:
 * - el borrador del wizard manda sobre el valor persistido;
 * - sin borrador se envía el valor persistido (el backend lo trata como no-op);
 * - un borrador vacío es una limpieza (`""`);
 * - sin borrador ni valor persistido se envía `""`.
 *
 * El módulo es puro: sin React, sin HTTP y sin efectos secundarios.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la verificación
 * corre en la fase final de SDD (tarea 5.4).
 */
import { describe, expect, it } from "vitest";

import { resolveExpedienteToSend } from "./rh-expediente";

describe("resolveExpedienteToSend — valor a enviar por item", () => {
  it("envía el borrador cuando el usuario editó la fila", () => {
    expect(resolveExpedienteToSend("EXP-NUEVO", "EXP-001")).toBe("EXP-NUEVO");
  });

  it("envía el valor persistido cuando la fila no se editó", () => {
    expect(resolveExpedienteToSend(undefined, "EXP-001")).toBe("EXP-001");
  });

  it("envía el string vacío cuando el usuario limpió la fila", () => {
    // "" es una limpieza: no debe caer al valor persistido.
    expect(resolveExpedienteToSend("", "EXP-001")).toBe("");
  });

  it("envía el string vacío cuando la liquidación no tiene expediente", () => {
    expect(resolveExpedienteToSend(undefined, null)).toBe("");
    expect(resolveExpedienteToSend(undefined, undefined)).toBe("");
  });

  it("no modifica el valor persistido cuando no hay borrador", () => {
    // El valor persistido se envía tal cual: el backend lo compara con el suyo
    // y no escribe nada (no-op).
    expect(resolveExpedienteToSend(undefined, "  EXP-001  ")).toBe("  EXP-001  ");
  });
});
