"use client";

import { Pencil, Phone, Plus, User, X } from "lucide-react";
import type { ContactoInline } from "../types/contacto";

interface ContactosSectionProps {
  /** List of currently selected contacts */
  selectedContactos: ContactoInline[];
  /** Whether the section is read-only (no add/remove) */
  readOnly?: boolean;
  /** Callback when user clicks add button */
  onAddContacto: () => void;
  /** Callback when user clicks remove on a contact (uses index) */
  onRemoveContacto: (index: number) => void;
  /** Callback when user clicks edit on a contact (uses index) */
  onEditContacto?: (index: number) => void;
}

/**
 * Reusable Contactos section for forms.
 * Displays selected contacts as cards and supports add/remove when not readOnly.
 */
export function ContactosSection({
  selectedContactos,
  readOnly = false,
  onAddContacto,
  onRemoveContacto,
  onEditContacto,
}: ContactosSectionProps) {
  const count = selectedContactos.length;

  return (
    <div className="space-y-2.5">
      {/* Header - subtle to avoid competing with the parent form sections */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border/40 pb-2 text-primary">
        <Phone className="h-4 w-4" />
        <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">
          Contactos
        </h3>
        {count > 0 && (
          <span className="text-[10px] font-medium text-muted-foreground">
            ({count} contacto{count !== 1 ? "s" : ""})
          </span>
        )}
        {!readOnly && (
          <button
            type="button"
            onClick={onAddContacto}
            className="ml-auto inline-flex items-center gap-1.5 rounded-md border border-primary/25 bg-primary/5 px-2.5 py-1 text-xs font-medium text-primary transition-colors hover:border-primary/40 hover:bg-primary/10"
            aria-label="Agregar contacto"
          >
            <Plus className="h-3.5 w-3.5" />
            Agregar contacto
          </button>
        )}
      </div>

      {/* Content */}
      {count > 0 ? (
        <div className="flex flex-wrap gap-2">
          {/* Contact chips */}
          {selectedContactos.map((contacto, index) => {
            const nombreCompleto = `${contacto.nombres} ${contacto.apellidos}`;
            const isPrincipal = contacto.principal === true;

            return (
              <div
                key={index}
                className="inline-flex max-w-full items-center gap-2 rounded-full border border-border/70 bg-secondary/30 px-2.5 py-1.5 transition-colors hover:border-primary/35 hover:bg-secondary/60"
              >
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <User className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0 text-xs leading-tight">
                  <div className="flex max-w-[260px] items-center gap-1.5 sm:max-w-[360px]">
                    <span className="truncate font-semibold text-foreground">
                      {nombreCompleto}
                    </span>
                    {isPrincipal && (
                      <span className="shrink-0 rounded bg-primary/15 px-1.5 py-0.5 text-[9px] font-semibold text-primary">
                        PRINCIPAL
                      </span>
                    )}
                  </div>
                  <div className="flex max-w-[260px] items-center gap-1.5 truncate text-[11px] text-muted-foreground sm:max-w-[360px]">
                    {contacto.cargo && (
                      <span className="truncate">{contacto.cargo}</span>
                    )}
                    {contacto.celular && (
                      <span className="shrink-0">
                        {contacto.cargo ? "• " : ""}
                        {contacto.celular}
                      </span>
                    )}
                    {contacto.email && (
                      <span className="truncate">
                        {contacto.cargo || contacto.celular ? "• " : ""}
                        {contacto.email}
                      </span>
                    )}
                    {contacto.dni && (
                      <span className="shrink-0">
                        {contacto.cargo || contacto.celular || contacto.email
                          ? "• "
                          : ""}
                        DNI: {contacto.dni}
                      </span>
                    )}
                  </div>
                </div>
                {!readOnly && (
                  <div className="ml-0.5 flex shrink-0 items-center gap-0.5">
                    {onEditContacto && (
                      <button
                        type="button"
                        onClick={() => onEditContacto(index)}
                        className="rounded-full p-1 transition-colors hover:bg-primary/10"
                        aria-label={`Editar ${nombreCompleto}`}
                      >
                        <Pencil className="h-3.5 w-3.5 text-muted-foreground hover:text-primary" />
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => onRemoveContacto(index)}
                      className="rounded-full p-1 transition-colors hover:bg-destructive/10"
                      aria-label={`Remover ${nombreCompleto}`}
                    >
                      <X className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          {readOnly
            ? "Sin contactos registrados."
            : "Agrega un contacto de referencia para esta liquidación."}
        </p>
      )}
    </div>
  );
}
