"use client";

/**
 * DatosDelProyectoSection — Reusable "Datos del Proyecto" section for liquidation forms.
 *
 * Shared UI pattern across liquidation modals:
 * - Wrapper div with border, header "Datos del Proyecto" + Building2 icon
 * - Denominación + Dirección fields (configurable names/labels via props)
 * - Entity section slot (passed as children — allows EntidadLookupField or inline fields)
 * - Contactos compact section via ContactosSection
 *
 * This component does NOT include cotizacion — that's module-specific per liquidation type.
 */

import type { UseFormRegister } from "react-hook-form";
import type { ReactNode } from "react";
import { Building2, MapPin } from "lucide-react";
import type { ContactoInline } from "../types/contacto";
import { ContactosSection } from "./ContactosSection";
import { GenericInput } from "@/components/genericForm/GenericInput";

export interface DatosDelProyectoFieldConfig {
  name: string;
  label: string;
  placeholder?: string;
  required?: boolean;
}

export interface DatosDelProyectoSectionProps {
  /** Form registration from react-hook-form */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  register: UseFormRegister<any>;
  /** Form control from react-hook-form */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  control: import("react-hook-form").Control<any, any>;
  /** Form errors from react-hook-form */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  errors: Record<string, any>;
  /** Denominacion field config */
  denominacionField: DatosDelProyectoFieldConfig;
  /** Direccion field config */
  direccionField: DatosDelProyectoFieldConfig;
  /** Slot for the entity section content — e.g. EntidadLookupField or inline entity fields */
  entidadSlot: ReactNode;
  /** Contactos section — selected contacts list */
  selectedContactos: ContactoInline[];
  /** Callback when user clicks add contacto */
  onAddContacto: () => void;
  /** Callback when user clicks remove on a contacto */
  onRemoveContacto: (index: number) => void;
  /** Optional callback when user clicks edit on a contacto */
  onEditContacto?: (index: number) => void;
  /** Whether contactos section is read-only */
  contactosReadOnly?: boolean;
  /** Additional class for the wrapper div */
  wrapperClassName?: string;
}

/**
 * Reusable "Datos del Proyecto" section.
 *
 * Usage:
 * - Pass `entidadSlot` with the appropriate entity fields for your form
 * - Edificaciones: wrap EntidadLookupField + proy_nombre_propietario as the slot
 * - Habilitacion Urbana: pass inline entity fields as the slot
 */
export function DatosDelProyectoSection({
  register,
  errors,
  denominacionField,
  direccionField,
  entidadSlot,
  selectedContactos,
  onAddContacto,
  onRemoveContacto,
  onEditContacto,
  contactosReadOnly = false,
  wrapperClassName = "",
}: DatosDelProyectoSectionProps) {
  return (
    <div
      className={`rounded-xl border border-border/50 bg-card p-4 space-y-4 pt-4 ${wrapperClassName}`}
    >
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 border-b border-border/40 pb-2 text-primary">
        <Building2 className="h-4 w-4" />
        <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">
          Datos del Proyecto
        </h3>
      </div>

      {/* ── Denominacion + Direccion ────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <GenericInput
          field={{
            name: denominacionField.name,
            label: denominacionField.label,
            type: "text",
            required: denominacionField.required,
            placeholder: denominacionField.placeholder,
            icon: Building2,
            labelClassName: "text-foreground font-medium",
            containerClassName: "min-w-0 w-full",
          }}
          register={register as never}
          control={undefined as never}
          errors={errors as never}
        />
        <GenericInput
          field={{
            name: direccionField.name,
            label: direccionField.label,
            type: "text",
            required: direccionField.required,
            placeholder: direccionField.placeholder,
            icon: MapPin,
            labelClassName: "text-foreground font-medium",
            containerClassName: "min-w-0 w-full",
          }}
          register={register as never}
          control={undefined as never}
          errors={errors as never}
        />
      </div>

      {/* ── Entidad section (slot) ───────────────────────────────────── */}
      {entidadSlot}

      {/* ── Contactos ──────────────────────────────────────────────── */}
      <div className="border-t border-border/20 pt-4">
        <ContactosSection
          selectedContactos={selectedContactos}
          readOnly={contactosReadOnly}
          onAddContacto={onAddContacto}
          onRemoveContacto={onRemoveContacto}
          onEditContacto={onEditContacto}
        />
      </div>
    </div>
  );
}
