/**
 * Servicios API para Mecánica de Suelos.
 * Endpoint base: /liquidaciones/mecanica-suelos
 */
import api from "@/lib/api";
import type {
  CotizacionMecanicaSuelosResponse,
  CrearMecanicaSuelosPrimeraRevisionIn,
  CrearMecanicaSuelosResponse,
  LiquidacionesMecanicaSuelosPaginated,
  TarifaVigenteMecanicaSuelos,
} from "../types/liquidacion-mecanica-suelos.types";
import type { CotizarMecanicaSuelosPrimeraRevisionIn } from "../types/liquidacion-mecanica-suelos.types";
import { cotizacionMecanicaSuelosResponseSchema } from "../schemas/liquidacion-mecanica-suelos.schema";
import { crearMecanicaSuelosResponseSchema } from "../schemas/liquidacion-mecanica-suelos.schema";
import { liquidacionesMecanicaSuelosResponseSchema } from "../schemas/liquidacion-mecanica-suelos.schema";
import { tarifasVigentesMecanicaSuelosResponseSchema } from "../schemas/liquidacion-mecanica-suelos.schema";
import type { LiquidacionGeneralOut } from "../types/liquidacion-general";

const BASE_URL = "/liquidaciones/mecanica-suelos";

export const mecanicaSuelosService = {
  /**
   * Lista liquidaciones de Mecánica de Suelos con paginación.
   * Endpoint: GET /liquidaciones/mecanica-suelos
   */
  async listarLiquidaciones(params: {
    page: number;
    page_size: number;
  }): Promise<LiquidacionesMecanicaSuelosPaginated> {
    const { data } = await api.get(BASE_URL, { params });
    return (data as { data: LiquidacionesMecanicaSuelosPaginated }).data;
  },

  /**
   * Crea primera revisión de Mecánica de Suelos.
   * Endpoint: POST /liquidaciones/mecanica-suelos/primera-revision
   */
  async crearPrimeraRevision(
    payload: CrearMecanicaSuelosPrimeraRevisionIn,
  ): Promise<CrearMecanicaSuelosResponse> {
    const { data } = await api.post(`${BASE_URL}/primera-revision`, {
      liquidacion: payload,
    });
    return (data as { data: CrearMecanicaSuelosResponse }).data;
  },

  /**
   * Cotiza primera revisión de Mecánica de Suelos.
   * Endpoint: POST /liquidaciones/mecanica-suelos/cotizar/primera-revision
   */
  async cotizarPrimeraRevision(
    payload: CotizarMecanicaSuelosPrimeraRevisionIn,
  ): Promise<CotizacionMecanicaSuelosResponse> {
    const { data } = await api.post(`${BASE_URL}/cotizar/primera-revision`, {
      liquidacion: payload,
    });
    return (data as { data: CotizacionMecanicaSuelosResponse }).data;
  },

  /**
   * Obtiene detalle de una liquidación.
   * Endpoint: GET /liquidaciones/mecanica-suelos/{id}
   */
  async obtenerLiquidacion(
    liquidacionId: string,
  ): Promise<LiquidacionGeneralOut> {
    const { data } = await api.get(`${BASE_URL}/${liquidacionId}`);
    return (data as { data: LiquidacionGeneralOut }).data;
  },

  /**
   * Obtiene tarifas vigentes para Mecánica de Suelos.
   * Endpoint: GET /liquidaciones/mecanica-suelos/tarifas-vigentes
   */
  async obtenerTarifasVigentes(): Promise<TarifaVigenteMecanicaSuelos[]> {
    const { data } = await api.get(`${BASE_URL}/tarifas-vigentes`);
    const tarifas = (data as { data: { tarifas: TarifaVigenteMecanicaSuelos[] } }).data.tarifas;
    return tarifas;
  },
};
