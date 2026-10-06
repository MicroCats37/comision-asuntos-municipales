/**
 * liquidacionPdfHelpers — Construye las filas extra específicas del PDF
 * según el tipo de liquidación.
 *
 * Cada tipo tiene campos específicos en `liquidacion_tipo`:
 * - edificacion / impacto-vial / taludes → "porcentaje"
 * - habilitacion-urbana / mecanica-suelos → "m2"
 * - inspeccion-obra → "visitas"
 *
 * Devuelve un array `[[label, value], ...]` listo para pasar como
 * cuarto argumento a `printLiquidacionPreview(item, tipo, extraFieldRows)`.
 */
import type { PdfLiquidacionItem } from "./buildLiquidacionPdfElement";
import type { PdfTipoSlug } from "./LiquidacionPdfPreview";

function formatCurrency(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return "S/ 0.00";
  return `S/ ${Number(value).toLocaleString("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function buildExtraFieldRows(
  item: PdfLiquidacionItem,
  tipo: PdfTipoSlug,
): ReadonlyArray<readonly [string, string]> {
  const lt = item.liquidacion_tipo;
  const rows: Array<[string, string]> = [];
  const derechoMinimo = lt.derecho_minimo ?? 0;

  if (tipo === "edificacion" || tipo === "impacto-vial" || tipo === "taludes") {
    // Motor porcentaje
    if (lt.valor_declarado && lt.valor_declarado > 0) {
      rows.push(["VALOR DE OBRA", formatCurrency(lt.valor_declarado)]);
    }
    if (lt.porcentaje_liquidacion != null) {
      const pct = (Number(lt.porcentaje_liquidacion) * 100).toFixed(2);
      rows.push(["PORCENTAJE", `${pct}%`]);
    }
    if (derechoMinimo > 0) {
      rows.push(["DERECHO MINIMO", `${formatCurrency(derechoMinimo)} + IGV`]);
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
      rows.push(["DERECHO MINIMO", `${formatCurrency(derechoMinimo)} + IGV`]);
    }
    return rows;
  }

  if (tipo === "inspeccion-obra") {
    // Motor visitas
    if (lt.cantidad_visitas && lt.cantidad_visitas > 0) {
      rows.push(["CANTIDAD DE VISITAS", `${lt.cantidad_visitas}`]);
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
      rows.push(["DERECHO MINIMO", `${formatCurrency(derechoMinimo)} + IGV`]);
    }
    return rows;
  }

  // Tipo desconocido: solo derecho mínimo
  if (derechoMinimo > 0) {
    rows.push(["DERECHO MINIMO", `${formatCurrency(derechoMinimo)} + IGV`]);
  }
  return rows;
}
