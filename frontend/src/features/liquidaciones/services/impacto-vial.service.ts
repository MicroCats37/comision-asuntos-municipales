/**
 * Servicios API para Impacto Vial.
 * Endpoint base: /liquidaciones/impacto-vial
 */
import api from "@/lib/api";
import type {
  CotizacionImpactoVialResponse,
  CrearImpactoVialPrimeraRevisionIn,
  CrearImpactoVialResponse,
  LiquidacionesImpactoVialPaginated,
  TarifaVigenteImpactoVial,
} from "../types/liquidacion-impacto-vial.types";
import type { CotizarImpactoVialPrimeraRevisionIn } from "../types/liquidacion-impacto-vial.types";
import { cotizacionImpactoVialResponseSchema } from "../schemas/liquidacion-impacto-vial.schema";
import { crearImpactoVialResponseSchema } from "../schemas/liquidacion-impacto-vial.schema";
import { liquidacionesImpactoVialResponseSchema } from "../schemas/liquidacion-impacto-vial.schema";
import { tarifasVigentesImpactoVialResponseSchema } from "../schemas/liquidacion-impacto-vial.schema";

const BASE_URL = "/liquidaciones/impacto-vial";

export const impactoVialService = {
  /**
   * Lista liquidaciones de Impacto Vial con paginación.
   * Endpoint: GET /liquidaciones/impacto-vial
   */
  async listarLiquidaciones(params: {
    page: number;
    page_size: number;
  }): Promise<LiquidacionesImpactoVialPaginated> {
    const { data } = await api.get(BASE_URL, { params });
    return (data as { data: LiquidacionesImpactoVialPaginated }).data;
  },

  /**
   * Crea primera revisión de Impacto Vial.
   * Endpoint: POST /liquidaciones/impacto-vial/primera-revision
   */
  async crearPrimeraRevision(
    payload: CrearImpactoVialPrimeraRevisionIn,
  ): Promise<CrearImpactoVialResponse> {
    const { data } = await api.post(`${BASE_URL}/primera-revision`, {
      liquidacion: payload,
    });
    return (data as { data: CrearImpactoVialResponse }).data;
  },

  /**
   * Cotiza primera revisión de Impacto Vial.
   * Endpoint: POST /liquidaciones/impacto-vial/cotizar/primera-revision
   */
  async cotizarPrimeraRevision(
    payload: CotizarImpactoVialPrimeraRevisionIn,
  ): Promise<CotizacionImpactoVialResponse> {
    const { data } = await api.post(`${BASE_URL}/cotizar/primera-revision`, {
      liquidacion: payload,
    });
    return (data as { data: CotizacionImpactoVialResponse }).data;
  },

  /**
   * Obtiene detalle de una liquidación.
   * Endpoint: GET /liquidaciones/impacto-vial/{id}
   */
  async obtenerLiquidacion(
    liquidacionId: string,
  ): Promise<CrearImpactoVialResponse> {
    const { data } = await api.get(`${BASE_URL}/${liquidacionId}`);
    return (data as { data: CrearImpactoVialResponse }).data;
  },

  /**
   * Obtiene tarifas vigentes para Impacto Vial.
   * Endpoint: GET /liquidaciones/impacto-vial/tarifas-vigentes
   */
  async obtenerTarifasVigentes(): Promise<TarifaVigenteImpactoVial[]> {
    const { data } = await api.get(`${BASE_URL}/tarifas-vigentes`);
    const tarifas = (data as { data: { tarifas: TarifaVigenteImpactoVial[] } }).data.tarifas;
    return tarifas;
  },
};
