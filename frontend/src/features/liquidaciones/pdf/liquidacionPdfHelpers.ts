/**
 * liquidacionPdfHelpers — Construye las filas del recibo de liquidación
 * según el tipo de liquidación.
 *
 * Cada tipo tiene campos específicos en `liquidacion_tipo`:
 * - edificacion → "porcentaje"
 * - impacto-vial / taludes → "porcentaje"
 * - habilitacion-urbana / mecanica-suelos → "m2"
 * - inspeccion-obra → "visitas"
 *
 * Este es el ÚNICO lugar donde se decide qué filas van en el recibo. La base
 * (`LiquidacionPdfPreview`) siempre delega aquí — no hay implementación
 * paralela ni decisiones de tipo dentro de la base.
 */
import type { PdfLiquidacionItem, PdfTipoSlug } from "./pdfTypes";

function formatCurrency(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return "S/ 0.00";
  return `S/ ${Number(value).toLocaleString("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

/**
 * Costo por visita = UIT × porcentaje_uit.
 * `porcentaje_uit` ya es una proporción (decimal 0-1, ej. 0.05 = 5 %).
 * Devuelve null cuando falta el UIT de la liquidación o el porcentaje.
 */
function calcCostoPorVisita(item: PdfLiquidacionItem): number | null {
  const uit = item.liquidacion_general.uit?.valor;
  const porcentaje = item.liquidacion_tipo.porcentaje_uit;
  if (uit == null || porcentaje == null) return null;
  const costo = Number(uit) * Number(porcentaje);
  return Number.isFinite(costo) ? costo : null;
}

/**
 * Filas del bloque de detalle común (parte base del recibo).
 *
 * El tipo decide si el nombre del proyecto se imprime: en Inspección de Obra
 * no aplica — la liquidación de inspección hereda el nombre del proyecto de
 * la liquidación previa y no describe la obra inspeccionada.
 */
export function buildCommonFieldRows(
  item: PdfLiquidacionItem,
  tipo: PdfTipoSlug,
): ReadonlyArray<readonly [string, string]> {
  const lg = item.liquidacion_general;
  const proyecto = lg.proyecto;
  const entidad = proyecto.entidad ?? null;

  const rows: Array<[string, string]> = [
    ["RUC", entidad?.numero_documento ?? ""],
    ["RAZON SOCIAL", entidad?.razon_social ?? ""],
    [
      "NOMBRE DEL PROPIETARIO",
      proyecto.nombre_propietario || entidad?.razon_social || "",
    ],
  ];

  if (tipo !== "inspeccion-obra") {
    rows.push(["NOMBRE DEL PROYECTO", lg.denominacion_de_proyecto ?? ""]);
  }

  rows.push(["DPTO. / PROV. / DISTRITO", lg.municipalidad?.nombre ?? ""]);
  rows.push(["DIRECCION DE LA OBRA", proyecto.direccion ?? ""]);

  return rows;
}

export function buildExtraFieldRows(
  item: PdfLiquidacionItem,
  tipo: PdfTipoSlug,
): ReadonlyArray<readonly [string, string]> {
  const lt = item.liquidacion_tipo;
  const rows: Array<[string, string]> = [];
  const derechoMinimo = lt.derecho_minimo ?? 0;

  if (tipo === "edificacion") {
    // Motor porcentaje.
    if (lt.valor_declarado && lt.valor_declarado > 0) {
      rows.push(["VALOR DE OBRA", formatCurrency(lt.valor_declarado)]);
    }
    if (lt.porcentaje_liquidacion != null) {
      const pct = (Number(lt.porcentaje_liquidacion) * 100).toFixed(2);
      rows.push(["PORCENTAJE", `${pct}%`]);
    }
    return rows;
  }

  if (tipo === "impacto-vial" || tipo === "taludes") {
    // Motor porcentaje (sin contexto de estrategia: esos motores no lo tienen)
    if (lt.valor_declarado && lt.valor_declarado > 0) {
      rows.push(["VALOR DE OBRA", formatCurrency(lt.valor_declarado)]);
    }
    if (lt.porcentaje_liquidacion != null) {
      const pct = (Number(lt.porcentaje_liquidacion) * 100).toFixed(2);
      rows.push(["PORCENTAJE", `${pct}%`]);
    }
    return rows;
  }

  if (tipo === "habilitacion-urbana" || tipo === "mecanica-suelos") {
    // Motor m2
    if (lt.area_m2 && lt.area_m2 > 0) {
      rows.push(["AREA", `${Number(lt.area_m2).toLocaleString("es-PE")} m²`]);
    }
    if (lt.costo_por_m2 && lt.costo_por_m2 > 0) {
      rows.push(["COSTO POR M2", formatCurrency(lt.costo_por_m2)]);
    }
    if (derechoMinimo > 0) {
      rows.push(["DERECHO MINIMO", `${formatCurrency(derechoMinimo)}`]);
    }
    return rows;
  }

  if (tipo === "inspeccion-obra") {
    // Motor visitas
    if (lt.cantidad_visitas && lt.cantidad_visitas > 0) {
      rows.push(["CANTIDAD DE VISITAS", `${lt.cantidad_visitas}`]);
    }
    const costoPorVisita = calcCostoPorVisita(item);
    if (costoPorVisita != null) {
      rows.push(["COSTO POR VISITA", formatCurrency(costoPorVisita)]);
    }
    if (lt.categoria) {
      rows.push(["CATEGORIA", lt.categoria]);
    }
    const inspector = lt.inspectores?.[0];
    const perfil = inspector?.perfil_ingeniero;
    if (perfil?.nombre_completo) {
      rows.push(["INSPECTOR", perfil.nombre_completo]);
    }
    if (perfil?.cip) {
      rows.push(["CIP", perfil.cip]);
    }
    if (derechoMinimo > 0) {
      rows.push(["DERECHO MINIMO", `${formatCurrency(derechoMinimo)}`]);
    }
    return rows;
  }

  // Tipo desconocido: solo derecho mínimo
  if (derechoMinimo > 0) {
    rows.push(["DERECHO MINIMO", `${formatCurrency(derechoMinimo)}`]);
  }
  return rows;
}
