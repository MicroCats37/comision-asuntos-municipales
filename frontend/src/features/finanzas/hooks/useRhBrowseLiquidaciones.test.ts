/**
 * useRhBrowseLiquidaciones — contrato de filtros del listado de browse.
 *
 * Contrato de la capability `liquidaciones-browse-listado` (corregido):
 * - el browse usa el MISMO contrato de filtros que las listas de Liquidaciones
 *   (`LiquidacionFiltros`), NO el de las candidatas RH;
 * - los filtros del wizard RH sólo SIEMBLAN los compatibles: no limitan la
 *   búsqueda más allá de los filtros de Liquidaciones activos;
 * - NO hay filtro municipal implícito: `entidad_id` sólo viaja si el usuario
 *   lo elige en el panel de filtros;
 * - los filtros que el endpoint activo NO soporta se OMITEN de forma
 *   explícita: nunca se envían vacíos (un filtro vacío ampliaría el
 *   resultado).
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la verificación
 * corre en la fase final de SDD (tarea 5.4).
 */
import { describe, expect, it } from "vitest";

import {
  buildRhBrowseParams,
  buildRhBrowseSemillaFiltros,
  fusionarFiltrosLiquidacion,
} from "./useRhBrowseLiquidaciones";

/** Los 12 filtros del contrato `LiquidacionFiltros`. */
const FILTROS_LIQUIDACION_COMPLETOS = {
  entidad_id: "mun-1",
  distrito_id: "dis-1",
  propietario: "ACME S.A.",
  razon_social: "ACME S.A.",
  direccion: "Av. Siempre Viva 742",
  documento: "20123456789",
  fecha_desde: "2026-01-01",
  fecha_hasta: "2026-12-31",
  numero: 88,
  expediente: "EXP-1",
  comprobante_serie: "F001",
  comprobante_numero: "55",
};

describe("buildRhBrowseSemillaFiltros — filtros del wizard → contrato Liquidaciones", () => {
  it("siembra sólo los campos compatibles del wizard", () => {
    const semilla = buildRhBrowseSemillaFiltros({
      filtros: {
        expediente: "EXP-001",
        numero: "88",
        propietario: "ACME S.A.",
        direccion: "Av. Siempre Viva 742",
        documento: "20123456789",
        comprobante_serie: "F001",
        comprobante_numero: "55",
      },
      fechaDesde: "2026-01-01",
      fechaHasta: "2026-12-31",
    });

    expect(semilla).toEqual({
      expediente: "EXP-001",
      numero: 88,
      propietario: "ACME S.A.",
      direccion: "Av. Siempre Viva 742",
      documento: "20123456789",
      comprobante_serie: "F001",
      comprobante_numero: "55",
      fecha_desde: "2026-01-01",
      fecha_hasta: "2026-12-31",
    });
  });

  it("NO siembra ningún filtro municipal (no hay filtro implícito)", () => {
    const semilla = buildRhBrowseSemillaFiltros({
      filtros: { expediente: "EXP-001" },
    });

    expect(semilla.entidad_id).toBeUndefined();
    expect(semilla.distrito_id).toBeUndefined();
  });

  it("ignora un número que no es entero (el listado exige match exacto)", () => {
    expect(
      buildRhBrowseSemillaFiltros({ filtros: { numero: "ABC" } }).numero,
    ).toBeUndefined();
    expect(
      buildRhBrowseSemillaFiltros({ filtros: { numero: "88.5" } }).numero,
    ).toBeUndefined();
  });

  it("ignora valores vacíos o sólo espacios", () => {
    expect(
      buildRhBrowseSemillaFiltros({
        filtros: { expediente: "   ", propietario: "" },
        fechaDesde: "",
        fechaHasta: "  ",
      }),
    ).toEqual({});
  });
});

describe("buildRhBrowseParams — listado por tipo", () => {
  it("mapea 1:1 TODOS los filtros del contrato de Liquidaciones", () => {
    const { params, omitidos } = buildRhBrowseParams({
      tipoCodigo: "EDIFICACION",
      filtros: FILTROS_LIQUIDACION_COMPLETOS,
    });

    expect(params).toEqual({
      entidad_id: "mun-1",
      distrito_id: "dis-1",
      propietario: "ACME S.A.",
      razon_social: "ACME S.A.",
      direccion: "Av. Siempre Viva 742",
      documento: "20123456789",
      fecha_desde: "2026-01-01",
      fecha_hasta: "2026-12-31",
      numero: 88,
      expediente: "EXP-1",
      comprobante_serie: "F001",
      comprobante_numero: "55",
    });
    expect(omitidos).toEqual([]);
  });

  it("no envía filtros vacíos", () => {
    const { params, omitidos } = buildRhBrowseParams({
      tipoCodigo: "TALUDES",
      filtros: {
        expediente: "   ",
        propietario: "",
        direccion: undefined,
        entidad_id: "",
      },
    });

    expect(params).toEqual({});
    expect(omitidos).toEqual([]);
  });

  it("omite de forma explícita un número que no es un entero exacto", () => {
    const { params, omitidos } = buildRhBrowseParams({
      tipoCodigo: "TALUDES",
      filtros: { numero: Number.NaN },
    });

    expect(params).not.toHaveProperty("numero");
    expect(omitidos.map((omitido) => omitido.filtro)).toEqual(["numero"]);
  });
});

describe("buildRhBrowseParams — listado cross-tipo (/generales/)", () => {
  it("envía sólo los filtros que el endpoint admite y omite el resto explícitamente", () => {
    const { params, omitidos } = buildRhBrowseParams({
      tipoCodigo: null,
      filtros: FILTROS_LIQUIDACION_COMPLETOS,
    });

    expect(params).toEqual({
      entidad_id: "mun-1",
      distrito_id: "dis-1",
      propietario: "ACME S.A.",
      razon_social: "ACME S.A.",
      direccion: "Av. Siempre Viva 742",
      documento: "20123456789",
      expediente: "EXP-1",
    });

    // Los no soportados NO viajan (ni vacíos: un filtro vacío ampliaría).
    expect(params).not.toHaveProperty("numero");
    expect(params).not.toHaveProperty("comprobante_serie");
    expect(params).not.toHaveProperty("comprobante_numero");
    expect(params).not.toHaveProperty("fecha_desde");
    expect(params).not.toHaveProperty("fecha_hasta");

    // Y la omisión es EXPLÍCITA (queda registrada para avisar al usuario).
    expect(omitidos.map((omitido) => omitido.filtro).sort()).toEqual([
      "comprobante_numero",
      "comprobante_serie",
      "fecha_desde",
      "fecha_hasta",
      "numero",
    ]);
  });

  it("omite el número no entero sin duplicar el aviso de omisión", () => {
    const { params, omitidos } = buildRhBrowseParams({
      tipoCodigo: null,
      filtros: { numero: Number.NaN },
    });

    expect(params).not.toHaveProperty("numero");
    expect(omitidos.filter((omitido) => omitido.filtro === "numero")).toHaveLength(
      1,
    );
  });
});

describe("fusionarFiltrosLiquidacion — panel de Liquidaciones sobre filtros activos", () => {
  it("el panel REEMPLAZA los filtros que edita", () => {
    const fusionado = fusionarFiltrosLiquidacion(
      { propietario: "ACME S.A.",razon_social: "ACME S.A." },
      { razon_social: "NUEVA S.A." },
    );

    // `propietario` lo editaba el panel y el usuario lo borró → desaparece.
    expect(fusionado.propietario).toBeUndefined();
    expect(fusionado.razon_social).toBe("NUEVA S.A.");
  });

  it("el panel CONSERVA los filtros que no expone (p. ej. el expediente sembrado)", () => {
    const fusionado = fusionarFiltrosLiquidacion(
      { expediente: "EXP-001", propietario: "ACME S.A." },
      { propietario: "ACME S.A." },
    );

    expect(fusionado.expediente).toBe("EXP-001");
    expect(fusionado.propietario).toBe("ACME S.A.");
  });
});
