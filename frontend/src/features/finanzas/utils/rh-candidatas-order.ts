type CandidataConNumero = {
  liquidacion_especifica_numero?: number | null;
};

type SeleccionRh<T extends CandidataConNumero> = {
  candidate: T;
};

function numeroParaOrdenar(item: CandidataConNumero): number {
  return item.liquidacion_especifica_numero ?? Number.MAX_SAFE_INTEGER;
}

/** Ordena las liquidaciones RH por su número específico, de menor a mayor. */
export function ordenarCandidatasRh<T extends CandidataConNumero>(
  candidatas: readonly T[],
): T[] {
  return [...candidatas].sort(
    (a, b) => numeroParaOrdenar(a) - numeroParaOrdenar(b),
  );
}

/** Mantiene las filas seleccionadas alineadas con el mismo orden del listado. */
export function ordenarSeleccionRh<
  T extends SeleccionRh<CandidataConNumero>,
>(selecciones: readonly T[]): T[] {
  return [...selecciones].sort(
    (a, b) => numeroParaOrdenar(a.candidate) - numeroParaOrdenar(b.candidate),
  );
}
