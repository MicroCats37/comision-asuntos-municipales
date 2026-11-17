/**
 * Continuidad de visitas de IO — payload, schema y defaults.
 *
 * Contrato cubierto (io-continuidad-visitas-impacto, io-continuity-server-quote):
 *  · El bloque de continuidad es OPCIONAL: sin activarlo, la petición es
 *    idéntica a la vigente (sin la clave `continuidad`).
 *  · El bloque solo viaja en `POST /nueva-liquidacion` (nunca en legacy).
 *  · El dato que el usuario DECLARA es el BRUTO pagado en la IO previa
 *    (`total_pagado_previa`): si viaja, MANDA y el neto (`subtotal_credito`)
 *    se omite (nunca se envían las dos cifras del mismo dinero).
 *  · `monto_acumulado` / `total_acumulado` NO se envían: los calcula el
 *    servidor.
 */
import { describe, expect, it } from "vitest";
import { deriveContinuidadDefaults } from "../components/forms/inspeccion-obra/ContinuidadVisitasPanel";
import { buildCrearInspeccionObraPayload } from "../hooks/useCrearInspeccionObra";
import type { LiquidacionInspeccionObraListItem } from "./liquidacion-inspeccion-obra.schema";
import {
  continuidadVisitasFormSchema,
  type VisitasFormData,
  visitasFormSchema,
} from "./liquidacion-visitas-form.schema";

const visitasFormData = {
  cantidad_visitas: 3,
  categoria: "4",
  tarifa_visitas_id: "tarifa-2",
  inspector_operacion_id: "operacion-1",
  municipalidad_id: "municipalidad-1",
  expediente: "EXP-1",
  denominacion: "Proyecto",
  nombre_propietario: "Propietario",
  direccion: "Direccion",
  entidad_tipo_documento: "RUC",
  entidad_numero_documento: "20123456789",
  entidad_razon_social: "Entidad",
} as VisitasFormData;

describe("payload de IO con continuidad", () => {
  it("omite el bloque de continuidad cuando la IO es normal", () => {
    const payload = buildCrearInspeccionObraPayload(visitasFormData);

    expect(payload.liquidacion_especifica).not.toHaveProperty("continuidad");
    expect(Object.hasOwn(payload.liquidacion_especifica, "continuidad")).toBe(
      false,
    );
  });

  it("mantiene el payload idéntico al vigente cuando la continuidad está apagada", () => {
    const payload = buildCrearInspeccionObraPayload(visitasFormData);

    // El bloque específico es EXACTAMENTE el de siempre: sin `continuidad`
    // y sin ninguna clave nueva.
    expect(payload.liquidacion_especifica).toEqual({
      datos: { cantidad_visitas: 3 },
      tarifa: { tarifa_visitas_id: "tarifa-2" },
      inspector_operacion_id: "operacion-1",
    });
    expect(Object.keys(payload.liquidacion_especifica).sort()).toEqual([
      "datos",
      "inspector_operacion_id",
      "tarifa",
    ]);
  });

  it("adjunta el bloque de continuidad cuando está activo", () => {
    const payload = buildCrearInspeccionObraPayload({
      ...visitasFormData,
      continuidad: {
        liquidacion_previa_id: "previa-1",
        subtotal_credito: 515,
      },
    });

    expect(payload.liquidacion_especifica.continuidad).toEqual({
      liquidacion_previa_id: "previa-1",
      subtotal_credito: 515,
    });
  });

  it("el bruto declarado MANDA: viaja el bruto y NO el neto", () => {
    const payload = buildCrearInspeccionObraPayload({
      ...visitasFormData,
      continuidad: {
        liquidacion_previa_id: "previa-1",
        total_pagado_previa: 212.6,
        subtotal_credito: 999,
      },
    });

    expect(payload.liquidacion_especifica.continuidad).toEqual({
      liquidacion_previa_id: "previa-1",
      total_pagado_previa: 212.6,
    });
    expect(payload.liquidacion_especifica.continuidad).not.toHaveProperty(
      "subtotal_credito",
    );
  });

  it("no envía los importes que calcula el servidor", () => {
    const payload = buildCrearInspeccionObraPayload({
      ...visitasFormData,
      continuidad: {
        liquidacion_previa_id: "previa-1",
        total_pagado_previa: 212.6,
      },
    });

    // `monto_acumulado` / `total_acumulado` los deriva el servidor a la
    // tarifa de B: el cliente NO puede inyectarlos.
    expect(payload.liquidacion_especifica.continuidad).not.toHaveProperty(
      "monto_acumulado",
    );
    expect(payload.liquidacion_especifica.continuidad).not.toHaveProperty(
      "total_acumulado",
    );
    expect(payload.liquidacion_especifica.continuidad).not.toHaveProperty(
      "total_credito",
    );
  });

  it("el bloque de continuidad no viaja en el payload legacy", () => {
    const payload = buildCrearInspeccionObraPayload(
      {
        ...visitasFormData,
        continuidad: {
          subtotal_credito: 100,
        },
      },
      true,
    );

    expect(payload.liquidacion_especifica).not.toHaveProperty("continuidad");
  });
});

describe("schema del form de IO con continuidad", () => {
  it("acepta un form sin continuidad", () => {
    const result = visitasFormSchema.safeParse(visitasFormData);
    expect(result.success).toBe(true);
  });

  it("acepta un form con continuidad y solo el bruto declarado", () => {
    const result = visitasFormSchema.safeParse({
      ...visitasFormData,
      continuidad: {
        liquidacion_previa_id: "previa-1",
        total_pagado_previa: 515.5,
      },
    });

    expect(result.success).toBe(true);
  });

  it("acepta un form con el bruto declarado y el neto legacy", () => {
    const result = visitasFormSchema.safeParse({
      ...visitasFormData,
      continuidad: {
        liquidacion_previa_id: "previa-1",
        total_pagado_previa: 515.5,
        subtotal_credito: 437,
      },
    });

    expect(result.success).toBe(true);
  });

  it("rechaza un crédito negativo", () => {
    const result = visitasFormSchema.safeParse({
      ...visitasFormData,
      continuidad: {
        liquidacion_previa_id: "previa-1",
        subtotal_credito: -1,
      },
    });

    expect(result.success).toBe(false);
  });

  it("rechaza un bruto declarado negativo", () => {
    const result = visitasFormSchema.safeParse({
      ...visitasFormData,
      continuidad: {
        liquidacion_previa_id: "previa-1",
        total_pagado_previa: -1,
      },
    });

    expect(result.success).toBe(false);
  });

  it("rechaza un bruto declarado por encima del máximo del backend", () => {
    const result = visitasFormSchema.safeParse({
      ...visitasFormData,
      continuidad: {
        liquidacion_previa_id: "previa-1",
        total_pagado_previa: 99999999999.99,
      },
    });

    expect(result.success).toBe(false);
  });

  it("admite saldo sin una liquidación previa", () => {
    const result = visitasFormSchema.safeParse({
      ...visitasFormData,
      continuidad: {
        subtotal_credito: 100,
      },
    });

    expect(result.success).toBe(true);
  });

  it("el límite de crédito del cliente ya no existe en el schema", () => {
    // El invariante IV-5 del servidor (el crédito no puede superar el valor
    // completo del trabajo) es la única barrera: el cliente no la replica.
    const result = continuidadVisitasFormSchema.safeParse({
      subtotal_credito: 501,
      valor_maximo_credito: 500,
    });

    expect(result.success).toBe(true);
  });
});

describe("defaults de continuidad derivados de la previa", () => {
  const previa = {
    liquidacion_general: {
      id: "io-previa-1",
      expediente: "EXP-PREVIA-1",
      sub_total: 2575,
      total: 3038.5,
      comprobantes: [
        { id: "comp-1", monto: 3038.5, activo: true },
        { id: "comp-2", monto: 100, activo: false },
      ],
    },
    liquidacion_especifica: { id: "esp-1", numero: 1 },
    liquidacion_tipo: {
      id: "lcv-1",
      cantidad_visitas: 10,
      categoria: "INSPECCION",
      registros_pago: [
        { id: "rp-1", inspecciones_pagadas: 2, periodo: 2026, mes: 1 },
      ],
    },
  } as unknown as LiquidacionInspeccionObraListItem;

  it("referencia la previa y propone su bruto cobrado como dato declarado", () => {
    const defaults = deriveContinuidadDefaults(previa);

    expect(defaults.liquidacion_previa_id).toBe("io-previa-1");
    // El bruto es el Σ de los comprobantes ACTIVOS (no el subtotal neto).
    expect(defaults.total_pagado_previa).toBe(3038.5);
    // El neto NO se propone: lo deriva el servidor del bruto.
    expect(defaults.subtotal_credito).toBeUndefined();
  });
});
