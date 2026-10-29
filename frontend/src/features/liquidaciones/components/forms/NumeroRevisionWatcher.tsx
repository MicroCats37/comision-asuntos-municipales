"use client";

import { useEffect } from "react";
import type { Control } from "react-hook-form";
import { useWatch } from "react-hook-form";
import { toNumeroRevision } from "../../utils/numeroRevision";

interface NumeroRevisionWatcherProps {
  // biome-ignore lint/suspicious/noExplicitAny: RHF generics pattern matches the existing smart fields
  control: Control<any>;
  onChange: (numeroRevision: number | undefined) => void;
}

/**
 * NumeroRevisionWatcher — publica el valor VIVO de `numero_revision`.
 *
 * El slot `headerActions` de `AppFormModal` se renderiza en el header del
 * modal, FUERA del `FormProvider` de `GenericForm` (que vive en el body), por
 * lo que la cabecera del formulario no puede usar `useWatch` por sí misma.
 * Este componente se monta DENTRO del form y levanta el valor al shell, que
 * lo refleja en la cabecera.
 *
 * Cuando el formulario no tiene el campo (Inspección de Obra) se publica
 * `undefined`: la cabecera conserva entonces la revisión fija (1).
 */
export function NumeroRevisionWatcher({
  control,
  onChange,
}: NumeroRevisionWatcherProps) {
  const valor = useWatch({ control, name: "numero_revision" });

  useEffect(() => {
    onChange(toNumeroRevision(valor));
  }, [valor, onChange]);

  return null;
}
