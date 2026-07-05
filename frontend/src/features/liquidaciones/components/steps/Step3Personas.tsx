"use client";

import type { FieldValues, UseFormReturn } from "react-hook-form";
import { useLiquidacionStepperUIStore } from "../../store";
import { ContactosSection } from "../ContactosSection";
import { ProyectistasSection } from "../ProyectistasSection";

interface Step3PersonasProps {
  methods: UseFormReturn<FieldValues>;
  isActive: boolean;
  especialidadOptions?: Array<{ label: string; value: string }>;
  especialidadLabels?: Record<string, string>;
  onOpenProyectistaModal: () => void;
  onRemoveProyectista: (cip: string) => void;
  onOpenContactoModal: () => void;
  onEditContacto: (index: number) => void;
  onRemoveContacto: (index: number) => void;
}

export function Step3Personas({
  methods: _methods,
  isActive,
  especialidadOptions: _especialidadOptions,
  especialidadLabels = {},
  onOpenProyectistaModal,
  onRemoveProyectista,
  onOpenContactoModal,
  onEditContacto,
  onRemoveContacto,
}: Step3PersonasProps) {
  const { selectedProyectistas, selectedContactos } =
    useLiquidacionStepperUIStore();

  if (!isActive) return null;

  return (
    <div className="space-y-4 min-w-0 max-w-full">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 min-w-0">
        {/* Proyectistas */}
        <div className="rounded-xl border border-primary/20 bg-card p-4 min-w-0 overflow-hidden">
          <ProyectistasSection
            selectedProyectistas={selectedProyectistas}
            onAddProyectista={onOpenProyectistaModal}
            onRemoveProyectista={onRemoveProyectista}
            especialidadLabels={especialidadLabels}
          />
        </div>

        {/* Contactos */}
        <div className="rounded-xl border border-primary/20 bg-card p-4 min-w-0 overflow-hidden">
          <ContactosSection
            selectedContactos={selectedContactos}
            onAddContacto={onOpenContactoModal}
            onRemoveContacto={onRemoveContacto}
            onEditContacto={onEditContacto}
          />
        </div>
      </div>
    </div>
  );
}
