/**
 * buildLiquidacionPdfElement — Compositor del recibo oficial.
 *
 * Une las secciones (pdfSections) en orden, con el tema (pdfTheme) como
 * fuente de verdad de estilos. No hardcodea estilos ni contenido aquí.
 *
 * Orden: header → title → detalle (común + motor) → total a pagar → footer
 */
import { applyStyles } from "@/components-app/pdf/pdfShell";
import {
  renderDetalle,
  renderFooter,
  renderHeader,
  renderTitle,
  renderTotalPagar,
} from "./pdfSections";
import { pdfTheme } from "./pdfTheme";

/** Forma mínima que necesita el recibo — datos del output del backend */
export interface PdfLiquidacionItem {
  liquidacion_general: {
    id: string;
    municipalidad?: { codigo?: string | null; nombre?: string } | null;
    usuario_creador?: {
      nombres?: string | null;
      apellidos?: string | null;
      username?: string | null;
    } | null;
    fecha_registro?: string | null;
    expediente?: string | null;
    numero_revision?: number;
    sub_total?: number;
    total?: number;
    retencion?: boolean;
    igv?: { valor?: number } | null;
    uit?: { valor?: number } | null;
    proyecto: {
      denominacion: string;
      nombre_propietario?: string;
      direccion?: string;
      entidad?: {
        tipo_documento?: string;
        numero_documento?: string;
        razon_social?: string;
      } | null;
    };
  };
  liquidacion_especifica: {
    /** Número correlativo de la especialidad (auto-incremental) — es el "Nro" del recibo */
    numero?: number;
  };
  liquidacion_tipo: {
    valor_declarado?: number;
    porcentaje_liquidacion?: number;
    area_m2?: number;
    costo_por_m2?: number;
    cantidad_visitas?: number;
    categoria?: string;
    derecho_minimo?: number;
    derecho_maximo?: number;
    inspectores?: {
      id?: string;
      inspector_id?: string;
      perfil_ingeniero?: {
        cip?: string;
        nombre_completo?: string;
      };
    }[];
    detalles?: {
      subtotal?: number;
      igv?: number;
      uit?: number;
      total?: number;
      porcentaje_aplicado?: number;
    }[];
  };
}

export type PdfMotor = "porcentaje" | "m2" | "visitas";

export function getMotorByTipo(tipo: string): PdfMotor {
  if (tipo === "habilitacion-urbana" || tipo === "mecanica-suelos") return "m2";
  if (tipo === "inspeccion-obra") return "visitas";
  return "porcentaje";
}

export function getPdfTitleByTipo(tipo: string): string {
  const TITLES: Record<string, string> = {
    edificacion:
      "LIQUIDACION DE DERECHOS POR CALIFICACION DE PROYECTOS DE INGENIERIA",
    "impacto-vial": "LIQUIDACION DE DERECHOS POR IMPACTO VIAL",
    taludes: "LIQUIDACION DE DERECHOS POR TALUDES",
    "habilitacion-urbana": "LIQUIDACION DE DERECHOS POR HABILITACION URBANA",
    "mecanica-suelos": "LIQUIDACION DE DERECHOS POR MECANICA DE SUELOS",
    "inspeccion-obra": "LIQUIDACION DE DERECHOS POR INSPECCION DE OBRA",
  };
  return TITLES[tipo] ?? tipo.replace(/[-_]/g, " ").toUpperCase();
}

export function buildLiquidacionPdfElement(
  item: PdfLiquidacionItem,
  tipo: string,
  ownerDocument: Document,
): HTMLElement {
  const motor = getMotorByTipo(tipo);

  // Root
  const root = ownerDocument.createElement("div");
  applyStyles(root, pdfTheme.root);

  // Paper (borde del recibo)
  const paper = ownerDocument.createElement("div");
  applyStyles(paper, pdfTheme.paper);
  root.appendChild(paper);

  // Secciones en orden
  renderHeader(paper, item);
  renderTitle(paper, tipo);
  renderDetalle(paper, item, motor);
  renderTotalPagar(paper, item);
  renderFooter(paper, item);

  return root;
}
