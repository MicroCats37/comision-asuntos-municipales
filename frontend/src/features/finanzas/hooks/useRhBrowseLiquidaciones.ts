/**
 * useRhBrowseLiquidaciones — listado de liquidaciones EXISTENTES para el browse
 * del RH mensual (paso 2 del wizard de Delegado e Inspector).
 *
 * El browse usa el MISMO contrato de filtros que las listas de Liquidaciones
 * (`LiquidacionFiltros`) y el MISMO panel de filtros (`LiquidacionFiltroModal`):
 * el browse NO tiene un panel de filtros propio.
 *
 * Origen del listado (misma decisión que el diseño):
 * - Si el wizard conoce un tipo CONCRETO de liquidación → listado por tipo
 *   (`GET /liquidaciones/{tipo}/`), que admite los 12 filtros del contrato
 *   `LiquidacionFiltros`.
 * - Si el tipo es un COMODÍN (el wizard no lo conoce) → listado cross-tipo
 *   (`GET /liquidaciones/generales/`), que admite un subconjunto (no admite
 *   rango de fechas, número ni comprobante vigente).
 *
 * Los filtros que el endpoint activo NO soporta se OMITEN de forma explícita
 * (nunca se envían vacíos: un filtro vacío ampliaría el resultado).
 *
 * NO hay filtro municipal IMPLÍCITO: `entidad_id` sólo viaja si el usuario lo
 * elige en el panel de filtros de Liquidaciones.
 */

import { useMemo } from "react";
import { z } from "zod";
import { useApiQuery } from "@/hooks";
import type { LiquidacionFiltros } from "@/features/liquidaciones/hooks/useLiquidacionList";
import {
  LiquidacionGeneralOutputSchema,
  paginatedResponseSchema,
} from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import { apiResponseSchema } from "@/types/api.types";

/** Endpoint de listado por tipo de liquidación. */
export const RH_BROWSE_TIPO_ENDPOINTS: Record<string, string> = {
  EDIFICACION: "/liquidaciones/edificaciones/",
  HABILITACION_URBANA: "/liquidaciones/habilitacion-urbana/",
  MECANICA_SUELOS: "/liquidaciones/mecanica-suelos/",
  TALUDES: "/liquidaciones/taludes/",
  IMPACTO_VIAL: "/liquidaciones/impacto-vial/",
  INSPECCION_OBRA: "/liquidaciones/inspeccion-obra/",
};

/** Endpoint cross-tipo (el wizard no conoce un tipo concreto). */
export const RH_BROWSE_ENDPOINT_GENERAL = "/liquidaciones/generales/";

/** Filtros del contrato `LiquidacionFiltros` manejados por el browse. */
export type RhBrowseFiltroNombre = keyof LiquidacionFiltros;

/** Etiqueta legible de cada filtro (chips activos y avisos de omisión). */
export const RH_BROWSE_ETIQUETA_FILTRO: Record<RhBrowseFiltroNombre, string> = {
  entidad_id: "Municipalidad",
  distrito_id: "Distrito",
  propietario: "Propietario",
  razon_social: "Razón Social",
  direccion: "Dirección",
  documento: "N° Documento Entidad",
  fecha_desde: "Fecha Desde",
  fecha_hasta: "Fecha Hasta",
  numero: "Número",
  expediente: "Expediente",
  comprobante_serie: "Comprobante — Serie",
  comprobante_numero: "Comprobante — Número",
};

/**
 * Filtros que EDITA el usuario en el panel de Liquidaciones.
 *
 * Los que no están en esta lista (p. ej. `expediente`, que el panel de
 * Liquidaciones no expone) los SEMILLA el wizard y se conservan mientras el
 * panel no los toque: quitarlos es explícito (chip "Quitar filtro").
 */
export const FILTROS_PANEL_LIQUIDACION: RhBrowseFiltroNombre[] = [
  "entidad_id",
  "distrito_id",
  "propietario",
  "razon_social",
  "direccion",
  "documento",
  "fecha_desde",
  "fecha_hasta",
  "numero",
  "comprobante_serie",
  "comprobante_numero",
];

/**
 * Filtros soportados por el listado POR TIPO.
 *
 * `numero` es el número de la liquidación específica (exacto) — la misma
 * semántica que en las candidatas RH.
 */
const FILTROS_SOPORTADOS_POR_TIPO: RhBrowseFiltroNombre[] = [
  "entidad_id",
  "distrito_id",
  "propietario",
  "razon_social",
  "direccion",
  "documento",
  "fecha_desde",
  "fecha_hasta",
  "numero",
  "expediente",
  "comprobante_serie",
  "comprobante_numero",
];

/**
 * Filtros soportados por el listado CROSS-TIPO (`/liquidaciones/generales/`).
 *
 * NO soporta el rango de fechas, `numero` ni los filtros de comprobante
 * vigente: se omiten de forma explícita.
 */
const FILTROS_SOPORTADOS_GENERAL: RhBrowseFiltroNombre[] = [
  "entidad_id",
  "distrito_id",
  "propietario",
  "razon_social",
  "direccion",
  "documento",
  "expediente",
];

/**
 * Filtros del wizard RH que sirven de SEMILLA para el panel de Liquidaciones.
 *
 * El browse NO hereda el panel de candidatas: sólo toma los valores
 * compatibles con el contrato `LiquidacionFiltros` para precargar el panel
 * de filtros de Liquidaciones. La municipalidad de la operatividad NO se
 * hereda (sería un filtro implícito).
 */
export interface RhBrowseFiltrosSemilla {
  /** N.º de expediente de la liquidación (icontains). */
  expediente?: string;
  /** N.º de la liquidación específica (texto; sólo se hereda si es entero). */
  numero?: string;
  /** Nombre del propietario del proyecto (icontains). */
  propietario?: string;
  /** Dirección del proyecto (icontains). */
  direccion?: string;
  /** N.º de documento de la entidad (icontains). */
  documento?: string;
  /** Serie del comprobante VIGENTE (icontains). */
  comprobante_serie?: string;
  /** Número del comprobante VIGENTE (icontains). */
  comprobante_numero?: string;
}

/** Filtro heredado que el endpoint activo no puede aplicar. */
export interface RhBrowseFiltroOmitido {
  filtro: RhBrowseFiltroNombre;
  razon: string;
}

export interface RhBrowseParamsResult {
  /** Parámetros de query realmente enviados al backend. */
  params: Record<string, string | number>;
  /** Filtros activos descartados de forma explícita. */
  omitidos: RhBrowseFiltroOmitido[];
}

/** Normaliza un texto de filtro (recorta y descarta vacíos). */
function texto(value?: string): string {
  return value?.trim() ?? "";
}

/**
 * Convierte los filtros del wizard RH (semilla) en filtros del contrato
 * `LiquidacionFiltros`.
 *
 * Función PURA (sin React ni HTTP): la municipalidad de la operatividad NO
 * se propaga — el browse no aplica ningún filtro municipal implícito.
 */
export function buildRhBrowseSemillaFiltros({
  filtros,
  fechaDesde,
  fechaHasta,
}: {
  filtros?: RhBrowseFiltrosSemilla;
  fechaDesde?: string;
  fechaHasta?: string;
}): LiquidacionFiltros {
  const semilla: LiquidacionFiltros = {};

  if (texto(filtros?.expediente)) semilla.expediente = texto(filtros?.expediente);
  if (texto(filtros?.propietario))
    semilla.propietario = texto(filtros?.propietario);
  if (texto(filtros?.direccion)) semilla.direccion = texto(filtros?.direccion);
  if (texto(filtros?.documento)) semilla.documento = texto(filtros?.documento);
  if (texto(filtros?.comprobante_serie))
    semilla.comprobante_serie = texto(filtros?.comprobante_serie);
  if (texto(filtros?.comprobante_numero))
    semilla.comprobante_numero = texto(filtros?.comprobante_numero);

  // El número sólo se hereda si es un entero válido: el listado exige un
  // match EXACTO sobre el número de la liquidación específica.
  const numeroRaw = texto(filtros?.numero);
  const numero = Number(numeroRaw);
  if (numeroRaw && Number.isInteger(numero) && numero > 0) {
    semilla.numero = numero;
  }

  if (texto(fechaDesde)) semilla.fecha_desde = texto(fechaDesde);
  if (texto(fechaHasta)) semilla.fecha_hasta = texto(fechaHasta);

  return semilla;
}

/**
 * Fusiona los filtros que devuelve el panel de Liquidaciones con los filtros
 * activos del browse.
 *
 * El panel REEMPLAZA los filtros que edita (si el usuario borra un campo, el
 * filtro desaparece) y CONSERVA los que no expone (p. ej. `expediente`,
 * sembrado por el wizard), que el usuario puede quitar con su chip.
 */
export function fusionarFiltrosLiquidacion(
  current: LiquidacionFiltros,
  applied: LiquidacionFiltros,
): LiquidacionFiltros {
  const merged: LiquidacionFiltros = { ...current };
  for (const filtro of FILTROS_PANEL_LIQUIDACION) {
    delete merged[filtro];
  }
  return { ...merged, ...applied };
}

/**
 * Construye los parámetros del listado de browse.
 *
 * Función PURA (sin React ni HTTP) para poder verificar la paridad de filtros
 * de forma aislada.
 */
export function buildRhBrowseParams({
  filtros,
  tipoCodigo,
}: {
  filtros?: LiquidacionFiltros;
  tipoCodigo?: string | null;
}): RhBrowseParamsResult {
  const esGeneral =
    !tipoCodigo || !(tipoCodigo in RH_BROWSE_TIPO_ENDPOINTS);
  const soportados = esGeneral
    ? FILTROS_SOPORTADOS_GENERAL
    : FILTROS_SOPORTADOS_POR_TIPO;

  const params: Record<string, string | number> = {};
  const omitidos: RhBrowseFiltroOmitido[] = [];

  const aplicar = (
    filtro: RhBrowseFiltroNombre,
    valor: string | number | undefined,
  ) => {
    if (valor === undefined || valor === null || valor === "") return;
    if (!soportados.includes(filtro)) {
      omitidos.push({
        filtro,
        razon: "El listado activo no admite este filtro: se omite.",
      });
      return;
    }
    params[filtro] = valor;
  };

  aplicar("entidad_id", texto(filtros?.entidad_id));
  aplicar("distrito_id", texto(filtros?.distrito_id));
  aplicar("propietario", texto(filtros?.propietario));
  aplicar("razon_social", texto(filtros?.razon_social));
  aplicar("direccion", texto(filtros?.direccion));
  aplicar("documento", texto(filtros?.documento));
  aplicar("expediente", texto(filtros?.expediente));
  aplicar("comprobante_serie", texto(filtros?.comprobante_serie));
  aplicar("comprobante_numero", texto(filtros?.comprobante_numero));
  aplicar("fecha_desde", texto(filtros?.fecha_desde));
  aplicar("fecha_hasta", texto(filtros?.fecha_hasta));

  // `numero` es un match EXACTO sobre el número de la liquidación específica.
  const numero = filtros?.numero;
  if (numero !== undefined && numero !== null) {
    if (!soportados.includes("numero")) {
      omitidos.push({
        filtro: "numero",
        razon: "El listado activo no admite este filtro: se omite.",
      });
    } else if (!Number.isInteger(numero) || numero <= 0) {
      omitidos.push({
        filtro: "numero",
        razon:
          "El listado exige un número entero exacto: el valor introducido se omite.",
      });
    } else {
      params.numero = numero;
    }
  }

  return { params, omitidos };
}

/** Payload crudo de un item del listado (3 wrappers). */
export interface RhBrowseRawItem {
  liquidacion_general: z.infer<typeof LiquidacionGeneralOutputSchema>;
  liquidacion_especifica: { id: string; numero: number } | null;
  tipo_liquidacion: { codigo?: string | null; nombre?: string | null } | null;
}

/** Item normalizado para la UI del browse. */
export interface RhBrowseItem {
  /** Id de la LiquidacionGeneral. */
  id: string;
  /** Payload crudo (para el modal de detalle de solo lectura). */
  raw: RhBrowseRawItem;
  expediente: string | null;
  /** Número de la liquidación específica. */
  numero: number | null;
  tipoCodigo: string | null;
  tipoNombre: string | null;
  estado: string | null;
  total: number;
  subTotal: number;
  fechaRegistro: string;
  propietario: string | null;
  direccion: string | null;
  municipalidad: string | null;
  numeroRevision: number | null;
  /** Comprobante VIGENTE de la liquidación (activo=True). */
  comprobante: {
    tipo: string | null;
    serie: string | null;
    numero: string | null;
    fecha_emision: string | null;
  } | null;
}

const rhBrowseItemSchema = z.object({
  liquidacion_general: LiquidacionGeneralOutputSchema,
  liquidacion_especifica: z
    .object({ id: z.string(), numero: z.coerce.number().int() })
    .nullish(),
  tipo_liquidacion: z
    .object({ codigo: z.string().nullish(), nombre: z.string().nullish() })
    .nullish(),
});

const rhBrowsePaginatedSchema = apiResponseSchema(
  paginatedResponseSchema(rhBrowseItemSchema),
);

function normalizarItem(raw: RhBrowseRawItem): RhBrowseItem {
  const lg = raw.liquidacion_general;
  const tipoCodigo =
    raw.tipo_liquidacion?.codigo ?? lg.tipo_liquidacion?.codigo ?? null;
  const tipoNombre =
    raw.tipo_liquidacion?.nombre ?? lg.tipo_liquidacion?.nombre ?? null;
  const comprobanteActivo =
    lg.comprobantes.find((comprobante) => comprobante.activo) ?? null;

  return {
    id: lg.id,
    raw,
    expediente: lg.expediente ?? null,
    numero: raw.liquidacion_especifica?.numero ?? null,
    tipoCodigo,
    tipoNombre,
    estado: lg.estado ?? null,
    total: lg.total,
    subTotal: lg.sub_total,
    fechaRegistro: lg.fecha_registro,
    propietario: lg.proyecto?.nombre_propietario ?? null,
    direccion: lg.proyecto?.direccion ?? null,
    municipalidad: lg.municipalidad?.nombre ?? null,
    numeroRevision: lg.numero_revision ?? null,
    comprobante: comprobanteActivo
      ? {
          tipo: comprobanteActivo.tipo_comprobante ?? null,
          serie: comprobanteActivo.serie ?? null,
          numero: comprobanteActivo.numero ?? null,
          fecha_emision: comprobanteActivo.fecha_emision ?? null,
        }
      : null,
  };
}

export interface UseRhBrowseLiquidacionesProps {
  /** Código de tipo conocido por el wizard (null/undefined → cross-tipo). */
  tipoCodigo?: string | null;
  /** Filtros activos del panel de filtros de Liquidaciones. */
  filtros?: LiquidacionFiltros;
  page?: number;
  pageSize?: number;
  enabled?: boolean;
}

/**
 * Hook de solo lectura para el browse de liquidaciones existentes del RH.
 */
export function useRhBrowseLiquidaciones({
  tipoCodigo,
  filtros,
  page = 1,
  pageSize = 20,
  enabled = true,
}: UseRhBrowseLiquidacionesProps) {
  const { params, omitidos } = useMemo(
    () => buildRhBrowseParams({ filtros, tipoCodigo }),
    [filtros, tipoCodigo],
  );

  const endpoint =
    tipoCodigo && tipoCodigo in RH_BROWSE_TIPO_ENDPOINTS
      ? RH_BROWSE_TIPO_ENDPOINTS[tipoCodigo]
      : RH_BROWSE_ENDPOINT_GENERAL;

  const queryParams = useMemo(
    () => ({ ...params, page, page_size: pageSize }),
    [params, page, pageSize],
  );

  const {
    data,
    isLoading,
    isError,
    refetch,
  } = useApiQuery({
    queryKey: ["rh-browse", "liquidaciones", endpoint],
    url: endpoint,
    schema: rhBrowsePaginatedSchema,
    params: queryParams,
    queryOptions: { enabled },
  });

  const paginated = data?.data;
  const rawItems = (paginated?.items ?? []) as RhBrowseRawItem[];
  const items = rawItems.map(normalizarItem);

  return {
    items,
    total: paginated?.total ?? 0,
    page: paginated?.page ?? page,
    pageSize: paginated?.page_size ?? pageSize,
    totalPages: paginated?.total_pages ?? 0,
    isLoading,
    isError,
    refetch,
    /** Endpoint activo (por tipo o cross-tipo). */
    endpoint,
    /** Filtros activos descartados de forma explícita. */
    omitidos,
  };
}
