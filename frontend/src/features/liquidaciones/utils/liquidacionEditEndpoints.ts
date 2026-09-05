/**
 * Endpoint mapping for liquidacion PATCH calls by tipo.
 * Matches backend routes:
 *   PATCH /liquidaciones/edificaciones/{id}
 *   PATCH /liquidaciones/impacto-vial/{id}
 *   PATCH /liquidaciones/taludes/{id}
 *   PATCH /liquidaciones/habilitacion-urbana/{id}
 *   PATCH /liquidaciones/mecanica-suelos/{id}
 *   PATCH /liquidaciones/inspeccion-obra/{id}
 */
export const LIQUIDACION_EDIT_ENDPOINTS = {
  edificacion: "/liquidaciones/edificaciones",
  "impacto-vial": "/liquidaciones/impacto-vial",
  taludes: "/liquidaciones/taludes",
  "habilitacion-urbana": "/liquidaciones/habilitacion-urbana",
  "mecanica-suelos": "/liquidaciones/mecanica-suelos",
  "inspeccion-obra": "/liquidaciones/inspeccion-obra",
} as const;

export type LiquidacionTipoClave =
  keyof typeof LIQUIDACION_EDIT_ENDPOINTS;

/**
 * Returns the PATCH endpoint base path for a given tipo clave.
 * Append the liquidacion id to build the full URL.
 */
export function getLiquidacionEditEndpoint(
  tipo: LiquidacionTipoClave,
): string {
  return LIQUIDACION_EDIT_ENDPOINTS[tipo];
}
