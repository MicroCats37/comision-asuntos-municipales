/**
 * Servicios API para Taludes.
 * Endpoint base: /liquidaciones/taludes
 */
import api from "@/lib/api";
import type {
  CotizacionTaludesResponse,
  CrearTaludesPrimeraRevisionIn,
  CrearTaludesResponse,
  LiquidacionesTaludesPaginated,
  TarifaVigenteTaludes,
} from "../types/liquidacion-taludes.types";
import type { CotizarTaludesPrimeraRevisionIn } from "../types/liquidacion-taludes.types";
import { cotizacionTaludesResponseSchema } from "../schemas/liquidacion-taludes.schema";
import { crearTaludesResponseSchema } from "../schemas/liquidacion-taludes.schema";
import { liquidacionesTaludesResponseSchema } from "../schemas/liquidacion-taludes.schema";
import { tarifasVigentesTaludesResponseSchema } from "../schemas/liquidacion-taludes.schema";
import type { LiquidacionGeneralOut } from "../types/liquidacion-general";

const BASE_URL = "/liquidaciones/taludes";

export const taludesService = {
  /**
   * Lista liquidaciones de Taludes con paginación.
   * Endpoint: GET /liquidaciones/taludes
   */
  async listarLiquidaciones(params: {
    page: number;
    page_size: number;
  }): Promise<LiquidacionesTaludesPaginated> {
    const { data } = await api.get(BASE_URL, { params });
    return (data as { data: LiquidacionesTaludesPaginated }).data;
  },

  /**
   * Crea primera revisión de Taludes.
   * Endpoint: POST /liquidaciones/taludes/primera-revision
   */
  async crearPrimeraRevision(
    payload: CrearTaludesPrimeraRevisionIn,
  ): Promise<CrearTaludesResponse> {
    const { data } = await api.post(`${BASE_URL}/primera-revision`, {
      liquidacion: payload,
    });
    return (data as { data: CrearTaludesResponse }).data;
  },

  /**
   * Cotiza primera revisión de Taludes.
   * Endpoint: POST /liquidaciones/taludes/cotizar/primera-revision
   */
  async cotizarPrimeraRevision(
    payload: CotizarTaludesPrimeraRevisionIn,
  ): Promise<CotizacionTaludesResponse> {
    const { data } = await api.post(`${BASE_URL}/cotizar/primera-revision`, {
      liquidacion: payload,
    });
    return (data as { data: CotizacionTaludesResponse }).data;
  },

  /**
   * Obtiene detalle de una liquidación.
   * Endpoint: GET /liquidaciones/taludes/{id}
   */
  async obtenerLiquidacion(
    liquidacionId: string,
  ): Promise<LiquidacionGeneralOut> {
    const { data } = await api.get(`${BASE_URL}/${liquidacionId}`);
    return (data as { data: LiquidacionGeneralOut }).data;
  },

  /**
   * Obtiene tarifas vigentes para Taludes.
   * Endpoint: GET /liquidaciones/taludes/tarifas-vigentes
   */
  async obtenerTarifasVigentes(): Promise<TarifaVigenteTaludes[]> {
    const { data } = await api.get(`${BASE_URL}/tarifas-vigentes`);
    const tarifas = (data as { data: { tarifas: TarifaVigenteTaludes[] } }).data.tarifas;
    return tarifas;
  },
};
