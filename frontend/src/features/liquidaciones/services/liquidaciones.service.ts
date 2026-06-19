/**
 * Servicios API para Liquidaciones Edificaciones.
 */
import api from "@/lib/api";
import type {
  PaginatedLiquidaciones,
  PrimeraRevisionFormData,
  VariablesFinancieras,
  LiquidacionSnapshot,
  CotizacionQuote,
  NuevaRevisionFormularioResponse,
  NuevaRevisionFormData,
} from "../types/liquidacion-edificaciones";

const BASE_URL = "/liquidaciones/edificaciones";

export const liquidacionesService = {
  /**
   * Lista liquidaciones con paginación.
   */
  async listarLiquidaciones(params: {
    page: number;
    page_size: number;
  }): Promise<PaginatedLiquidaciones> {
    const { data } = await api.get(BASE_URL, { params });
    return data.data as PaginatedLiquidaciones;
  },

  /**
   * Crea primera revisión de liquidación.
   */
  async crearPrimeraRevision(
    payload: PrimeraRevisionFormData,
  ): Promise<{ data: LiquidacionSnapshot }> {
    const { data } = await api.post(`${BASE_URL}/primera-revision`, {
      liquidacion: payload,
    });
    return data as { data: LiquidacionSnapshot };
  },

  /**
   * Obtiene detalle de una liquidación.
   */
  async obtenerLiquidacion(
    liquidacionId: string,
  ): Promise<{ data: LiquidacionSnapshot }> {
    const { data } = await api.get(`${BASE_URL}/${liquidacionId}`);
    return data as { data: LiquidacionSnapshot };
  },

  /**
   * Cotiza primera revisión sin guardar en BD.
   */
  async cotizarPrimeraRevision(payload: {
    proyecto_public_id: string;
    valor_proyecto: number;
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
   */
  async crearNuevaRevision(
    payload: NuevaRevisionFormData,
  ): Promise<{ data: LiquidacionSnapshot }> {
    const { data } = await api.post(`${BASE_URL}/nueva-revision`, payload);
    return data as { data: LiquidacionSnapshot };
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