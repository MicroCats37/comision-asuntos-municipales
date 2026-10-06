/**
 * Hook para listar liquidaciones GENERALES (cualquier tipo) — para búsqueda de previa.
 * Endpoint: GET /liquidaciones/generales/
 * Devuelve PaginatedData[LiquidacionGeneralOutput] con tipo_liquidacion.
 */

import { z } from "zod";
import { useApiQuery } from "@/hooks";
import { useUrlPagination } from "@/hooks/system/useUrlPagination";
import { apiResponseSchema } from "@/types/api.types";
import {
  LiquidacionGeneralOutputSchema,
  LiquidacionTipoOutputSchema,
  paginatedResponseSchema,
} from "../schemas/liquidacion-base.schema";

/**
 * Schema for a general list item — wraps LiquidacionGeneralOutput alongside
 * tipo_liquidacion (minimal) and liquidacion_especifica (id + numero only).
 * The general list returns this 3-field wrapper per item.
 */
export const liquidacionGeneralItemSchema = z.object({
  liquidacion_general: LiquidacionGeneralOutputSchema,
  tipo_liquidacion: LiquidacionTipoOutputSchema.nullish(),
  liquidacion_especifica: z
    .object({ id: z.string(), numero: z.coerce.number().int() })
    .nullish(),
});

/** Item de liquidación general — defined explicitly to avoid Zod inference quirks */
export interface LiquidacionGeneralItem {
  liquidacion_general: {
    id: string;
    estado?: string | null | undefined;
    municipalidad?: { id: string; codigo: string | null; nombre: string } | null | undefined;
    usuario_creador?: { id: string; nombres: string | null; apellidos: string | null; email: string | null; dni: string | null; username: string | null } | null | undefined;
    fecha_registro: string;
    expediente?: string | null | undefined;
    observacion?: string | null | undefined;
    numero_revision: number;
    sub_total: number;
    total: number;
    retencion?: boolean;
    legacy?: boolean;
    codigo_cta?: string | null | undefined;
    igv?: { id: string; valor: number; periodo_inicio: string | null } | null | undefined;
    uit?: { id: string; valor: number; periodo_inicio: string | null } | null | undefined;
    proyecto: {
      id: string;
      nombre_propietario: string;
      direccion: string;
      urbanizacion?: string | null | undefined;
      distrito?: { id: string; nombre: string; ubigeo: string | null; provincia?: { id: string; nombre: string } | null | undefined; departamento?: { id: string; nombre: string } | null | undefined } | null | undefined;
      entidad?: { tipo_documento: string; numero_documento: string; razon_social: string } | null | undefined;
    };
    denominacion_de_proyecto?: string | null | undefined;
    contacto?: { id: string; nombres: string | null; apellidos: string | null; dni: string | null; cargo: string | null; telefono: string | null; celular: string | null; email: string | null } | null | undefined;
    tipo_liquidacion?: { codigo: string | null; nombre: string | null } | null | undefined;
    delegados: Array<{
      datos: { periodo?: number | null | undefined; mes?: number | null | undefined; dictamen_revision?: string | null | undefined; fecha_presentacion?: string | null | undefined; fecha_revision?: string | null | undefined };
      delegado: { id: string; nombre_completo: string; cip: string; tipo: string; especialidad: { id: string; nombre: string } };
    }>;
    comprobantes: Array<{ id: string; tipo_comprobante?: string | null | undefined; serie?: string | null | undefined; numero?: string | null | undefined; fecha_emision?: string | null | undefined; monto?: number | null | undefined; activo: boolean; motivo_reemplazo?: string | null | undefined }>;
    eliminado?: boolean;
  };
  tipo_liquidacion?: { codigo?: string | null | undefined; nombre?: string | null | undefined } | null | undefined;
  liquidacion_especifica?: { id: string; numero: number } | null | undefined;
}

const paginatedSchema = apiResponseSchema(
  paginatedResponseSchema(liquidacionGeneralItemSchema),
);

interface UseLiquidacionesGeneralesProps {
  tipo?: string;
  documento?: string;
  razonSocial?: string;
  propietario?: string;
  /** Filter by liquidacion numero (autoincremental per type, independent sequences across types) */
  numero?: number;
  enabled?: boolean;
  /** true → usa GET /ultimas-revisiones (solo la última revisión por proyecto+tipo) */
  soloUltimasRevisiones?: boolean;
}

export function useLiquidacionesGenerales({
  tipo,
  documento,
  razonSocial,
  propietario,
  numero,
  enabled = true,
  soloUltimasRevisiones = false,
}: UseLiquidacionesGeneralesProps = {}) {
  const { page, pageSize, setPage, setPageSize, resetPagination } =
    useUrlPagination();

  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (tipo) params.tipo = tipo;
  if (documento) params.documento = documento;
  if (razonSocial) params.razon_social = razonSocial;
  if (propietario) params.propietario = propietario;
  if (numero !== undefined) params.numero = numero;

  const {
    data: rawData,
    isLoading,
    isError,
    refetch,
  } = useApiQuery({
    queryKey: [
      "liquidaciones",
      "generales",
      soloUltimasRevisiones ? "ultimas-revisiones" : "todas",
      page,
      pageSize,
      tipo,
      documento,
      razonSocial,
      propietario,
      numero,
    ],
    url: soloUltimasRevisiones
      ? "/liquidaciones/generales/ultimas-revisiones"
      : "/liquidaciones/generales",
    schema: paginatedSchema,
    params,
    queryOptions: {
      enabled,
    },
  });

  const paginatedData = rawData?.data;
  const items = (paginatedData?.items ?? []) as LiquidacionGeneralItem[];
  const total: number = paginatedData?.total ?? 0;
  const totalPages: number = paginatedData?.total_pages ?? 1;

  return {
    items,
    total,
    page,
    pageSize,
    totalPages,
    setPage,
    setPageSize,
    resetPagination,
    isLoading,
    isError,
    refetch,
  };
}
