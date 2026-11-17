/**
 * Continuidad de visitas de IO en EDICIÓN — payload, schema y rehidratación.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la ejecución de
 * la suite queda reservada para la Fase 3 (verificación).
 *
 * Contrato cubierto (io-continuidad-visitas-ui-edit, Fase 2):
 *  · La rehidratación del bloque de continuidad NO lleva `modo`: mientras el
 *    usuario no toque la sección, el PATCH es idéntico al vigente.
 *  · Editar el bloque de continuidad envía `modo: "mantener"` (o `"activar"`
 *    si la IO no tenía continuidad) con el bloque COMPLETO.
 *  · Desactivar envía `modo: "desactivar"` y solo el discriminador.
 *  · El cliente NUNCA envía `monto_acumulado` / `total_acumulado` /
 *    `total_credito`: los deriva el servidor con el IGV histórico.
 */
import { describe, expect, it } from "vitest";
import { deriveContinuidadEditDefaults } from "../components/forms/inspeccion-obra/ContinuidadVisitasPanel";
import { buildCrearInspeccionObraPayload } from "../hooks/useCrearInspeccionObra";
import type { ContinuidadVisitasOut } from "./liquidacion-visitas.schema";
import {
  buildVisitasEditPayload,
  buildVisitasTipoPayload,
} from "./liquidacion-visitas-edit.schema";
import type { VisitasFormData } from "./liquidacion-visitas-form.schema";
import { visitasFormSchema } from "./liquidacion-visitas-form.schema";

const baseFormData = {
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

const continuidadPersistida: ContinuidadVisitasOut = {
  id: "cont-1",
  liquidacion_previa_id: "io-previa-1",
  monto_acumulado: 2500,
  total_acumulado: 2950,
  subtotal_credito: 500,
  total_credito: 590,
  visitas_previas_totales: 10,
  visitas_previas_pendientes: 2,
  categoria_previa: "2",
  observacion: "Observación persistida",
};

describe("rehidratación de la continuidad en edición", () => {
  it("rehidrata el bloque persistido sin `modo` (operación no solicitada)", () => {
    const rehidratado = deriveContinuidadEditDefaults(continuidadPersistida);

    expect(rehidratado.liquidacion_previa_id).toBe("io-previa-1");
    expect(rehidratado.visitas_previas_totales).toBe(10);
    expect(rehidratado.visitas_previas_pendientes).toBe(2);
    expect(rehidratado.categoria_previa).toBe("2");
    expect(rehidratado.subtotal_credito).toBe(500);
    expect(rehidratado.observacion).toBe("Observación persistida");
    // El bruto vigente del crédito (derivado por el servidor) se propone como
    // bruto DECLARADO: al re-declararlo, el servidor lo vuelve a derivar con
    // el MISMO IGV histórico.
    expect(rehidratado.total_pagado_previa).toBe(590);
    // El `modo` es la señal de que el usuario interactuó con la sección: un
    // bloque rehidratado NO debe llevarlo.
    expect(rehidratado.modo).toBeUndefined();
  });

  it("rehidrata un registro manual (previa fuera de CAM) sin total de visitas", () => {
    const rehidratado = deriveContinuidadEditDefaults({
      ...continuidadPersistida,
      liquidacion_previa_id: null,
      visitas_previas_totales: null,
      categoria_previa: null,
      observacion: null,
    });

    expect(rehidratado.liquidacion_previa_id).toBeUndefined();
    expect(rehidratado.visitas_previas_totales).toBeUndefined();
    expect(rehidratado.categoria_previa).toBeUndefined();
    expect(rehidratado.observacion).toBe("");
    expect(rehidratado.modo).toBeUndefined();
  });

  it("el bloque rehidratado es válido para el schema del formulario", () => {
    const result = visitasFormSchema.safeParse({
      ...baseFormData,
      continuidad: deriveContinuidadEditDefaults({
        ...continuidadPersistida,
        liquidacion_previa_id: null,
        visitas_previas_totales: null,
        subtotal_credito: 0,
        visitas_previas_pendientes: 0,
      }),
    });

    expect(result.success).toBe(true);
  });
});

describe("payload de edición de IO con continuidad", () => {
  it("omite el bloque de continuidad cuando la IO no tiene continuidad", () => {
    const payload = buildVisitasEditPayload(baseFormData);

    expect(payload.liquidacion_tipo).not.toHaveProperty("continuidad");
    expect(Object.hasOwn(payload.liquidacion_tipo ?? {}, "continuidad")).toBe(
      false,
    );
  });

  it("omite el bloque de continuidad cuando el usuario no tocó la sección", () => {
    const payload = buildVisitasEditPayload({
      ...baseFormData,
      continuidad: deriveContinuidadEditDefaults(continuidadPersistida),
    });

    // Rehidratado SIN `modo`: el PATCH es idéntico al vigente (el servidor
    // conserva el crédito congelado).
    expect(payload.liquidacion_tipo).not.toHaveProperty("continuidad");
  });

  it("envía `mantener` con el BRUTO declarado cuando el usuario edita el crédito", () => {
    const payload = buildVisitasEditPayload({
      ...baseFormData,
      continuidad: {
        ...deriveContinuidadEditDefaults(continuidadPersistida),
        modo: "mantener",
        total_pagado_previa: 750,
      },
    });

    // El BRUTO MANDA: el neto no viaja (nunca las dos cifras del mismo dinero).
    expect(payload.liquidacion_tipo?.continuidad).toEqual({
      modo: "mantener",
      liquidacion_previa_id: "io-previa-1",
      total_pagado_previa: 750,
    });
  });

  it("envía `activar` con el bruto declarado cuando la IO no tenía continuidad", () => {
    const payload = buildVisitasEditPayload({
      ...baseFormData,
      continuidad: {
        modo: "activar",
        visitas_previas_pendientes: 3,
        visitas_previas_totales: 10,
        total_pagado_previa: 354,
      },
    });

    expect(payload.liquidacion_tipo?.continuidad).toEqual({
      modo: "activar",
      total_pagado_previa: 354,
    });
  });

  it("mantiene el camino legacy: sin bruto declarado viaja el neto", () => {
    const payload = buildVisitasEditPayload({
      ...baseFormData,
      continuidad: {
        modo: "mantener",
        liquidacion_previa_id: "io-previa-1",
        subtotal_credito: 750,
      },
    });

    expect(payload.liquidacion_tipo?.continuidad).toEqual({
      modo: "mantener",
      liquidacion_previa_id: "io-previa-1",
      subtotal_credito: 750,
    });
  });

  it("envía solo el discriminador cuando se desactiva la continuidad", () => {
    const payload = buildVisitasEditPayload({
      ...baseFormData,
      continuidad: {
        ...deriveContinuidadEditDefaults(continuidadPersistida),
        modo: "desactivar",
      },
    });

    expect(payload.liquidacion_tipo?.continuidad).toEqual({
      modo: "desactivar",
    });
  });

  it("nunca envía los importes que deriva el servidor", () => {
    const payload = buildVisitasEditPayload({
      ...baseFormData,
      continuidad: {
        ...deriveContinuidadEditDefaults(continuidadPersistida),
        modo: "mantener",
      },
    });

    const bloque = payload.liquidacion_tipo?.continuidad ?? {};
    expect(bloque).not.toHaveProperty("monto_acumulado");
    expect(bloque).not.toHaveProperty("total_acumulado");
    expect(bloque).not.toHaveProperty("total_credito");
    // El neto tampoco viaja cuando el bruto está declarado.
    expect(bloque).not.toHaveProperty("subtotal_credito");
  });

  it("mantiene intacto el payload de una IO normal (sin continuidad)", () => {
    const payload = buildVisitasEditPayload(baseFormData);

    expect(payload.liquidacion_tipo).toEqual({
      datos: { cantidad_visitas: 3 },
      tarifa: { tarifa_visitas_id: "tarifa-2" },
      inspector_operacion_id: "operacion-1",
    });
  });

  it("el builder de tipo no inventa el bloque de continuidad sin `modo`", () => {
    const tipoFields = buildVisitasTipoPayload({
      ...baseFormData,
      continuidad: {
        ...deriveContinuidadEditDefaults(continuidadPersistida),
      },
    });

    expect(tipoFields).not.toHaveProperty("continuidad");
  });
});

describe("schema del form de IO con el discriminador de modo", () => {
  it.each(["activar", "mantener", "desactivar"])(
    "acepta el modo %s",
    (modo) => {
      const result = visitasFormSchema.safeParse({
        ...baseFormData,
        continuidad: {
          modo,
          liquidacion_previa_id: "io-previa-1",
          visitas_previas_totales: 10,
          visitas_previas_pendientes: 2,
          subtotal_credito: 500,
        },
      });

      expect(result.success).toBe(true);
    },
  );

  it("rechaza un modo desconocido", () => {
    const result = visitasFormSchema.safeParse({
      ...baseFormData,
      continuidad: {
        modo: "apagar",
        visitas_previas_pendientes: 2,
        subtotal_credito: 500,
      },
    });

    expect(result.success).toBe(false);
  });
});

describe("payload de creación de IO — el modo es del PATCH, no del alta", () => {
  it("no viaja el discriminador de modo en el alta", () => {
    const payload = buildCrearInspeccionObraPayload({
      ...baseFormData,
      continuidad: {
        modo: "mantener",
        liquidacion_previa_id: "io-previa-1",
        visitas_previas_totales: 10,
        visitas_previas_pendientes: 2,
        subtotal_credito: 500,
        observacion: "Observación",
      },
    });

    expect(payload.liquidacion_especifica.continuidad).not.toHaveProperty(
      "modo",
    );
    expect(payload.liquidacion_especifica.continuidad).toEqual({
      liquidacion_previa_id: "io-previa-1",
      subtotal_credito: 500,
    });
  });
});
