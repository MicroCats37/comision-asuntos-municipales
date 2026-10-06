"use client";

import { useCallback, useState } from "react";
/**
 * ContactoSmartField — Smart Component para el campo `contacto` del form.
 *
 * Architecture:
 * - Recibe `methods` (RHF) del padre.
 * - Se ata al campo `contacto` vía `useController({ name: "contacto" })` — usa el schema
 *   del form como única fuente de verdad. NO tiene estado propio del valor.
 * - Renderiza `<ContactoCard>` (visualización + CTAs) + `<ContactoFormModal>` (sub-modal de edición).
 * - Al guardar, llama `field.onChange(contacto)` con el `ContactoInline` resultante.
 * - Al eliminar, llama `field.onChange(undefined)` — RHF se encarga del reset.
 *
 * Antes este patrón vivía como `useState<ContactoInline>` local en
 * `LiquidacionEdificacionFormModal` + payload override manual
 * (`{...data, contacto: contacto ?? undefined}`). Eso duplicaba el state,
 * obligaba a `setContacto(null)` manual en cada branch del handler, y dejaba
 * a los 5 modales shell-based SIN UI de contacto.
 *
 * Referencia: mismo patrón que `EntidadLookupField` (EntidadLookupSmartField.tsx).
 */
import type { UseFormReturn } from "react-hook-form";
import { useController } from "react-hook-form";
import { ContactoCard } from "./ContactoCard";
import { ContactoFormModal } from "./ContactoFormModal";
import type { ContactoInline } from "../../schemas/liquidacion-form-base.schema";

interface ContactoSmartFieldProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  methods: UseFormReturn<any>;
  disabled?: boolean;
}

export function ContactoSmartField({ methods, disabled }: ContactoSmartFieldProps) {
  const { field } = useController({
    name: "contacto",
    control: methods.control,
  });

  const [open, setOpen] = useState(false);

  const handleSaved = useCallback(
    (contacto: ContactoInline) => {
      field.onChange(contacto);
      setOpen(false);
    },
    [field],
  );

  const handleRemove = useCallback(() => {
    field.onChange(undefined);
  }, [field]);

  const value: ContactoInline | null = field.value ?? null;

  return (
    <>
      <ContactoCard
        contacto={value}
        onAdd={() => setOpen(true)}
        onRemove={handleRemove}
      />
      <ContactoFormModal
        open={open}
        onOpenChange={setOpen}
        onSaved={handleSaved}
        initialData={value ?? undefined}
      />
    </>
  );
}