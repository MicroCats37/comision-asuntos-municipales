/**
 * Número de revisión de una liquidación — etiqueta EDITABLE elegida por el cliente.
 *
 * Espejo 1:1 del contrato backend:
 * - `backend/modules/liquidaciones/domain/constants.py`
 *   → `NUMERO_REVISION_PERMITIDOS`, `MAX_REVISIONES`
 * - `backend/modules/liquidaciones/presentation/schemas/liquidacion_general/general_schemas.py`
 *   → `NumeroRevisionRequeridoMixin` (obligatorio en creación/relacionada/nueva revisión)
 *   → `NumeroRevisionOpcionalMixin` (opcional en el PATCH)
 *
 * El backend NO deriva ni recalcula el número: lo recibe del cliente y lo
 * persiste tal cual. Este módulo solo replica el conjunto permitido y las
 * reglas de inicialización del formulario.
 */

/** Conjunto permitido de números de revisión (mismo orden que el backend). */
export const NUMERO_REVISION_PERMITIDOS = [1, 3, 5] as const;

export type NumeroRevision = (typeof NUMERO_REVISION_PERMITIDOS)[number];

/** Máximo de revisiones admitidas por el contrato backend. */
export const MAX_REVISIONES = 5;

/**
 * Revisión fija de los tipos sin revisión editable (Inspección de Obra).
 *
 * IO es revision-less: su contrato HTTP no expone `numero_revision` y el
 * backend mantiene su liquidación en revisión 1. Se usa también como valor
 * por defecto cuando un formulario no tiene el campo (IO).
 */
export const NUMERO_REVISION_FIJA = 1;

/** Opciones del selector de revisión (el valor es numérico, no string). */
export const NUMERO_REVISION_OPTIONS = NUMERO_REVISION_PERMITIDOS.map(
  (valor) => ({ label: `Revisión ${valor}`, value: valor }),
);

/** Indica si un valor pertenece al conjunto permitido {1, 3, 5}. */
export function esNumeroRevisionValido(
  valor: unknown,
): valor is NumeroRevision {
  return (
    typeof valor === "number" &&
    (NUMERO_REVISION_PERMITIDOS as readonly number[]).includes(valor)
  );
}

/**
 * Normaliza a número de revisión válido.
 * Acepta el `number | string` que devuelve la API y descarta lo que no está
 * en el conjunto permitido.
 */
export function toNumeroRevision(valor: unknown): NumeroRevision | undefined {
  const numero = typeof valor === "number" ? valor : Number(valor);
  if (!Number.isFinite(numero)) return undefined;
  return esNumeroRevisionValido(numero) ? numero : undefined;
}

/**
 * Calcula el valor con el que se abre el campo `numero_revision`.
 *
 * - `create` / `relacionada` → 1 (la relacionada no incrementa la revisión).
 * - `nueva-revision` → revisión de la previa + 2 (cadena 1 → 3 → 5), acotada
 *   al máximo permitido: desde una previa en revisión 5 el resultado sería 7,
 *   que no pertenece al conjunto {1, 3, 5}, así que se queda en 5.
 * - `edit` → el valor almacenado en la liquidación.
 *
 * El valor es solo el punto de partida: el usuario puede cambiarlo libremente
 * porque el número de revisión es una etiqueta editable, no una secuencia.
 */
export function resolveNumeroRevisionInicial(
  mode: "create" | "edit" | "nueva-revision" | "relacionada",
  numeroRevisionOrigen?: number | string | null,
): NumeroRevision {
  if (mode === "edit") {
    return toNumeroRevision(numeroRevisionOrigen) ?? NUMERO_REVISION_FIJA;
  }

  if (mode === "nueva-revision") {
    const origen = toNumeroRevision(numeroRevisionOrigen);
    if (origen === undefined) return NUMERO_REVISION_FIJA;
    const siguiente = Math.min(origen + 2, MAX_REVISIONES);
    return toNumeroRevision(siguiente) ?? NUMERO_REVISION_FIJA;
  }

  return NUMERO_REVISION_FIJA;
}
