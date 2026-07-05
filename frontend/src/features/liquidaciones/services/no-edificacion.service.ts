/**
 * Servicios API para Liquidaciones No Edificación.
 * Endpoints: POST /liquidaciones/{kind}/primera-revision
 *            POST /liquidaciones/{kind}/cotizar/primera-revision
 * Kinds: habilitacion-urbana, mecanica-suelos, impacto-vial, taludes, inspeccion-obra
 */
import api from "@/lib/api";
import type {
  CotizarInspeccionObraPrimeraRevisionIn,
  CotizarM2PrimeraRevisionIn,
  CotizacionNoEdificacionResponse,
  CrearLiquidacionInspeccionObraIn,
  LiquidacionKind,
  LiquidacionM2BaseIn,
  LiquidacionM2Kind,
} from "../types/liquidacion-no-edificacion.types";

/**
 * Construye la URL base para un tipo de liquidación.
 * @param kind - Tipo de liquidación (ej: "habilitacion-urbana")
 */
function getBaseUrl(kind: LiquidacionKind): string {
  return `/liquidaciones/${kind}`;
}

// ── Tipos de respuesta ────────────────────────────────────────────────────────

/**
 * Respuesta de creación de liquidación no-edificación.
 * Estructura similar a Liquidacion de edificación.
 */
export interface CrearLiquidacionNoEdificacionResponse {
  liquidacion: {
    id: string;
    public_id: string;
    estado: string;
    fecha_creacion: string;
    expediente: string | null;
    observacion: string | null;
  };
  totales: {
    subtotal: number;
    igv: number;
    total: number;
    liquidacion_total: number;
    total_a_pagar: number;
  };
}

// ── Servicio ────────────────────────────────────────────────────────────────

export const noEdificacionService = {
  /**
   * Crea una primera revisión para liquidación M2-based.
   * Válido para: Habilitación Urbana, Mecánica de Suelos, Impacto Vial, Taludes.
   *
   * @param kind - Tipo de liquidación M2
   * @param payload - Datos de la liquidación
   */
  async crearPrimeraRevisionM2(
    kind: LiquidacionM2Kind,
    payload: LiquidacionM2BaseIn,
  ): Promise<{ data: CrearLiquidacionNoEdificacionResponse }> {
    const { data } = await api.post(`${getBaseUrl(kind)}/primera-revision`, {
      liquidacion: payload,
    });
    return data as { data: CrearLiquidacionNoEdificacionResponse };
  },

  /**
   * Crea una primera revisión para Inspección de Obra.
   *
   * @param payload - Datos de la liquidación IO
   */
  async crearPrimeraRevisionInspeccionObra(
    payload: CrearLiquidacionInspeccionObraIn,
  ): Promise<{ data: CrearLiquidacionNoEdificacionResponse }> {
    const { data } = await api.post(
      `${getBaseUrl("inspeccion-obra")}/primera-revision`,
      { liquidacion: payload },
    );
    return data as { data: CrearLiquidacionNoEdificacionResponse };
  },

  /**
   * Crea primera revisión (polimórfico según kind).
   * Dispatch interno basado en el tipo.
   */
  async crearPrimeraRevision(
    kind: LiquidacionKind,
    payload: LiquidacionM2BaseIn | CrearLiquidacionInspeccionObraIn,
  ): Promise<{ data: CrearLiquidacionNoEdificacionResponse }> {
    if (kind === "inspeccion-obra") {
      return this.crearPrimeraRevisionInspeccionObra(
        payload as CrearLiquidacionInspeccionObraIn,
      );
    }
    return this.crearPrimeraRevisionM2(
      kind as LiquidacionM2Kind,
      payload as LiquidacionM2BaseIn,
    );
  },

  /**
   * Cotiza primera revisión para liquidación M2-based.
   *
   * @param kind - Tipo de liquidación M2
   * @param payload - Payload de cotización
   */
  async cotizarPrimeraRevisionM2(
    kind: LiquidacionM2Kind,
    payload: CotizarM2PrimeraRevisionIn,
  ): Promise<CotizacionNoEdificacionResponse> {
    const { data } = await api.post(
      `${getBaseUrl(kind)}/cotizar/primera-revision`,
      { liquidacion: payload },
    );
    // useApiCreate con cotizacionNoEdificacionResponseSchema valida y retorna
    // el wrapper {success, data, error}, así que aquí retornamos data.data
    return (data as { data: CotizacionNoEdificacionResponse }).data;
  },

  /**
   * Cotiza primera revisión para Inspección de Obra.
   *
   * @param payload - Payload de cotización IO
   */
  async cotizarPrimeraRevisionInspeccionObra(
    payload: CotizarInspeccionObraPrimeraRevisionIn,
  ): Promise<CotizacionNoEdificacionResponse> {
    const { data } = await api.post(
      `${getBaseUrl("inspeccion-obra")}/cotizar/primera-revision`,
      { liquidacion: payload },
    );
    return (data as { data: CotizacionNoEdificacionResponse }).data;
  },

  /**
   * Cotiza primera revisión (polimórfico según tipo en payload).
   */
  async cotizarPrimeraRevision(
    payload:
      | (CotizarM2PrimeraRevisionIn & { tipo_liquidacion: LiquidacionM2Kind })
      | (CotizarInspeccionObraPrimeraRevisionIn & { tipo_liquidacion: "inspeccion-obra" }),
  ): Promise<CotizacionNoEdificacionResponse> {
    if (payload.tipo_liquidacion === "inspeccion-obra") {
      const ioPayload = payload as CotizarInspeccionObraPrimeraRevisionIn & {
        tipo_liquidacion: "inspeccion-obra";
      };
      return this.cotizarPrimeraRevisionInspeccionObra({
        cantidad_visitas: ioPayload.cantidad_visitas,
        categoria: ioPayload.categoria,
        municipalidad_id: ioPayload.municipalidad_id,
        tarifas_ids: ioPayload.tarifas_ids,
      });
    }
    const m2Payload = payload as CotizarM2PrimeraRevisionIn & {
      tipo_liquidacion: LiquidacionM2Kind;
    };
    return this.cotizarPrimeraRevisionM2(m2Payload.tipo_liquidacion, {
      tipo_liquidacion: m2Payload.tipo_liquidacion,
      area_solicitada: m2Payload.area_solicitada,
      municipalidad_id: m2Payload.municipalidad_id,
      tarifas_ids: m2Payload.tarifas_ids,
    });
  },
};
