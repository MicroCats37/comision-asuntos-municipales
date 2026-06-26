"use client";

import { User, Plus, X, Phone, Pencil } from "lucide-react";
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
    <div className="space-y-4">
      {/* Header - aligned with other section styles */}
      <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
        <Phone className="h-4 w-4" />
        <h3 className="text-sm font-semibold uppercase tracking-wide">
          Contactos
        </h3>
        {count > 0 && (
          <span className="ml-auto text-[10px] font-medium opacity-75">
            ({count} contacto{count !== 1 ? "s" : ""})
          </span>
        )}
      </div>

      {/* Content */}
      {count > 0 ? (
        <div className="flex flex-col gap-2">
          {/* Contact cards - full width vertical stack */}
          {selectedContactos.map((contacto, index) => {
            const nombreCompleto = `${contacto.nombres} ${contacto.apellidos}`;
            const isPrincipal = contacto.principal === true;

            return (
              <div
                key={index}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border bg-secondary/30 border-border/70 hover:bg-secondary/60 hover:border-primary/40 hover:shadow-sm hover:shadow-primary/10 transition-all"
              >
                {/* Avatar badge with primary accent ring */}
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm shadow-primary/20">
                  <User className="h-5 w-5" />
                </div>
                <div className="flex flex-col min-w-0 flex-1">
                  {/* Name row with principal badge */}
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-foreground truncate">
                      {nombreCompleto}
                    </span>
                    {isPrincipal && (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-semibold bg-primary/20 text-primary shrink-0">
                        PRINCIPAL
                      </span>
                    )}
                  </div>
                  {/* Metadata row - subtle with accent dots, responsive wrapping */}
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground mt-1">
                    {contacto.cargo && (
                      <>
                        <span className="inline-flex items-center px-2 py-0.5 rounded bg-muted/70 text-foreground/80 font-medium whitespace-nowrap">
                          {contacto.cargo}
                        </span>
                        <span className="text-muted-foreground/50">•</span>
                      </>
                    )}
                    {contacto.celular && (
                      <span className="whitespace-nowrap" title={contacto.celular}>
                        {contacto.celular}
                      </span>
                    )}
                    {contacto.email && (
                      <>
                        <span className="text-muted-foreground/50">•</span>
                        <span className="whitespace-nowrap truncate max-w-[150px] sm:max-w-[200px]" title={contacto.email}>
                          {contacto.email}
                        </span>
                      </>
                    )}
                    {contacto.dni && (
                      <>
                        <span className="text-muted-foreground/50">•</span>
                        <span className="whitespace-nowrap" title={contacto.dni}>
                          DNI: {contacto.dni}
                        </span>
                      </>
                    )}
                  </div>
                </div>
                {!readOnly && (
                  <div className="flex items-center gap-1 ml-1">
                    {onEditContacto && (
                      <button
                        type="button"
                        onClick={() => onEditContacto(index)}
                        className="hover:bg-primary/10 rounded p-1 transition-colors shrink-0"
                        aria-label={`Editar ${nombreCompleto}`}
                      >
                        <Pencil className="h-3.5 w-3.5 text-muted-foreground hover:text-primary" />
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => onRemoveContacto(index)}
                      className="hover:bg-destructive/10 rounded p-1 transition-colors shrink-0"
                      aria-label={`Remover ${nombreCompleto}`}
                    >
                      <X className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                    </button>
                  </div>
                )}
              </div>
            );
          })}

          {/* Add tile - full width, shown after contacts */}
          {!readOnly && (
            <button
              type="button"
              onClick={onAddContacto}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-dashed border-border hover:border-primary/40 hover:bg-secondary/30 transition-all text-muted-foreground hover:text-foreground"
              aria-label="Agregar contacto"
            >
              <Plus className="h-4 w-4" />
              <span className="text-sm font-medium">Agregar contacto</span>
            </button>
          )}
        </div>
      ) : (
        /* Empty state - centered add card, similar to other sections */
        <button
          type="button"
          onClick={onAddContacto}
          disabled={readOnly}
          className={`
            w-full flex flex-col items-center justify-center gap-3 p-8 rounded-xl border border-dashed transition-all
            ${readOnly
              ? "border-border bg-muted/30 cursor-not-allowed"
              : "border-border hover:border-primary/40 hover:bg-secondary/30 cursor-pointer"
            }
          `}
          aria-label="Agregar contacto"
        >
          <div className={`
            flex h-12 w-12 items-center justify-center rounded-full
            ${readOnly ? "bg-muted" : "bg-primary/10"}
          `}>
            <Plus className={`h-6 w-6 ${readOnly ? "text-muted-foreground" : "text-primary"}`} />
          </div>
          <div className="text-center">
            <p className={`text-sm font-medium ${readOnly ? "text-muted-foreground" : "text-foreground"}`}>
              {readOnly ? "Sin contactos" : "Agregar contacto"}
            </p>
            {!readOnly && (
              <p className="text-xs text-muted-foreground mt-1">
                Agrega un contacto de referencia para esta liquidación
              </p>
            )}
          </div>
        </button>
      )}
    </div>
  );
}
