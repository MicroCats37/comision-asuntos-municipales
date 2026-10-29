/**
 * Espejo EXACTO del contrato de estrategias de cotización del motor PO de
 * Edificaciones.
 *
 * Backend (fuente de verdad):
 *   `backend/modules/liquidaciones/presentation/schemas/liquidacion_especifico/
 *    liquidacion_edificaciones_schemas.py` → union discriminada SOLO de
 *    Edificaciones.
 *
 * Hay exactamente TRES estrategias (no hay alias ni cuarto modo):
 *   - `NORMAL_SELECCIONADAS`: `datos.valor_declarado` + participantes. El
 *     discriminador es OPCIONAL en el backend (el payload vigente queda
 *     byte-compatible); aquí se materializa siempre para que el payload sea
 *     explícito.
 *   - `TARIFA_HABILITADAS_PARTICIPANTES`: `datos.valor_declarado` +
 *     participantes. El discriminador es OBLIGATORIO: H (habilitadas) lo
 *     resuelve el catálogo, nunca el cliente.
 *   - `TOTAL_EXPLICITO`: `datos.total_explicito` + participantes. El
 *     discriminador es OBLIGATORIO y `valor_declarado` está PROHIBIDO (el
 *     total con IGV es autoritativo y el backend extrae el subtotal).
 *
 * Cada variante es `strict` (equivalente a `extra="forbid"` en el backend):
 * un payload mixto (campos de dos estrategias), incompleto o con campos
 * prohibidos se rechaza.
 *
 * Taludes, Impacto Vial, edge y legacy NO usan estrategias: sus schemas no se
 * tocan (contrato SCHEMA_DRY_INTENTION).
 */
import { z } from "zod";
import { toFiniteNumber } from "../utils/toFiniteNumber";

// ── Constantes canónicas ────────────────────────────────────────────────────

export const ESTRATEGIA_NORMAL = "NORMAL_SELECCIONADAS";
export const ESTRATEGIA_HABILITADAS = "TARIFA_HABILITADAS_PARTICIPANTES";
export const ESTRATEGIA_TOTAL = "TOTAL_EXPLICITO";

/** Las TRES estrategias canónicas, en el orden del enum del backend. */
export const ESTRATEGIAS_COTIZACION_PO = [
  ESTRATEGIA_NORMAL,
  ESTRATEGIA_HABILITADAS,
  ESTRATEGIA_TOTAL,
] as const;

export type EstrategiaCotizacionPO = (typeof ESTRATEGIAS_COTIZACION_PO)[number];

/** Etiquetas legibles (mismo texto que el `verbose_name` del enum backend). */
export const ESTRATEGIA_COTIZACION_LABELS: Record<
  EstrategiaCotizacionPO,
  string
> = {
  [ESTRATEGIA_NORMAL]: "Normal - seleccionadas",
  [ESTRATEGIA_HABILITADAS]: "1 o 2 especialidades",
  [ESTRATEGIA_TOTAL]: "Plantas Típicas",
};

/** Descripción corta del alcance de cada estrategia (ayuda contextual). */
export const ESTRATEGIA_COTIZACION_DESCRIPCIONES: Record<
  EstrategiaCotizacionPO,
  string
> = {
  [ESTRATEGIA_NORMAL]:
    "Cotiza según las especialidades seleccionadas y distribuye el importe proporcionalmente entre ellas.",
  [ESTRATEGIA_HABILITADAS]:
    "La liquidación conserva el 0.15% y distribuye el importe entre una o dos especialidades.",
  [ESTRATEGIA_TOTAL]:
    "Para liquidaciones convencionales de plantas típicas, ingresando directamente el total final.",
};

export const estrategiaCotizacionSchema = z.enum(ESTRATEGIAS_COTIZACION_PO);

/** `true` si el valor es una de las TRES estrategias canónicas. */
export function esEstrategiaValida(
  valor: unknown,
): valor is EstrategiaCotizacionPO {
  return (
    typeof valor === "string" &&
    (ESTRATEGIAS_COTIZACION_PO as readonly string[]).includes(valor)
  );
}

/** Máximo compatible con `DecimalField(max_digits=12, decimal_places=2)`. */
export const VALOR_MAXIMO_PORCENTAJE_OBRA = 9999999999.99;

// ── Mensajes de validación (compartidos con el schema del formulario) ──────

export const MENSAJE_VALOR_DECLARADO_REQUERIDO =
  "El valor declarado es requerido";
export const MENSAJE_VALOR_DECLARADO_POSITIVO =
  "El valor declarado debe ser positivo";
export const MENSAJE_VALOR_DECLARADO_MAXIMO =
  "El valor declarado excede el máximo permitido";
export const MENSAJE_VALOR_DECLARADO_NUMERO =
  "El valor declarado debe ser un número válido";

export const MENSAJE_TOTAL_EXPLICITO_REQUERIDO = "El total final es requerido";
export const MENSAJE_TOTAL_EXPLICITO_POSITIVO =
  "El total final debe ser positivo";
export const MENSAJE_TOTAL_EXPLICITO_MAXIMO =
  "El total final excede el máximo permitido";
export const MENSAJE_TOTAL_EXPLICITO_NUMERO =
  "El total final debe ser un número válido";

// ── Schemas Zod ─────────────────────────────────────────────────────────────

/** `tarifas[]` — participante = (tarifa vigente, especialidad). */
export const estrategiaTarifaSchema = z.strictObject({
  tarifa_porcentaje_obra_id: z.string(),
  especialidad_id: z.string(),
});
export type EstrategiaTarifa = z.infer<typeof estrategiaTarifaSchema>;

const valorDeclaradoNumero = z
  .number({
    error: (issue) =>
      issue.input === undefined || issue.input === null || issue.input === ""
        ? MENSAJE_VALOR_DECLARADO_REQUERIDO
        : MENSAJE_VALOR_DECLARADO_NUMERO,
  })
  .positive(MENSAJE_VALOR_DECLARADO_POSITIVO)
  .max(VALOR_MAXIMO_PORCENTAJE_OBRA, MENSAJE_VALOR_DECLARADO_MAXIMO)
  .finite(MENSAJE_VALOR_DECLARADO_NUMERO);

const totalExplicitoNumero = z
  .number({
    error: (issue) =>
      issue.input === undefined || issue.input === null || issue.input === ""
        ? MENSAJE_TOTAL_EXPLICITO_REQUERIDO
        : MENSAJE_TOTAL_EXPLICITO_NUMERO,
  })
  .positive(MENSAJE_TOTAL_EXPLICITO_POSITIVO)
  .max(VALOR_MAXIMO_PORCENTAJE_OBRA, MENSAJE_TOTAL_EXPLICITO_MAXIMO)
  .finite(MENSAJE_TOTAL_EXPLICITO_NUMERO);

/** `datos` de NORMAL_SELECCIONADAS: valor declarado del proyecto. */
export const estrategiaNormalDatosSchema = z.strictObject({
  valor_declarado: valorDeclaradoNumero,
  tipo_tramite: z.string().optional(),
});

/** `datos` de TARIFA_HABILITADAS_PARTICIPANTES: valor declarado del proyecto. */
export const estrategiaHabilitadasDatosSchema = z.strictObject({
  valor_declarado: valorDeclaradoNumero,
  tipo_tramite: z.string().optional(),
});

/** `datos` de TOTAL_EXPLICITO: valor informativo y total final autoritativo. */
export const estrategiaTotalExplicitoDatosSchema = z.strictObject({
  valor_declarado: valorDeclaradoNumero,
  total_explicito: totalExplicitoNumero,
  tipo_tramite: z.string().optional(),
});

export const estrategiaNormalInSchema = z.strictObject({
  estrategia_cotizacion: z.literal(ESTRATEGIA_NORMAL),
  datos: estrategiaNormalDatosSchema,
  tipo_tramite: z.string().optional(),
  tarifas: z.array(estrategiaTarifaSchema).default([]),
});

export const estrategiaHabilitadasInSchema = z.strictObject({
  estrategia_cotizacion: z.literal(ESTRATEGIA_HABILITADAS),
  datos: estrategiaHabilitadasDatosSchema,
  tipo_tramite: z.string().optional(),
  tarifas: z.array(estrategiaTarifaSchema).default([]),
});

export const estrategiaTotalExplicitoInSchema = z.strictObject({
  estrategia_cotizacion: z.literal(ESTRATEGIA_TOTAL),
  datos: estrategiaTotalExplicitoDatosSchema,
  tipo_tramite: z.string().optional(),
  tarifas: z.array(estrategiaTarifaSchema).default([]),
});

/**
 * Union discriminada de estrategias — espejo exacto de
 * `LiquidacionEdificacionesEstrategiaIn` del backend.
 */
export const edificacionesEstrategiaSchema = z.discriminatedUnion(
  "estrategia_cotizacion",
  [
    estrategiaNormalInSchema,
    estrategiaHabilitadasInSchema,
    estrategiaTotalExplicitoInSchema,
  ],
);

export type EstrategiaNormalPayload = z.infer<typeof estrategiaNormalInSchema>;
export type EstrategiaHabilitadasPayload = z.infer<
  typeof estrategiaHabilitadasInSchema
>;
export type EstrategiaTotalExplicitoPayload = z.infer<
  typeof estrategiaTotalExplicitoInSchema
>;
export type EstrategiaPayload =
  | EstrategiaNormalPayload
  | EstrategiaHabilitadasPayload
  | EstrategiaTotalExplicitoPayload;

// ── Normalización y parsing ─────────────────────────────────────────────────

/**
 * Materializa el discriminador cuando el payload no lo trae.
 *
 * Espejo del backend: el discriminador es opcional únicamente para
 * `NORMAL_SELECCIONADAS`, de modo que el payload vigente (modo normal)
 * permanece byte-compatible. Cualquier otro valor ausente se interpreta como
 * NORMAL y la union lo rechaza si los datos no corresponden.
 */
export function normalizarPayloadEstrategia<T extends Record<string, unknown>>(
  payload: T,
): T & { estrategia_cotizacion: EstrategiaCotizacionPO } {
  const discriminador = payload.estrategia_cotizacion;
  if (
    typeof discriminador === "string" &&
    (ESTRATEGIAS_COTIZACION_PO as readonly string[]).includes(discriminador)
  ) {
    return payload as T & { estrategia_cotizacion: EstrategiaCotizacionPO };
  }
  return {
    ...payload,
    estrategia_cotizacion: ESTRATEGIA_NORMAL,
  };
}

/** Parsea un payload de estrategia aplicando la normalización previa. */
export function parsePayloadEstrategia(payload: unknown) {
  return edificacionesEstrategiaSchema.parse(
    normalizarPayloadEstrategia((payload ?? {}) as Record<string, unknown>),
  );
}

// ── Builder del payload discriminado ───────────────────────────────────────

export interface EstrategiaPayloadInput {
  estrategia: EstrategiaCotizacionPO;
  valor_declarado?: number | null;
  total_explicito?: number | null;
  tipo_tramite?: string | null;
  tarifas?: EstrategiaTarifa[];
}

/**
 * Construye el payload discriminado exacto que espera el backend.
 *
 * Todas las estrategias envían `datos.valor_declarado`. TOTAL_EXPLICITO añade
 * `datos.total_explicito`, que es el único dato usado por las fórmulas.
 *
 * `tipo_tramite` viaja en el nivel de la variante (es donde lo lee el
 * orquestador del backend) y no dentro de `datos`.
 */
export function construirEstrategiaPayload(
  input: EstrategiaPayloadInput,
): EstrategiaPayload {
  const tarifas = input.tarifas ?? [];
  const tipoTramite = input.tipo_tramite ?? undefined;
  // Barrera final: una estrategia desconocida NUNCA se envía — se degrada a
  // NORMAL_SELECCIONADAS (el modo vigente y el único que el backend acepta
  // como discriminador ausente).
  const estrategia = esEstrategiaValida(input.estrategia)
    ? input.estrategia
    : ESTRATEGIA_NORMAL;

  if (estrategia === ESTRATEGIA_TOTAL) {
    return {
      estrategia_cotizacion: ESTRATEGIA_TOTAL,
      ...(tipoTramite ? { tipo_tramite: tipoTramite } : {}),
      datos: {
        valor_declarado: Number(input.valor_declarado ?? 0),
        total_explicito: Number(input.total_explicito ?? 0),
      },
      tarifas,
    };
  }

  return {
    estrategia_cotizacion: estrategia,
    ...(tipoTramite ? { tipo_tramite: tipoTramite } : {}),
    datos: { valor_declarado: Number(input.valor_declarado ?? 0) },
    tarifas,
  };
}

// ── Lectura segura desde un form data heterogéneo ───────────────────────────

export interface EstrategiaFormDataLectura {
  estrategia_cotizacion?: EstrategiaCotizacionPO;
  valor_declarado?: number;
  total_explicito?: number;
}

/**
 * Lee los campos de estrategia desde un form data heterogéneo.
 *
 * El formulario de Edificaciones tiene estrategia, valor declarado y total
 * explícito; los de Taludes e Impacto Vial no tienen ninguno de ellos. Esta
 * lectura evita castear el union `POFormData` y devuelve solo lo que existe.
 */
export function leerEstrategiaFormData(
  data: unknown,
): EstrategiaFormDataLectura {
  if (typeof data !== "object" || data === null) return {};
  const registro = data as Record<string, unknown>;

  const estrategia = registro.estrategia_cotizacion;
  const valorDeclarado = toFiniteNumber(registro.valor_declarado);
  const totalExplicito = toFiniteNumber(registro.total_explicito);

  return {
    ...(esEstrategiaValida(estrategia)
      ? { estrategia_cotizacion: estrategia }
      : {}),
    ...(valorDeclarado !== undefined
      ? { valor_declarado: valorDeclarado }
      : {}),
    ...(totalExplicito !== undefined
      ? { total_explicito: totalExplicito }
      : {}),
  };
}

// ── Validación por estrategia (compartida con el schema del formulario) ─────

export interface EstrategiaValidacionIssue {
  path: "valor_declarado" | "total_explicito";
  message: string;
}

/**
 * Valida el dato que exige la estrategia activa.
 *
 * El dato de la estrategia INACTIVA se ignora por completo (no se valida ni
 * se envía): es la barrera de frontend contra los payloads mixtos que el
 * backend rechaza con 400.
 */
export function validarDatosDeEstrategia(
  estrategia: EstrategiaCotizacionPO,
  datos: {
    valor_declarado?: number | null;
    total_explicito?: number | null;
  },
): EstrategiaValidacionIssue[] {
  const issues: EstrategiaValidacionIssue[] = [];
  const valor = datos.valor_declarado;
  if (valor === undefined || valor === null) {
    issues.push({
      path: "valor_declarado",
      message: MENSAJE_VALOR_DECLARADO_REQUERIDO,
    });
  } else if (typeof valor === "number" && Number.isFinite(valor)) {
    if (valor <= 0) {
      issues.push({
        path: "valor_declarado",
        message: MENSAJE_VALOR_DECLARADO_POSITIVO,
      });
    } else if (valor > VALOR_MAXIMO_PORCENTAJE_OBRA) {
      issues.push({
        path: "valor_declarado",
        message: MENSAJE_VALOR_DECLARADO_MAXIMO,
      });
    }
  }

  if (estrategia === ESTRATEGIA_TOTAL) {
    const total = datos.total_explicito;
    if (total === undefined || total === null) {
      issues.push({
        path: "total_explicito",
        message: MENSAJE_TOTAL_EXPLICITO_REQUERIDO,
      });
    } else if (typeof total === "number" && Number.isFinite(total)) {
      if (total <= 0) {
        issues.push({
          path: "total_explicito",
          message: MENSAJE_TOTAL_EXPLICITO_POSITIVO,
        });
      } else if (total > VALOR_MAXIMO_PORCENTAJE_OBRA) {
        issues.push({
          path: "total_explicito",
          message: MENSAJE_TOTAL_EXPLICITO_MAXIMO,
        });
      }
    }
    return issues;
  }
  return issues;
}
