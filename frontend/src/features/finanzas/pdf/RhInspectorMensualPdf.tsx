"use client";

/**
 * RhInspectorMensualPdf — Componente React del recibo oficial de RH mensual
 * de Inspector.
 *
 * DISTRIBUCIÓN: la del documento oficial original "Liquidación de Honorarios por
 * Inspección Municipal de Obras" → escudo con título y subtítulo centrados,
 * inspector a la izquierda, periodo a la derecha, tabla de detalle de 11
 * columnas y caja de totales (SUB TOTAL / DESCUENTOS / HONORARIOS).
 *
 * ESTILO: el del PDF de Liquidaciones (tipografía monoespaciada, bordes
 * negros, textos que envuelven). Los estilos son inline porque el documento
 * se monta en un iframe aislado sin el CSS de la app.
 *
 * A4 vertical y responsive: la tabla ocupa el ancho de la hoja con columnas
 * en porcentaje, así que nunca se corta.
 */
import type { ReciboHonorarioInspectorMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";
import {
  formatCreatedAt,
  RhPdfLogo,
  RhPdfPaper,
  rhPdfStyles,
} from "./rhPdfChrome";

/** Columnas del documento original (ancho en %). */
const COLUMNAS = [
  { label: "Distrito", width: "11%" },
  { label: "Administrado", width: "20%" },
  { label: "Expediente", width: "8%" },
  { label: "Nro. Comp.", width: "10%" },
  { label: "Importe Bruto", width: "8%" },
  { label: "N° Insp. Program.", width: "7%" },
  { label: "Costo por inspección", width: "8%" },
  { label: "Inspecciones del mes", width: "8%" },
  { label: "Monto Bruto", width: "8%" },
  { label: "N° Insp. Pagadas hasta mes anterior", width: "7%" },
  { label: "Saldo de inspecciones", width: "5%" },
];

/** Número con 2 decimales y separador de miles. */
function formatMonto(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "0.00";
  return Number(value).toLocaleString("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** Importe sin separador de miles (como el documento oficial). */
function formatImporteBruto(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "0.00";
  return Number(value).toFixed(2);
}

/** Entero sin formato; vacío cuando no hay dato (como el documento oficial). */
function formatConteo(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "";
  return String(value);
}

/** Número de comprobante (serie-número). */
function formatNumeroComprobante(
  comprobante:
    | { serie?: string | null; numero?: string | null }
    | null
    | undefined,
): string {
  if (!comprobante) return "";
  const serie = comprobante.serie ?? "";
  const numero = comprobante.numero ?? "";
  if (serie && numero) return `${serie}-${numero}`;
  return serie || numero;
}

/** Periodo en formato clásico: `SEPTIEMBRE 2026`. */
function formatPeriodo(periodo?: number | null, mes?: number | null): string {
  if (periodo == null) return "—";
  if (mes == null) return String(periodo);
  const meses = [
    "ENERO",
    "FEBRERO",
    "MARZO",
    "ABRIL",
    "MAYO",
    "JUNIO",
    "JULIO",
    "AGOSTO",
    "SEPTIEMBRE",
    "OCTUBRE",
    "NOVIEMBRE",
    "DICIEMBRE",
  ];
  return `${meses[mes - 1] ?? String(mes)} ${periodo}`;
}

export function RhInspectorMensualPdf({
  item,
}: {
  item: ReciboHonorarioInspectorMensual;
}) {
  const insp = item.inspector;
  const totales = item.totales;
  const detalles = item.detalles || [];
  const inspectorNombre = insp?.nombre_completo || "—";

  return (
    <RhPdfPaper>
      {/* Header: escudo | título y subtítulo | inspector y periodo */}
      <div style={rhPdfStyles.header}>
        <RhPdfLogo />

        <div style={rhPdfStyles.titleBlock}>
          <p style={rhPdfStyles.docTitle}>
            Liquidación de Honorarios por Inspección Municipal de Obras
          </p>
          <p style={rhPdfStyles.docSubtitle}>
            Comisión de Asuntos Municipales - Colegio de Ingenieros de Lima
          </p>
          <p style={rhPdfStyles.personLine}>
            Inspector&nbsp; CIP {insp?.cip ?? ""} - {inspectorNombre}
          </p>
        </div>

        <div style={rhPdfStyles.sideBox}>
          <p style={rhPdfStyles.createdAt}>
            {formatCreatedAt(item.fecha_registro)}
          </p>
          <p style={rhPdfStyles.sideValueUnderlined}>
            {formatPeriodo(item.periodo, item.mes)}
          </p>
        </div>
      </div>

      {/* Detalle por liquidación */}
      <table style={rhPdfStyles.table}>
        <thead>
          <tr>
            {COLUMNAS.map((columna) => (
              <th key={columna.label} style={rhPdfStyles.th}>
                {columna.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {detalles.map((detalle, index) => (
            <tr key={detalle.detalle_id ?? `${detalle.expediente}-${index}`}>
              <td style={rhPdfStyles.td}>{detalle.distrito ?? ""}</td>
              <td style={rhPdfStyles.td}>{detalle.nombre_propietario ?? ""}</td>
              <td style={rhPdfStyles.td}>{detalle.expediente ?? ""}</td>
              <td style={rhPdfStyles.td}>
                {formatNumeroComprobante(detalle.comprobante_activo)}
              </td>
              <td style={rhPdfStyles.tdRight}>
                {formatImporteBruto(detalle.importe_bruto)}
              </td>
              <td style={rhPdfStyles.tdCenter}>
                {formatConteo(detalle.inspecciones_programadas)}
              </td>
              <td style={rhPdfStyles.tdRight}>
                {formatMonto(detalle.costo_por_inspeccion)}
              </td>
              <td style={rhPdfStyles.tdCenter}>
                {formatConteo(detalle.inspecciones_liquidadas)}
              </td>
              <td style={rhPdfStyles.tdRight}>
                {formatMonto(detalle.monto_contribuido)}
              </td>
              <td style={rhPdfStyles.tdCenter}>
                {formatConteo(detalle.inspecciones_pagadas_hasta_mes_anterior)}
              </td>
              <td style={rhPdfStyles.tdCenter}>
                {formatConteo(detalle.saldo_restante)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Totales: SUB TOTAL / DESCUENTOS / HONORARIOS */}
      <table style={rhPdfStyles.totalsBox}>
        <tbody>
          <tr>
            <td
              style={{ ...rhPdfStyles.totalsRow, ...rhPdfStyles.totalsLabel }}
            >
              SUB TOTAL
            </td>
            <td
              style={{ ...rhPdfStyles.totalsRow, ...rhPdfStyles.totalsValue }}
            >
              S/. {formatMonto(totales?.sub_total)}
            </td>
          </tr>
          <tr>
            <td
              style={{ ...rhPdfStyles.totalsRow, ...rhPdfStyles.totalsLabel }}
            >
              DESCUENTOS
            </td>
            <td
              style={{ ...rhPdfStyles.totalsRow, ...rhPdfStyles.totalsValue }}
            >
              -S/. {formatMonto(totales?.descuento)}
            </td>
          </tr>
          <tr>
            <td
              style={{
                ...rhPdfStyles.totalsTotalRow,
                ...rhPdfStyles.totalsLabel,
              }}
            >
              HONORARIOS
            </td>
            <td
              style={{
                ...rhPdfStyles.totalsTotalRow,
                ...rhPdfStyles.totalsValue,
              }}
            >
              S/. {formatMonto(totales?.honorarios)}
            </td>
          </tr>
        </tbody>
      </table>
    </RhPdfPaper>
  );
}
