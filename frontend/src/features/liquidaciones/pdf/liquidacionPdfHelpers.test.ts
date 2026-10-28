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
});
