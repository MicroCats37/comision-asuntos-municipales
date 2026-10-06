"use client";

import { Phone, Plus, Trash2 } from "lucide-react";
/**
 * ContactoCard — Card de visualización del contacto principal dentro del form.
 *
 * Componente "tonto": recibe el contacto y los handlers onAdd/onRemove.
 * La lógica de binding con React Hook Form + sub-modal vive en
 * `ContactoSmartField` (su padre en composición).
 *
 * Antes vivía inline en `LiquidacionFormBodyBase.tsx`; se extrajo para
 * permitir que `ContactoSmartField` lo reuse sin duplicar JSX ni iconos.
 */
import { Button } from "@/components/ui/button";
import type { ContactoInline } from "../../schemas/liquidacion-form-base.schema";

interface ContactoCardProps {
  contacto: ContactoInline | null;
  onAdd: () => void;
  onRemove: () => void;
}

export function ContactoCard({ contacto, onAdd, onRemove }: ContactoCardProps) {
  return (
    <div className="rounded-xl border border-border/50 bg-card p-2 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          <Phone className="h-3.5 w-3.5 text-primary/70" />
          <span>Contacto Principal</span>
          {contacto && (
            <span className="inline-flex items-center rounded-full bg-primary/10 border border-primary/20 px-2 py-0.5 text-[9px] font-bold text-primary">
              Agregado
            </span>
          )}
        </div>
        {contacto ? (
          <div className="flex items-center gap-1 shrink-0">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={onAdd}
            >
              Editar
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 text-destructive hover:text-destructive"
              onClick={onRemove}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        ) : null}
      </div>

      {contacto ? (
        <div className="flex items-center justify-between gap-2 rounded-lg border border-border/60 bg-background px-3 py-2">
          <div className="min-w-0">
            <p className="text-sm font-medium truncate">
              {contacto.nombres} {contacto.apellidos}
            </p>
            <p className="text-xs text-muted-foreground truncate">
              {[
                contacto.dni ? `DNI ${contacto.dni}` : null,
                contacto.telefono || null,
                contacto.celular || null,
                contacto.email || null,
                contacto.cargo || null,
              ]
                .filter(Boolean)
                .join(" · ") || "Sin datos"}
            </p>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={onAdd}
          className="group flex w-full items-center gap-4 rounded-xl border-2 border-dashed border-primary/40 bg-primary/[0.04] p-2 text-left transition-all duration-200 hover:border-primary hover:bg-primary/[0.08] hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
        >
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-primary/10 border border-primary/20 group-hover:bg-primary/20 transition-colors">
            <Phone className="h-5 w-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-bold text-foreground">
              Agregar contacto principal
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Nombre, DNI, teléfono, email — para referencia de la liquidación
            </p>
          </div>
          <div className="inline-flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow-sm group-hover:shadow-md transition-shadow">
            <Plus className="h-4 w-4" />
            Agregar
          </div>
        </button>
      )}
    </div>
  );
}