/**
 * pdfTypes — Tipos y metadatos compartidos por el recibo oficial de liquidación.
 *
 * Módulo neutro (sin dependencias de DOM ni de otros módulos del PDF) para
 * que tanto el módulo por motor (`liquidacionPdfHelpers`) como la base
 * (`LiquidacionPdfPreview`) dependan de él sin ciclos.
 *
 * Forma mínima que necesita el recibo — datos del output del backend.
 */
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
    igv?: { valor?: number } | null;
    uit?: { valor?: number } | null;
    proyecto: {
      nombre_propietario?: string;
      direccion?: string;
      entidad?: {
        tipo_documento?: string;
        numero_documento?: string;
        razon_social?: string;
      } | null;
    };
    denominacion_de_proyecto?: string | null;
    /** Código de cuenta (LiquidacionCodigo) asociado al tipo de liquidación */
    codigo_cta?: string | null;
    /** Contacto principal de la liquidación (ContactoOutput) — persona de contacto, no el propietario */
    contacto?: {
      nombres?: string | null;
      apellidos?: string | null;
      dni?: string | null;
      cargo?: string | null;
      telefono?: string | null;
      celular?: string | null;
      email?: string | null;
    } | null;
  };
  liquidacion_especifica: {
    /** Número correlativo de la especialidad (auto-incremental) — es el "Nro" del recibo */
    numero?: number;
  };
  liquidacion_tipo: {
    valor_declarado?: number | null;
    porcentaje_liquidacion?: number | null;
    area_m2?: number;
    costo_por_m2?: number;
    cantidad_visitas?: number;
    /** Proporción de UIT por visita (decimal 0-1, ej. 0.05 = 5 %) */
    porcentaje_uit?: number | null;
    categoria?: string;
    derecho_minimo?: number;
    derecho_maximo?: number;
    // ── Estrategia PO (SOLO Edificaciones) ────────────────────────────────
    // Taludes, Impacto Vial, edge y legacy NUNCA traen estos campos: el
    // wrapper PO compartido del backend no los expone.
    /** Estrategia persistida: NORMAL_SELECCIONADAS, TARIFA_HABILITADAS_PARTICIPANTES o TOTAL_EXPLICITO. */
    estrategia_cotizacion?: string | null;
    /** Snapshot de H (habilitadas del catálogo en la fecha efectiva). */
    count_habilitadas?: number | null;
    /** Total final autoritativo persistido (TOTAL_EXPLICITO). */
    total_explicito?: number | null;
    /** Snapshot del porcentaje unitario (f) de la tarifa aplicada. */
    porcentaje_tarifa?: number | null;
    /** Proyección informativa de la diferencia padre - detalles. */
    acumulacion?: {
      /** NULL en TOTAL_EXPLICITO: el total es autoritativo. */
      porcentaje_acumulado?: number | null;
      subtotal_acumulado?: number;
    } | null;
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

/** Slug del tipo de liquidación — 6 tipos, agrupados en 3 motores de cálculo. */
export type PdfTipoSlug =
  | "edificacion"
  | "taludes"
  | "impacto-vial"
  | "habilitacion-urbana"
  | "mecanica-suelos"
  | "inspeccion-obra";

/** Título oficial del recibo, por tipo. */
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
