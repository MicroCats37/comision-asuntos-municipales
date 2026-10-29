import { describe, expect, it } from "vitest";
import { buildLiquidacionPdfDom } from "./LiquidacionPdfPreview";
import {
  buildCommonFieldRows,
  buildExtraFieldRows,
} from "./liquidacionPdfHelpers";
import type { PdfLiquidacionItem, PdfTipoSlug } from "./pdfTypes";

function baseItem(
  overrides: Partial<PdfLiquidacionItem> = {},
): PdfLiquidacionItem {
  return {
    liquidacion_general: {
      id: "lg-1",
      municipalidad: { codigo: "L50-1", nombre: "Municipalidad de Miraflores" },
      proyecto: {
        nombre_propietario: "Propietario Test SAC",
        direccion: "Av. Test 123, Lima",
        entidad: {
          tipo_documento: "RUC",
          numero_documento: "20123456789",
          razon_social: "Propietario Test SAC",
        },
      },
      denominacion_de_proyecto: "Habilitación Urbana",
      sub_total: 1000,
      total: 1180,
      uit: { valor: 5150 },
    },
    liquidacion_especifica: { numero: 1534 },
    liquidacion_tipo: {},
    ...overrides,
  };
}

describe("buildCommonFieldRows", () => {
  it("incluye NOMBRE DEL PROYECTO para los tipos con motor m2", () => {
    const rows = buildCommonFieldRows(baseItem(), "habilitacion-urbana");
    const labels = rows.map(([label]) => label);

    expect(labels).toContain("NOMBRE DEL PROYECTO");
    expect(labels).toContain("RUC");
    expect(labels).toContain("DIRECCION DE LA OBRA");
  });

  it("omite NOMBRE DEL PROYECTO en inspeccion de obra", () => {
    const rows = buildCommonFieldRows(baseItem(), "inspeccion-obra");
    const labels = rows.map(([label]) => label);

    expect(labels).not.toContain("NOMBRE DEL PROYECTO");
    expect(labels).toContain("NOMBRE DEL PROPIETARIO");
    expect(labels).toContain("DPTO. / PROV. / DISTRITO");
  });
});

describe("buildExtraFieldRows", () => {
  it("agrega COSTO POR VISITA en inspeccion de obra (UIT x porcentaje_uit)", () => {
    const item = baseItem();
    item.liquidacion_tipo = { cantidad_visitas: 3, porcentaje_uit: 0.05 };

    const rows = buildExtraFieldRows(item, "inspeccion-obra");
    const costo = rows.find(([label]) => label === "COSTO POR VISITA");

    expect(costo).toBeDefined();
    expect(costo?.[1]).toBe("S/ 257.50");
  });

  it("omite COSTO POR VISITA cuando falta el UIT o el porcentaje", () => {
    const sinPorcentaje = baseItem();
    sinPorcentaje.liquidacion_tipo = { cantidad_visitas: 3 };

    const sinUit = baseItem();
    sinUit.liquidacion_general.uit = undefined;
    sinUit.liquidacion_tipo = { cantidad_visitas: 3, porcentaje_uit: 0.05 };

    for (const item of [sinPorcentaje, sinUit]) {
      const rows = buildExtraFieldRows(item, "inspeccion-obra");
      expect(rows.some(([label]) => label === "COSTO POR VISITA")).toBe(false);
    }
  });

  it("mantiene las filas del motor m2 sin COSTO POR VISITA", () => {
    const item = baseItem();
    item.liquidacion_tipo = { area_m2: 100, costo_por_m2: 0.2 };

    const rows = buildExtraFieldRows(item, "habilitacion-urbana");
    const labels = rows.map(([label]) => label);

    expect(labels).toContain("AREA");
    expect(labels).toContain("COSTO POR M2");
    expect(labels).not.toContain("COSTO POR VISITA");
  });
});

describe("buildExtraFieldRows — contexto interno PO", () => {
  function edificacionItem(
    liquidacion_tipo: PdfLiquidacionItem["liquidacion_tipo"],
  ): PdfLiquidacionItem {
    const item = baseItem();
    item.liquidacion_tipo = liquidacion_tipo;
    return item;
  }

  it("oculta estrategia, H y porcentaje de tarifa en Edificaciones", () => {
    const rows = buildExtraFieldRows(
      edificacionItem({
        valor_declarado: 1_000_000,
        porcentaje_liquidacion: 0.0015,
        estrategia_cotizacion: "TARIFA_HABILITADAS_PARTICIPANTES",
        count_habilitadas: 3,
        porcentaje_tarifa: 0.0005,
      }),
      "edificacion",
    );

    const labels = rows.map(([label]) => label);
    expect(labels).not.toContain("ESTRATEGIA");
    expect(labels).not.toContain("HABILITADAS");
    expect(labels).not.toContain("% TARIFA");
  });

  it("omite H y % de tarifa en NORMAL_SELECCIONADAS (el padre cobra las seleccionadas)", () => {
    const rows = buildExtraFieldRows(
      edificacionItem({
        valor_declarado: 1_000_000,
        porcentaje_liquidacion: 0.001,
        estrategia_cotizacion: "NORMAL_SELECCIONADAS",
        count_habilitadas: 3,
        porcentaje_tarifa: 0.0005,
      }),
      "edificacion",
    );

    const labels = rows.map(([label]) => label);
    expect(labels).not.toContain("ESTRATEGIA");
    expect(labels).not.toContain("HABILITADAS");
    expect(labels).not.toContain("% TARIFA");
    expect(labels).not.toContain("ACUMULACION");
  });

  it("oculta la acumulación de Edificaciones", () => {
    const rows = buildExtraFieldRows(
      edificacionItem({
        estrategia_cotizacion: "TARIFA_HABILITADAS_PARTICIPANTES",
        count_habilitadas: 3,
        porcentaje_tarifa: 0.0005,
        acumulacion: {
          porcentaje_acumulado: 0.001,
          subtotal_acumulado: 1000,
        },
      }),
      "edificacion",
    );

    const acumulacion = rows.find(([label]) => label === "ACUMULACION");
    expect(acumulacion).toBeUndefined();
  });

  it("oculta la acumulación de TOTAL_EXPLICITO", () => {
    const rows = buildExtraFieldRows(
      edificacionItem({
        estrategia_cotizacion: "TOTAL_EXPLICITO",
        count_habilitadas: 3,
        acumulacion: {
          porcentaje_acumulado: null,
          subtotal_acumulado: 100,
        },
      }),
      "edificacion",
    );

    const acumulacion = rows.find(([label]) => label === "ACUMULACION");
    expect(acumulacion).toBeUndefined();
  });

  it("no agrega filas de estrategia a Taludes ni Impacto Vial", () => {
    const item = edificacionItem({
      valor_declarado: 1_000_000,
      porcentaje_liquidacion: 0.001,
      estrategia_cotizacion: "TARIFA_HABILITADAS_PARTICIPANTES",
      count_habilitadas: 3,
      porcentaje_tarifa: 0.0005,
      acumulacion: {
        porcentaje_acumulado: 0.001,
        subtotal_acumulado: 1000,
      },
    });

    for (const tipo of ["taludes", "impacto-vial"] as const) {
      const rows = buildExtraFieldRows(item, tipo);
      const labels = rows.map(([label]) => label);
      expect(labels).toContain("VALOR DE OBRA");
      expect(labels).toContain("PORCENTAJE");
      expect(labels).not.toContain("ESTRATEGIA");
      expect(labels).not.toContain("HABILITADAS");
      expect(labels).not.toContain("% TARIFA");
      expect(labels).not.toContain("ACUMULACION");
    }
  });

  it("no altera las filas del motor de visitas ni del motor m2", () => {
    const item = edificacionItem({
      estrategia_cotizacion: "NORMAL_SELECCIONADAS",
      cantidad_visitas: 3,
      porcentaje_uit: 0.05,
    });

    const visitas = buildExtraFieldRows(item, "inspeccion-obra").map(
      ([label]) => label,
    );
    expect(visitas).toContain("CANTIDAD DE VISITAS");
    expect(visitas).not.toContain("ESTRATEGIA");

    const m2 = buildExtraFieldRows(item, "habilitacion-urbana").map(
      ([label]) => label,
    );
    expect(m2).not.toContain("ESTRATEGIA");
  });
});

describe("buildLiquidacionPdfDom", () => {
  function render(item: PdfLiquidacionItem, tipo: PdfTipoSlug): HTMLElement {
    const host = document.createElement("div");
    document.body.appendChild(host);
    buildLiquidacionPdfDom(host, item, tipo);
    return host;
  }

  function findCtaBox(host: HTMLElement): HTMLElement {
    const box = Array.from(host.querySelectorAll("div")).find((el) =>
      Array.from(el.children).some(
        (child) => child.textContent === "Código de Pago: L50-1",
      ),
    );
    if (!box) throw new Error("No se encontró la caja CTA");
    return box;
  }

  it("muestra el Nro en grande y el código CTA en el slot pequeño", () => {
    const item = baseItem();
    item.liquidacion_general.codigo_cta = "703179999";
    item.liquidacion_especifica = { numero: 1534 };

    const host = render(item, "habilitacion-urbana");
    const ctaBox = findCtaBox(host);
    const lines = Array.from(ctaBox.querySelectorAll("p")).map(
      (p) => p.textContent,
    );

    expect(lines).toEqual([
      "Nro",
      "1534",
      "Código de Pago: L50-1",
      "CTA: 703179999",
    ]);
  });

  it("omite el nombre del proyecto en el bloque base de inspeccion de obra", () => {
    const item = baseItem();
    item.liquidacion_tipo = { cantidad_visitas: 3, porcentaje_uit: 0.05 };

    const io = render(item, "inspeccion-obra");
    expect(io.textContent).not.toContain("NOMBRE DEL PROYECTO");
    expect(io.textContent).toContain("NOMBRE DEL PROPIETARIO");
    expect(io.textContent).toContain("COSTO POR VISITA");

    const hu = render(item, "habilitacion-urbana");
    expect(hu.textContent).toContain("NOMBRE DEL PROYECTO");
  });

  it("fusiona el aviso y la instrucción de adjuntar en una sola caja abajo", () => {
    const host = render(baseItem(), "habilitacion-urbana");

    const merged = Array.from(host.querySelectorAll("div")).find(
      (el) =>
        el.textContent ===
        "⚠ ESTE NO ES UN COMPROBANTE DE PAGO" +
          "ESTE SE DEBERÁ DE ADJUNTAR\nJUNTO AL COMPROBANTE\nDE PAGO",
    );
    expect(merged).toBeDefined();
    expect(merged?.style.backgroundColor).toBe("rgb(254, 243, 199)");

    // El aviso arriba, la instrucción debajo y más grande.
    const lines = Array.from(merged?.querySelectorAll("p") ?? []);
    expect(lines.map((p) => p.textContent)).toEqual([
      "⚠ ESTE NO ES UN COMPROBANTE DE PAGO",
      "ESTE SE DEBERÁ DE ADJUNTAR\nJUNTO AL COMPROBANTE\nDE PAGO",
    ]);
    expect(Number.parseFloat(lines[1].style.fontSize)).toBeGreaterThan(
      Number.parseFloat(lines[0].style.fontSize),
    );

    // La caja fusionada ya no está en el header.
    const header = host.querySelector("[data-pdf-host] > div > div");
    expect(header?.textContent).not.toContain("COMPROBANTE DE PAGO");
  });

  it("mantiene el recibo de Edificaciones sin contexto interno", () => {
    const item = baseItem();
    item.liquidacion_tipo = {
      valor_declarado: 1_000_000,
      porcentaje_liquidacion: 0.0015,
      estrategia_cotizacion: "TARIFA_HABILITADAS_PARTICIPANTES",
      count_habilitadas: 3,
      porcentaje_tarifa: 0.0005,
      acumulacion: {
        porcentaje_acumulado: 0.001,
        subtotal_acumulado: 1000,
      },
    };

    const host = render(item, "edificacion");
    const texto = host.textContent ?? "";

    expect(texto).toContain("VALOR DE OBRA");
    expect(texto).toContain("PORCENTAJE");
    expect(texto).not.toContain("ESTRATEGIA");
    expect(texto).not.toContain("HABILITADAS");
    expect(texto).not.toContain("% TARIFA");
    expect(texto).not.toContain("ACUMULACION");
  });

  it("mantiene el recibo de Taludes sin contexto de estrategia", () => {
    const item = baseItem();
    item.liquidacion_tipo = {
      valor_declarado: 1_000_000,
      porcentaje_liquidacion: 0.001,
    };

    const host = render(item, "taludes");
    const texto = host.textContent ?? "";

    expect(texto).toContain("PORCENTAJE");
    expect(texto).not.toContain("ESTRATEGIA");
    expect(texto).not.toContain("ACUMULACION");
  });
});
