"use client";

/**
 * RhDelegadoMensualPdf — Componente React del recibo oficial de RH mensual
 * de Delegado.
 *
 * DISTRIBUCIÓN: la del documento oficial original "Liquidación de Honorarios a
 * Delegados" → escudo con título y subtítulo centrados, municipalidad y
 * delegado, nº de liquidación a la izquierda con el nº de RH a la derecha,
 * tabla de detalle de 14 columnas con fila TOTAL e importe final destacado.
 *
 * ESTILO: el del PDF de Liquidaciones (tipografía monoespaciada, bordes
 * negros, textos que envuelven). Los estilos son inline porque el documento
 * se monta en un iframe aislado sin el CSS de la app.
 *
 * A4 apaisada: en vertical las 14 columnas se cortarían.
 */
import type { ReciboHonorarioDelegadoMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";
import {
  formatCreatedAt,
  RhPdfLabelLine,
  RhPdfLogo,
  RhPdfPaper,
  rhPdfStyles,
} from "./rhPdfChrome";

/** Columnas del documento original (ancho en %). */
const COLUMNAS = [
  { label: "Nro.", width: "4%" },
  { label: "F. Rev.", width: "8%" },
  { label: "Expdte", width: "8%" },
  { label: "Nro. Comp.", width: "10%" },
  { label: "Rev", width: "4%" },
  { label: "Total", width: "7%" },
  { label: "IGV", width: "7%" },
  { label: "Subtotal", width: "8%" },
  { label: "Bruto", width: "8%" },
  { label: "Rt. CIP", width: "7%" },
  { label: "Ap. Cdmu", width: "7%" },
  { label: "Fnd. Cmm", width: "7%" },
  { label: "Hnratio", width: "8%" },
  { label: "N° RH", width: "4%" },
];

/** Monto con 2 decimales y separador de miles. */
function formatMonto(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "0.00";
  return Number(value).toLocaleString("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** Fecha `AAAA/MM/DD` (formato del documento clásico). */
function formatFecha(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const anio = date.getFullYear();
  const mes = String(date.getMonth() + 1).padStart(2, "0");
  const dia = String(date.getDate()).padStart(2, "0");
  return `${anio}/${mes}/${dia}`;
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

export function RhDelegadoMensualPdf({
  item,
}: {
  item: ReciboHonorarioDelegadoMensual;
}) {
  const del = item.delegado;
  const totales = item.totales;
  const detalles = item.detalles || [];
  const ctx = item.delegado_operacion_context;
  const numeroLiquidacion =
    item.mes != null ? String(item.mes).padStart(2, "0") : "";
  const numeroRh = item.numero != null ? String(item.numero) : "";

  return (
    <RhPdfPaper>
      {/* Header: escudo | título y subtítulo | liquidaciones y RH */}
      <div style={rhPdfStyles.header}>
        <RhPdfLogo />

        <div style={rhPdfStyles.titleBlock}>
          <p style={rhPdfStyles.docTitle}>
            Liquidación de Honorarios a Delegados
          </p>
          <p style={rhPdfStyles.docSubtitle}>
            Comisión Técnica Calificadora de Proyectos
          </p>
          <div style={{ marginTop: "6px", width: "100%" }}>
            <RhPdfLabelLine
              label="Municipalidad"
              value={ctx?.municipalidad_nombre ?? ""}
            />
            <RhPdfLabelLine
              label="Delegado"
              value={`CIP ${del?.cip ?? ""} - ${del?.nombre_completo ?? ""}`.trim()}
            />
          </div>
        </div>

        <div style={rhPdfStyles.sideBox}>
          <p style={rhPdfStyles.createdAt}>
            {formatCreatedAt(item.fecha_registro)}
          </p>
        </div>
      </div>

      {/* Nº de liquidación a la izquierda y nº de RH a la derecha */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          alignItems: "center",
          marginTop: "2px",
        }}
      >
        <p style={{ ...rhPdfStyles.sideValue, textAlign: "left" }}>
          Liquidación&nbsp; {numeroLiquidacion}
        </p>
        <p style={rhPdfStyles.sideValue}>{numeroRh}</p>
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
          {detalles.map((detalle, index) => {
            const total = detalle.total_liquidacion ?? 0;
            const subtotal = detalle.sub_total_liquidacion ?? 0;
            return (
              <tr key={detalle.detalle_id ?? `${detalle.expediente}-${index}`}>
                <td style={rhPdfStyles.tdCenter}>
                  {detalle.liquidacion_especifica_numero ?? ""}
                </td>
                <td style={rhPdfStyles.tdCenter}>
                  {formatFecha(detalle.fecha_revision)}
                </td>
                <td style={rhPdfStyles.td}>{detalle.expediente ?? ""}</td>
                <td style={rhPdfStyles.td}>
                  {formatNumeroComprobante(detalle.comprobante_activo)}
                </td>
                <td style={rhPdfStyles.tdCenter}>
                  {detalle.numero_revision ?? ""}
                </td>
                <td style={rhPdfStyles.tdRight}>{formatMonto(total)}</td>
                <td style={rhPdfStyles.tdRight}>
                  {formatMonto(total - subtotal)}
                </td>
                <td style={rhPdfStyles.tdRight}>{formatMonto(subtotal)}</td>
                <td style={rhPdfStyles.tdRight}>
                  {formatMonto(detalle.imp_bruto)}
                </td>
                <td style={rhPdfStyles.tdRight}>
                  {formatMonto(detalle.renta_cip)}
                </td>
                <td style={rhPdfStyles.tdRight}>
                  {formatMonto(detalle.aporte_codemu)}
                </td>
                <td style={rhPdfStyles.tdRight}>
                  {formatMonto(detalle.fondo_comun)}
                </td>
                <td style={rhPdfStyles.tdRight}>
                  {formatMonto(detalle.neto_honorario)}
                </td>
                <td style={rhPdfStyles.tdCenter}>{detalle.numero_rh ?? ""}</td>
              </tr>
            );
          })}

          {/* Fila TOTAL */}
          <tr>
            <td
              style={{ ...rhPdfStyles.td, ...rhPdfStyles.totalsLabel }}
              colSpan={8}
            >
              TOTAL
            </td>
            <td style={{ ...rhPdfStyles.td, ...rhPdfStyles.tdRight }}>
              {formatMonto(totales?.sub_total)}
            </td>
            <td style={{ ...rhPdfStyles.td, ...rhPdfStyles.tdRight }}>
              {formatMonto(totales?.renta_cip)}
            </td>
            <td style={rhPdfStyles.td} />
            <td style={rhPdfStyles.td} />
            <td style={{ ...rhPdfStyles.td, ...rhPdfStyles.tdRight }}>
              {formatMonto(totales?.neto_honorario)}
            </td>
            <td style={rhPdfStyles.td} />
          </tr>
        </tbody>
      </table>

      {/* Importe final */}
      <div style={rhPdfStyles.amountBox}>
        <p style={rhPdfStyles.amountLabel}>IMPORTE BRUTO S/.</p>
        <p style={rhPdfStyles.amountValue}>
          {formatMonto(totales?.neto_honorario)}
        </p>
      </div>
    </RhPdfPaper>
  );
}
