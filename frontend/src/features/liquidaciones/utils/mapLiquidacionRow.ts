/**
 * Helper that maps a domain-specific liquidacion item into the canonical
 * `LiquidacionTableRow` shape used by the Table view (and any other view that
 * wants a flat projection).
 *
 * Centralizes derivations that were duplicated across each card component:
 *   - publicId via formatPublicId(tipo, fecha, numero)
 *   - comprobanteActivo = comprobantes.find(c => c.activo) ?? null
 *   - municipalidadLabel = codigo + nombre when codigo present
 *   - distritoLabel = join(distrito, provincia, departamento)
 *   - entidadNombre = entidad.razon_social ?? proyecto.nombre_propietario
 */

import type { LiquidacionTableRow } from "../components/tables/LiquidacionesTable";
import {
  formatPublicId,
  getTipoSlugFromCodigo,
} from "./formatPublicId";

export type LiquidacionGeneralLike = {
  id: string;
  estado?: string | null | undefined;
  numero_revision?: number | null | undefined;
  expediente?: string | null | undefined;
  legacy?: boolean | undefined;
  fecha_registro: string;
  sub_total?: number | null | undefined;
  total?: number | null | undefined;
  denominacion_de_proyecto?: string | null | undefined;
  comprobantes?: Array<{
    activo: boolean;
    tipo_comprobante?: string | null | undefined;
    serie?: string | null | undefined;
    numero?: string | null | undefined;
  }> | null;
  municipalidad?: { codigo: string | null; nombre: string } | null;
  tipo_liquidacion?: { codigo?: string | null | undefined } | null;
  proyecto: {
    nombre_propietario?: string | null | undefined;
    direccion: string;
    urbanizacion?: string | null | undefined;
    distrito?: {
      nombre: string;
      provincia?: { nombre: string } | null | undefined;
      departamento?: { nombre: string } | null | undefined;
    } | null;
    entidad?: {
      razon_social: string;
      tipo_documento?: string | null;
      numero_documento?: string | null;
    } | null;
  };
};

export function mapLiquidacionRow(
  tipoSlug: string | null | undefined,
  liquidacionGeneral: LiquidacionGeneralLike,
  numero: number | null | undefined,
): LiquidacionTableRow {
  // Derive tipoSlug from tipo_liquidacion.codigo when not provided
  const resolvedTipoSlug =
    tipoSlug ?? getTipoSlugFromCodigo(liquidacionGeneral.tipo_liquidacion?.codigo) ?? "";
  const comprobanteActivo =
    liquidacionGeneral.comprobantes?.find((c) => c.activo) ?? null;

  const entidad =
    liquidacionGeneral.proyecto.entidad?.razon_social ??
    liquidacionGeneral.proyecto.nombre_propietario ??
    "—";

  return {
    id: liquidacionGeneral.id,
    publicId: formatPublicId(
      resolvedTipoSlug,
      liquidacionGeneral.fecha_registro,
      numero,
    ),
    estado: liquidacionGeneral.estado,
    numeroRevision: liquidacionGeneral.numero_revision,
    entidad,
    entidadDocTipo: liquidacionGeneral.proyecto.entidad?.tipo_documento,
    entidadDocNumero: liquidacionGeneral.proyecto.entidad?.numero_documento,
    proyecto:
      liquidacionGeneral.denominacion_de_proyecto ??
      liquidacionGeneral.proyecto.nombre_propietario ??
      null,
    direccion: liquidacionGeneral.proyecto.direccion,
    urbanizacion: liquidacionGeneral.proyecto.urbanizacion,
    administrado: liquidacionGeneral.proyecto.nombre_propietario,
    municipalidadCodigo: liquidacionGeneral.municipalidad?.codigo,
    municipalidadNombre: liquidacionGeneral.municipalidad?.nombre,
    expediente: liquidacionGeneral.expediente,
    fecha: liquidacionGeneral.fecha_registro,
    legacy: liquidacionGeneral.legacy,
    comprobanteActivo,
    subTotal: liquidacionGeneral.sub_total,
    total: liquidacionGeneral.total,
  };
}
