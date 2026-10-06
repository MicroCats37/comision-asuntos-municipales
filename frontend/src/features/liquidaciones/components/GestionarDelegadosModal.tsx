"use client";

import { Users } from "lucide-react";
import { z } from "zod";

import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { useDelegadosVigentes } from "../hooks/useDelegadosVigentes";
import type { LiquidacionGeneralOutput } from "../schemas/liquidacion-base.schema";
import { DelegadosSection } from "./DelegadosSection";

const gestionarDelegadosSchema = z.object({
  // No fields needed — read-only modal, no form submission
  asignaciones: z.array(z.unknown()).optional(),
});

interface GestionarDelegadosModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** The full liquidacion general — modal reads delegates directly from it */
  liquidacionGeneral: LiquidacionGeneralOutput;
}

export function GestionarDelegadosModal({
  open,
  onOpenChange,
  liquidacionGeneral,
}: GestionarDelegadosModalProps) {
  const asignados = liquidacionGeneral.delegados ?? [];

  // Extract municipalidadId directly from liquidacionGeneral (schema: municipalidad is a direct field)
  const municipalidadId = liquidacionGeneral.municipalidad?.id ?? null;
  const tipoLiquidacion = liquidacionGeneral.tipo_liquidacion?.codigo ?? null;

  // Fetch vigentes delegates filtered by municipalidad, tipo, and fechaRegistro
  const { data: vigentes = [], isLoading } = useDelegadosVigentes(
    municipalidadId,
    tipoLiquidacion,
    null, // revisionId — not needed for this read-only modal
    liquidacionGeneral.fecha_registro,
    open,
  );

  return (
    <AppFormModal
      open={open}
      onOpenChange={onOpenChange}
      title="Delegados de la Liquidación"
      description="Delegados asociados a esta liquidación. Vista de solo lectura."
      eyebrow="Liquidación"
      icon={<Users className="h-5 w-5 text-primary" />}
      primaryLabel="Cerrar"
      primaryLoadingLabel="Cerrando..."
      primaryLoading={false}
      onPrimary={() => {}}
      schema={gestionarDelegadosSchema}
      initialData={{ asignaciones: [] }}
      onSubmit={() => {}}
      size="xl"
    >
      {() => (
        <DelegadosSection
          vigentes={vigentes}
          asignados={asignados}
          isLoading={isLoading}
          fechaReferencia={liquidacionGeneral.fecha_registro}
          hasMunicipalidad={!!municipalidadId}
        />
      )}
    </AppFormModal>
  );
}
