/**
 * Servicios API para Habilitación Urbana.
 * Endpoint base: /liquidaciones/habilitacion-urbana
 */
import api from "@/lib/api";
import type {
  CotizacionHabilitacionUrbanaResponse,
  CrearHabilitacionUrbanaPrimeraRevisionIn,
  CrearHabilitacionUrbanaResponse,
  LiquidacionesHabilitacionUrbanaPaginated,
  TarifaVigenteHabilitacionUrbana,
} from "../types/liquidacion-habilitacion-urbana.types";
import type { CotizarHabilitacionUrbanaPrimeraRevisionIn } from "../types/liquidacion-habilitacion-urbana.types";
import { cotizacionHabilitacionUrbanaResponseSchema } from "../schemas/liquidacion-habilitacion-urbana.schema";
import { crearHabilitacionUrbanaResponseSchema } from "../schemas/liquidacion-habilitacion-urbana.schema";
import { liquidacionesHabilitacionUrbanaResponseSchema } from "../schemas/liquidacion-habilitacion-urbana.schema";
import { tarifasVigentesHabilitacionUrbanaResponseSchema } from "../schemas/liquidacion-habilitacion-urbana.schema";
import { liquidacionGeneralDetailResponseSchema } from "../schemas/liquidacion-general.schema";
import type { LiquidacionGeneralOut } from "../types/liquidacion-general";

const BASE_URL = "/liquidaciones/habilitacion-urbana";

export const habilitacionUrbanaService = {
  /**
   * Lista liquidaciones de Habilitación Urbana con paginación.
   * Endpoint: GET /liquidaciones/habilitacion-urbana
   */
  async listarLiquidaciones(params: {
    page: number;
    page_size: number;
  }): Promise<LiquidacionesHabilitacionUrbanaPaginated> {
    const { data } = await api.get(BASE_URL, { params });
    return (data as { data: LiquidacionesHabilitacionUrbanaPaginated }).data;
  },

  /**
   * Crea primera revisión de Habilitación Urbana.
   * Endpoint: POST /liquidaciones/habilitacion-urbana/primera-revision
   */
  async crearPrimeraRevision(
    payload: CrearHabilitacionUrbanaPrimeraRevisionIn,
  ): Promise<CrearHabilitacionUrbanaResponse> {
    const { data } = await api.post(`${BASE_URL}/primera-revision`, {
      liquidacion: payload,
    });
    return (data as { data: CrearHabilitacionUrbanaResponse }).data;
  },

  /**
   * Cotiza primera revisión de Habilitación Urbana.
   * Endpoint: POST /liquidaciones/habilitacion-urbana/cotizar/primera-revision
   */
  async cotizarPrimeraRevision(
    payload: CotizarHabilitacionUrbanaPrimeraRevisionIn,
  ): Promise<CotizacionHabilitacionUrbanaResponse> {
    const { data } = await api.post(`${BASE_URL}/cotizar/primera-revision`, {
      liquidacion: payload,
    });
    return (data as { data: CotizacionHabilitacionUrbanaResponse }).data;
  },

  /**
   * Obtiene detalle de una liquidación.
   * Endpoint: GET /liquidaciones/habilitacion-urbana/{id}
   */
  async obtenerLiquidacion(
    liquidacionId: string,
  ): Promise<LiquidacionGeneralOut> {
    const { data } = await api.get(`${BASE_URL}/${liquidacionId}`);
    return (data as { data: LiquidacionGeneralOut }).data;
  },

  /**
   * Obtiene tarifas vigentes para Habilitación Urbana.
   * Endpoint: GET /liquidaciones/habilitacion-urbana/tarifas-vigentes
   */
  async obtenerTarifasVigentes(): Promise<TarifaVigenteHabilitacionUrbana[]> {
    const { data } = await api.get(`${BASE_URL}/tarifas-vigentes`);
    const tarifas = (data as { data: { tarifas: TarifaVigenteHabilitacionUrbana[] } }).data.tarifas;
    return tarifas;
  },
};
