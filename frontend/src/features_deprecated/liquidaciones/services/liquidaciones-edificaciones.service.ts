/**
 * Servicios API para Liquidaciones Edificaciones.
 */
import api from "@/lib/api";
import type {
  CotizacionQuote,
  LiquidacionEdificacionOut,
  NuevaRevisionFormData,
  NuevaRevisionFormularioResponse,
  PaginatedLiquidacionesEdificaciones,
  PrimeraRevisionFormData,
  VariablesFinancieras,
} from "../types/liquidacion-edificaciones";

const BASE_URL = "/liquidaciones/edificaciones";

export const liquidacionesEdificacionesService = {
  /**
   * Lista liquidaciones de edificaciones con paginación.
   * El endpoint GET /liquidaciones/edificaciones retorna LiquidacionEdificacionOut
   * completo en cada item de la lista (backend Phase 4+).
   */
  async listarLiquidaciones(params: {
    page: number;
    page_size: number;
  }): Promise<PaginatedLiquidacionesEdificaciones> {
    const { data } = await api.get(BASE_URL, { params });
    return data.data as PaginatedLiquidacionesEdificaciones;
  },

  /**
   * Crea primera revisión de liquidación.
   * Retorna LiquidacionEdificacionOut plano (backend Phase 4+).
   */
  async crearPrimeraRevision(
    payload: PrimeraRevisionFormData,
  ): Promise<LiquidacionEdificacionOut> {
    const { data } = await api.post(`${BASE_URL}/primera-revision`, {
      liquidacion: payload,
    });
    return (data as { data: LiquidacionEdificacionOut }).data;
  },

  /**
   * Obtiene detalle de una liquidación.
   * Retorna LiquidacionEdificacionOut plano (backend Phase 4+).
   */
  async obtenerLiquidacion(
    liquidacionId: string,
  ): Promise<LiquidacionEdificacionOut> {
    const { data } = await api.get(`${BASE_URL}/${liquidacionId}`);
    return (data as { data: LiquidacionEdificacionOut }).data;
  },

  /**
   * Cotiza primera revisión sin guardar en BD.
   * Ahora acepta tarifas_ids en lugar de proyecto_public_id para el cálculo.
   */
  async cotizarPrimeraRevision(payload: {
    proyecto_public_id: string;
    valor_proyecto: number;
    valor_base_calculo: number;
    tarifas_ids: string[];
  }): Promise<CotizacionQuote> {
    const { data } = await api.post(`${BASE_URL}/cotizar/primera-revision`, {
      liquidacion: payload,
    });
    // Return the inner data directly — useApiCreate with cotizacionQuoteResponseSchema
    // already validates and returns the full {success, data, error} wrapper,
    // so we extract data.data here.
    return (data as { data: CotizacionQuote }).data;
  },

  /**
   * Cotiza nueva revisión sin guardar en BD.
   */
  async cotizarNuevaRevision(payload: {
    liquidacion_previa_id: string;
    revisiones_ids: string[];
  }): Promise<CotizacionQuote> {
    const { data } = await api.post(`${BASE_URL}/cotizar/nueva-revision`, {
      liquidacion_previa_id: payload.liquidacion_previa_id,
      revisiones_ids: payload.revisiones_ids,
    });
    // Return the inner data directly — useApiCreate with cotizacionQuoteResponseSchema
    // already validates and returns the full {success, data, error} wrapper,
    // so we extract data.data here.
    return (data as { data: CotizacionQuote }).data;
  },

  /**
   * Obtiene formulario para nueva revisión — retorna proyectistas_actuales.
   */
  async obtenerFormularioNuevaRevision(
    liquidacionPreviaId: string,
  ): Promise<NuevaRevisionFormularioResponse> {
    const { data } = await api.get(`${BASE_URL}/nueva-revision/formulario`, {
      params: { liquidacion_previa_id: liquidacionPreviaId },
    });
    return (data as { data: NuevaRevisionFormularioResponse }).data;
  },

  /**
   * Crea nueva revisión de liquidación.
   * Retorna LiquidacionEdificacionOut plano (backend Phase 4+).
   */
  async crearNuevaRevision(
    payload: NuevaRevisionFormData,
  ): Promise<LiquidacionEdificacionOut> {
    const { data } = await api.post(`${BASE_URL}/nueva-revision`, payload);
    return (data as { data: LiquidacionEdificacionOut }).data;
  },
};

export const finanzasService = {
  /**
   * Obtiene variables financieras vigentes (IGV/UIT).
   */
  async obtenerVariablesVigentes(): Promise<VariablesFinancieras> {
    const { data } = await api.get("/finanzas/variables/vigentes");
    return data.data as VariablesFinancieras;
  },
};
