/**
 * Utilidades de UI para el `numero_rh` del RH mensual de Delegado.
 *
 * `numero_rh` es un campo OPCIONAL (la asignación lo acepta vacío y el backend
 * no lo exige). La numeración "1, 2, 3, 4…" es únicamente una COMODIDAD de
 * frontend: cuando el usuario marca una asignación nueva y el campo está
 * vacío, se le propone el siguiente ordinal disponible.
 *
 * Reglas:
 *  - el valor sigue siendo editable y se puede dejar en blanco (válido);
 *  - los valores ya escritos (persistidos o editados) nunca se sobrescriben;
 *  - quitar una fila NO renumera a las que quedan;
 *  - la propuesta se calcula en el momento de añadir la fila.
 */

/** `true` si el `numero_rh` está vacío (null, undefined o solo espacios). */
export function esNumeroRhVacio(valor: string | null | undefined): boolean {
  return valor == null || valor.trim() === "";
}

/**
 * Propone el siguiente ordinal a partir de los valores ya seleccionados.
 *
 * Se toma el MAYOR entero positivo válido entre los valores actuales y se
 * devuelve ese número + 1 (string). Si no hay ningún entero positivo válido,
 * propone "1".
 *
 * Los valores no numéricos (p. ej. "RH-001") se ignoran para el cálculo: son
 * etiquetas, no ordinales.
 *
 * @param valores - Valores `numero_rh` de las filas ya seleccionadas.
 * @returns El ordinal sugerido como string (ej. "1", "2", "3").
 */
export function siguienteNumeroRhSugerido(
  valores: Array<string | null | undefined>,
): string {
  let maximo = 0;

  for (const valor of valores) {
    if (esNumeroRhVacio(valor)) continue;
    const numero = Number(valor?.trim());
    if (!Number.isInteger(numero) || numero <= 0) continue;
    if (numero > maximo) maximo = numero;
  }

  return String(maximo + 1);
}
