/**
 * Espejo Zod del contrato de cotización del motor IO (Inspección de Obra).
 *
 * Contrato cubierto (io-continuity-server-quote, D-1 / T-7):
 *  · La union discriminada `modo_cotizacion` acepta NORMAL y CONTINUAR y
 *    RECHAZA los payloads mixtos (continuidad en NORMAL, CONTINUAR sin el
 *    bruto declarado, modo desconocido, claves extra).
 *  · El discriminador ausente se normaliza a NORMAL (el payload vigente queda
 *    byte-compatible, igual que en el backend).
 *  · Los builders materializan el discriminador y, en CONTINUAR, el bloque
 *    `continuidad` con el BRUTO declarado.
 *  · El espejo de la salida conserva `modo_cotizacion` y `continuidad`: Zod no
 *    elimina las claves nuevas (riesgo R9).
 */
import { describe, expect, it } from "vitest";
import {
  construirCotizacionVisitasEdicionPayload,
  construirCotizacionVisitasPayload,
  cotizacionVisitasContinuidadOutSchema,
  cotizacionVisitasOutputSchema,
  cotizarVisitasEdicionSchema,
  cotizarVisitasSchema,
  MODO_COTIZACION_IO_CONTINUAR,
  MODO_COTIZACION_IO_NORMAL,
  normalizarPayloadCotizacionVisitas,
  parsePayloadCotizacionVisitas,
} from "./liquidacion-io-cotizacion.schema";

const DATOS = { cantidad_visitas: 3 };
const TARIFA = { tarifa_visitas_id: "3f1c0000-0000-0000-0000-000000000000" };

describe("cotización de IO — union discriminada", () => {
  it("acepta la variante NORMAL con el discriminador explícito", () => {
    const resultado = cotizarVisitasSchema.safeParse({
      modo_cotizacion: MODO_COTIZACION_IO_NORMAL,
      datos: DATOS,
      tarifa: TARIFA,
    });

    expect(resultado.success).toBe(true);
  });

  it("acepta la variante CONTINUAR con el bruto declarado", () => {
    const resultado = cotizarVisitasSchema.safeParse({
      modo_cotizacion: MODO_COTIZACION_IO_CONTINUAR,
      datos: DATOS,
      tarifa: TARIFA,
      continuidad: { total_pagado_previa: 212.6 },
    });

    expect(resultado.success).toBe(true);
    if (resultado.success && "continuidad" in resultado.data) {
      expect(resultado.data.continuidad?.total_pagado_previa).toBe(212.6);
    }
  });

  it("rechaza NORMAL con el bloque de continuidad (payload mixto)", () => {
    const resultado = cotizarVisitasSchema.safeParse({
      modo_cotizacion: MODO_COTIZACION_IO_NORMAL,
      datos: DATOS,
      tarifa: TARIFA,
      continuidad: { total_pagado_previa: 212.6 },
    });

    expect(resultado.success).toBe(false);
  });

  it("rechaza CONTINUAR sin el bruto declarado", () => {
    const resultado = cotizarVisitasSchema.safeParse({
      modo_cotizacion: MODO_COTIZACION_IO_CONTINUAR,
      datos: DATOS,
      tarifa: TARIFA,
    });

    expect(resultado.success).toBe(false);
  });

  it("rechaza un modo desconocido", () => {
    const resultado = cotizarVisitasSchema.safeParse({
      modo_cotizacion: "OTRO",
      datos: DATOS,
      tarifa: TARIFA,
    });

    expect(resultado.success).toBe(false);
  });

  it("rechaza un bruto declarado no positivo", () => {
    for (const bruto of [0, -5]) {
      const resultado = cotizarVisitasSchema.safeParse({
        modo_cotizacion: MODO_COTIZACION_IO_CONTINUAR,
        datos: DATOS,
        tarifa: TARIFA,
        continuidad: { total_pagado_previa: bruto },
      });

      expect(resultado.success).toBe(false);
    }
  });

  it("rechaza un bruto declarado por encima del máximo del backend", () => {
    const resultado = cotizarVisitasSchema.safeParse({
      modo_cotizacion: MODO_COTIZACION_IO_CONTINUAR,
      datos: DATOS,
      tarifa: TARIFA,
      continuidad: { total_pagado_previa: 99999999999.99 },
    });

    expect(resultado.success).toBe(false);
  });

  it("rechaza claves extra en la variante (strict ≡ extra=forbid)", () => {
    const resultado = cotizarVisitasSchema.safeParse({
      modo_cotizacion: MODO_COTIZACION_IO_NORMAL,
      datos: DATOS,
      tarifa: TARIFA,
      liquidacion_previa_id: "no-permitido",
    });

    expect(resultado.success).toBe(false);
  });
});

describe("cotización de IO — normalización del discriminador", () => {
  it("materializa NORMAL cuando el payload no trae discriminador", () => {
    const normalizado = normalizarPayloadCotizacionVisitas({
      datos: DATOS,
      tarifa: TARIFA,
    });

    expect(normalizado.modo_cotizacion).toBe(MODO_COTIZACION_IO_NORMAL);
  });

  it("conserva un discriminador ya materializado", () => {
    const normalizado = normalizarPayloadCotizacionVisitas({
      modo_cotizacion: MODO_COTIZACION_IO_CONTINUAR,
      datos: DATOS,
      tarifa: TARIFA,
    });

    expect(normalizado.modo_cotizacion).toBe(MODO_COTIZACION_IO_CONTINUAR);
  });

  it("parsea el payload vigente (sin discriminador) como NORMAL", () => {
    const payload = parsePayloadCotizacionVisitas({
      datos: DATOS,
      tarifa: TARIFA,
    });

    expect(payload.modo_cotizacion).toBe(MODO_COTIZACION_IO_NORMAL);
    expect(payload).not.toHaveProperty("continuidad");
  });
});

describe("cotización de IO — builders", () => {
  it("el builder de ALTA materializa el discriminador NORMAL", () => {
    const body = construirCotizacionVisitasPayload({
      modo: MODO_COTIZACION_IO_NORMAL,
      cantidad_visitas: 3,
      tarifa_visitas_id: TARIFA.tarifa_visitas_id,
    });

    expect(body).toEqual({
      liquidacion_especifica: {
        modo_cotizacion: MODO_COTIZACION_IO_NORMAL,
        datos: DATOS,
        tarifa: TARIFA,
      },
    });
  });

  it("el builder de ALTA incluye el bruto declarado en CONTINUAR", () => {
    const body = construirCotizacionVisitasPayload({
      modo: MODO_COTIZACION_IO_CONTINUAR,
      cantidad_visitas: 3,
      tarifa_visitas_id: TARIFA.tarifa_visitas_id,
      total_pagado_previa: 212.6,
    });

    expect(body.liquidacion_especifica).toEqual({
      modo_cotizacion: MODO_COTIZACION_IO_CONTINUAR,
      datos: DATOS,
      tarifa: TARIFA,
      continuidad: { total_pagado_previa: 212.6 },
    });
  });

  it("el builder de EDICIÓN usa el wrapper liquidacion_tipo", () => {
    const body = construirCotizacionVisitasEdicionPayload({
      modo: MODO_COTIZACION_IO_CONTINUAR,
      cantidad_visitas: 3,
      tarifa_visitas_id: TARIFA.tarifa_visitas_id,
      total_pagado_previa: 212.6,
    });

    expect(Object.keys(body)).toEqual(["liquidacion_tipo"]);
    expect(body.liquidacion_tipo).toEqual({
      modo_cotizacion: MODO_COTIZACION_IO_CONTINUAR,
      datos: DATOS,
      tarifa: TARIFA,
      continuidad: { total_pagado_previa: 212.6 },
    });
  });

  it("sin bruto declarado el builder NO inventa la variante CONTINUAR", () => {
    const body = construirCotizacionVisitasPayload({
      modo: MODO_COTIZACION_IO_CONTINUAR,
      cantidad_visitas: 3,
      tarifa_visitas_id: TARIFA.tarifa_visitas_id,
    });

    // El backend rechaza CONTINUAR sin `total_pagado_previa` (422): el cliente
    // degrada a NORMAL en vez de enviar un payload inválido.
    expect(body.liquidacion_especifica.modo_cotizacion).toBe(
      MODO_COTIZACION_IO_NORMAL,
    );
    expect(body.liquidacion_especifica).not.toHaveProperty("continuidad");
  });

  it("un modo desconocido degrada a NORMAL", () => {
    const body = construirCotizacionVisitasPayload({
      modo: "OTRO" as never,
      cantidad_visitas: 3,
      tarifa_visitas_id: TARIFA.tarifa_visitas_id,
    });

    expect(body.liquidacion_especifica.modo_cotizacion).toBe(
      MODO_COTIZACION_IO_NORMAL,
    );
  });

  it("el builder de EDICIÓN produce un payload que valida la union", () => {
    const body = construirCotizacionVisitasEdicionPayload({
      modo: MODO_COTIZACION_IO_CONTINUAR,
      cantidad_visitas: 3,
      tarifa_visitas_id: TARIFA.tarifa_visitas_id,
      total_pagado_previa: 212.6,
    });

    expect(
      cotizarVisitasEdicionSchema.safeParse(body.liquidacion_tipo).success,
    ).toBe(true);
  });
});

describe("cotización de IO — espejo de la salida", () => {
  const RESPUESTA = {
    datos: {
      entrada: {
        datos: { cantidad_visitas: 3, categoria: "2" },
        tarifa: { tarifa_visitas_id: TARIFA.tarifa_visitas_id },
      },
      tarifa: { id: TARIFA.tarifa_visitas_id, costo_por_visita: 107 },
      variables_financieras: {
        igv: { valor: 0.18 },
        uit: { valor: 5350 },
      },
    },
    calculo: { monto_bruto: 321, subtotal: 321, total: 378.78 },
    modo_cotizacion: "CONTINUAR",
    continuidad: {
      total_pagado_previa: 212.6,
      valor_completo_neto: 321,
      valor_completo_bruto: 378.78,
      credito_neto: 180.17,
      credito_bruto: 212.6,
      diferencia_neto: 140.83,
      diferencia_bruto: 166.18,
      igv_porcentaje: 0.18,
    },
  };

  it("conserva el bloque `continuidad` (Zod no lo elimina)", () => {
    const resultado = cotizacionVisitasOutputSchema.parse(RESPUESTA);

    expect(resultado.modo_cotizacion).toBe(MODO_COTIZACION_IO_CONTINUAR);
    expect(resultado.continuidad?.credito_neto).toBe(180.17);
    expect(resultado.continuidad?.diferencia_bruto).toBe(166.18);
  });

  it("acepta la respuesta NORMAL con `continuidad` en null", () => {
    const resultado = cotizacionVisitasOutputSchema.parse({
      ...RESPUESTA,
      modo_cotizacion: "NORMAL",
      continuidad: null,
    });

    expect(resultado.continuidad).toBeNull();
    expect(resultado.calculo.total).toBe(378.78);
  });

  it("el bloque de continuidad se puede leer sin el espejo completo", () => {
    const bloque = cotizacionVisitasContinuidadOutSchema.parse(
      RESPUESTA.continuidad,
    );

    expect(bloque.total_pagado_previa).toBe(212.6);
    expect(bloque.igv_porcentaje).toBe(0.18);
  });
});
