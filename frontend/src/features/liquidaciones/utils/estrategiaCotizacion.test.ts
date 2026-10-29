/**
 * Rehidratación y helpers de la estrategia de cotización PO (Edificaciones).
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la ejecución de
 * la suite queda reservada para el Módulo 8 de la verificación final.
 */
import { describe, expect, it } from "vitest";
import {
  ESTRATEGIA_HABILITADAS,
  ESTRATEGIA_NORMAL,
  ESTRATEGIA_TOTAL,
} from "../schemas/liquidacion-po-estrategia.schema";
import {
  campoProhibidoPorEstrategia,
  ESTRATEGIA_POR_DEFECTO,
  estrategiaUsaTotalExplicito,
  estrategiaUsaValorDeclarado,
  hidratarEstrategiaDesdeItem,
  leerEstrategiaFormData,
  resolverEstrategiaPersistida,
} from "./estrategiaCotizacion";

describe("resolverEstrategiaPersistida — rehidratación legacy", () => {
  it("una liquidación sin estrategia rehidrata como NORMAL_SELECCIONADAS", () => {
    expect(resolverEstrategiaPersistida(null)).toBe(ESTRATEGIA_NORMAL);
    expect(resolverEstrategiaPersistida(undefined)).toBe(ESTRATEGIA_NORMAL);
    expect(
      resolverEstrategiaPersistida({ estrategia_cotizacion: null }),
    ).toBe(ESTRATEGIA_NORMAL);
  });

  it("una estrategia desconocida rehidrata como NORMAL_SELECCIONADAS", () => {
    expect(
      resolverEstrategiaPersistida({ estrategia_cotizacion: "MODO_CUSTOM" }),
    ).toBe(ESTRATEGIA_NORMAL);
  });

  it("respeta la estrategia persistida cuando es válida", () => {
    expect(
      resolverEstrategiaPersistida({
        estrategia_cotizacion: ESTRATEGIA_HABILITADAS,
      }),
    ).toBe(ESTRATEGIA_HABILITADAS);
    expect(
      resolverEstrategiaPersistida({
        estrategia_cotizacion: ESTRATEGIA_TOTAL,
      }),
    ).toBe(ESTRATEGIA_TOTAL);
  });

  it("el valor por defecto es NORMAL_SELECCIONADAS", () => {
    expect(ESTRATEGIA_POR_DEFECTO).toBe(ESTRATEGIA_NORMAL);
  });
});

describe("hidratarEstrategiaDesdeItem — sin pérdida de datos", () => {
  it("una Edificaciones legacy rehidrata con su valor declarado", () => {
    const resultado = hidratarEstrategiaDesdeItem({
      liquidacion_tipo: {
        estrategia_cotizacion: null,
        valor_declarado: 1000000,
      },
    });
    expect(resultado.estrategia_cotizacion).toBe(ESTRATEGIA_NORMAL);
    expect(resultado.valor_declarado).toBe(1000000);
    expect(resultado.total_explicito).toBeUndefined();
  });

  it("una TOTAL_EXPLICITO rehidrata el valor informativo y su total", () => {
    const resultado = hidratarEstrategiaDesdeItem({
      liquidacion_tipo: {
        estrategia_cotizacion: ESTRATEGIA_TOTAL,
        valor_declarado: 1000000,
        total_explicito: 177,
      },
    });
    expect(resultado.estrategia_cotizacion).toBe(ESTRATEGIA_TOTAL);
    expect(resultado.total_explicito).toBe(177);
    expect(resultado.valor_declarado).toBe(1000000);
  });

  it("acepta los decimales serializados como string por el backend", () => {
    const resultado = hidratarEstrategiaDesdeItem({
      liquidacion_tipo: {
        estrategia_cotizacion: ESTRATEGIA_NORMAL,
        valor_declarado: "1000000.50",
      },
    });
    expect(resultado.valor_declarado).toBe(1000000.5);
  });
});

describe("datos exigidos por estrategia", () => {
  it("TOTAL_EXPLICITO conserva el valor declarado y usa el total final", () => {
    expect(estrategiaUsaTotalExplicito(ESTRATEGIA_TOTAL)).toBe(true);
    expect(estrategiaUsaValorDeclarado(ESTRATEGIA_TOTAL)).toBe(true);
    expect(campoProhibidoPorEstrategia(ESTRATEGIA_TOTAL)).toBeNull();
  });

  it("las otras dos estrategias usan el valor declarado", () => {
    expect(estrategiaUsaValorDeclarado(ESTRATEGIA_NORMAL)).toBe(true);
    expect(estrategiaUsaValorDeclarado(ESTRATEGIA_HABILITADAS)).toBe(true);
    expect(campoProhibidoPorEstrategia(ESTRATEGIA_NORMAL)).toBe(
      "total_explicito",
    );
    expect(campoProhibidoPorEstrategia(ESTRATEGIA_HABILITADAS)).toBe(
      "total_explicito",
    );
  });
});

describe("leerEstrategiaFormData — motores sin estrategia", () => {
  it("no inventa estrategia en un form data de Taludes o Impacto Vial", () => {
    expect(
      leerEstrategiaFormData({
        valor_declarado: 1000,
        tarifa_unica_id: "tarifa-1",
      }),
    ).toEqual({ valor_declarado: 1000 });
  });

  it("lee la estrategia y los dos datos cuando existen", () => {
    expect(
      leerEstrategiaFormData({
        estrategia_cotizacion: ESTRATEGIA_TOTAL,
        valor_declarado: undefined,
        total_explicito: 177,
      }),
    ).toEqual({
      estrategia_cotizacion: ESTRATEGIA_TOTAL,
      total_explicito: 177,
    });
  });

  it("descarta una estrategia desconocida", () => {
    expect(
      leerEstrategiaFormData({ estrategia_cotizacion: "MODO_CUSTOM" }),
    ).toEqual({});
  });

  it("tolera datos que no son objetos", () => {
    expect(leerEstrategiaFormData(null)).toEqual({});
    expect(leerEstrategiaFormData(undefined)).toEqual({});
  });
});
