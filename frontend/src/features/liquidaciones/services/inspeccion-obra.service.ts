/**
 * Servicios API para Inspección de Obra.
 * Endpoint base: /liquidaciones/inspeccion-obra
 */
import api from "@/lib/api";
import type {
  CotizacionIOResponse,
  CrearInspeccionObraPrimeraRevisionIn,
  CrearInspeccionObraResponse,
  LiquidacionesInspeccionObraPaginated,
  TarifaVigenteInspeccionObra,
} from "../types/liquidacion-inspeccion-obra.types";
import type { CotizarInspeccionObraPrimeraRevisionIn } from "../types/liquidacion-inspeccion-obra.types";
import type { LiquidacionGeneralOut } from "../types/liquidacion-general";

const BASE_URL = "/liquidaciones/inspeccion-obra";

export const inspeccionObraService = {
  /**
   * Lista liquidaciones de Inspección de Obra con paginación.
   * Endpoint: GET /liquidaciones/inspeccion-obra
   */
  async listarLiquidaciones(params: {
    page: number;
    page_size: number;
  }): Promise<LiquidacionesInspeccionObraPaginated> {
    const { data } = await api.get(BASE_URL, { params });
    return (data as { data: LiquidacionesInspeccionObraPaginated }).data;
  },

  /**
   * Crea primera revisión de Inspección de Obra.
   * Endpoint: POST /liquidaciones/inspeccion-obra/primera-revision
   */
  async crearPrimeraRevision(
    payload: CrearInspeccionObraPrimeraRevisionIn,
  ): Promise<CrearInspeccionObraResponse> {
    const { data } = await api.post(`${BASE_URL}/primera-revision`, {
      liquidacion: payload,
    });
    return (data as { data: CrearInspeccionObraResponse }).data;
  },

  /**
   * Cotiza primera revisión de Inspección de Obra.
   * Endpoint: POST /liquidaciones/inspeccion-obra/cotizar/primera-revision
   */
  async cotizarPrimeraRevision(
    payload: CotizarInspeccionObraPrimeraRevisionIn,
  ): Promise<CotizacionIOResponse> {
    const { data } = await api.post(`${BASE_URL}/cotizar/primera-revision`, {
      liquidacion: payload,
    });
    return (data as { data: CotizacionIOResponse }).data;
  },

  /**
   * Obtiene detalle de una liquidación.
   * Endpoint: GET /liquidaciones/inspeccion-obra/{id}
   */
  async obtenerLiquidacion(
    liquidacionId: string,
  ): Promise<LiquidacionGeneralOut> {
    const { data } = await api.get(`${BASE_URL}/${liquidacionId}`);
    return (data as { data: LiquidacionGeneralOut }).data;
  },

  /**
   * Obtiene tarifas vigentes para Inspección de Obra.
   * Endpoint: GET /liquidaciones/inspeccion-obra/tarifas-vigentes
   */
  async obtenerTarifasVigentes(
    params?: { categoria?: string },
  ): Promise<TarifaVigenteInspeccionObra[]> {
    const { data } = await api.get(`${BASE_URL}/tarifas-vigentes`, {
      params: params?.categoria ? { categoria: params.categoria } : undefined,
    });
    const tarifas = (data as { data: { tarifas: TarifaVigenteInspeccionObra[] } }).data.tarifas;
    return tarifas;
  },
};
