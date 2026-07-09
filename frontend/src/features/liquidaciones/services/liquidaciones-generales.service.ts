/**
 * Servicios API para Liquidaciones GENERALES.
 */
import api from "@/lib/api";
import type {
  LiquidacionGeneralListItem,
  PaginatedLiquidacionesGenerales,
} from "../types/liquidacion-general";
import type { EspecialidadBasica } from "../types/revisiones-vigentes";

const BASE_URL = "/liquidaciones";

export interface EspecialidadesCatalogoResponse {
  items: EspecialidadBasica[];
}

export const liquidacionesGeneralesService = {
  /**
   * Lista liquidaciones GENERALES con paginación.
   * Endpoint: GET /liquidaciones
   * Retorna LiquidacionGeneralListItemOut (backend Phase 4+).
   */
  async listarLiquidaciones(params: {
    page: number;
    page_size: number;
  }): Promise<PaginatedLiquidacionesGenerales> {
    const { data } = await api.get(BASE_URL, { params });
    return data.data as PaginatedLiquidacionesGenerales;
  },

  /**
   * Obtiene especialidades vigentes para un tipo de liquidación.
   * Endpoint: GET /liquidaciones/especialidades-vigentes?tipo_liquidacion=...
   */
  async obtenerEspecialidadesVigentesLiquidacion(params: {
    tipo_liquidacion: string;
  }): Promise<EspecialidadesCatalogoResponse> {
    const { data } = await api.get(`${BASE_URL}/especialidades-vigentes`, { params });
    return data.data as EspecialidadesCatalogoResponse;
  },
};
