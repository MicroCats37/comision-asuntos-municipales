"use client";

import { Users } from "lucide-react";
import { useState } from "react";
import { z } from "zod";

import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { handleApiError } from "@/errors";
import { useDelegadosVigentes } from "../hooks/useDelegadosVigentes";
import { useQuitarDelegadoLiquidacion } from "../hooks/useQuitarDelegadoLiquidacion";
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
  // Estado POR FILA de la acción "Quitar delegado".
  const [quitarPendientes, setQuitarPendientes] = useState<string[]>([]);
  const [quitarErrores, setQuitarErrores] = useState<Record<string, string>>(
    {},
  );
  // Delegados ya quitados con éxito: se ocultan aunque el snapshot que
  // recibe el modal todavía los contenga (el refetch de la cache es asíncrono).
  const [delegadosRemovidos, setDelegadosRemovidos] = useState<string[]>([]);

  const quitarDelegado = useQuitarDelegadoLiquidacion(liquidacionGeneral.id);

  const asignados = (liquidacionGeneral.delegados ?? []).filter(
    (item) => !delegadosRemovidos.includes(item.delegado.id),
  );

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

  /**
   * Quita UN delegado. Emite exactamente un PATCH con un único item en
   * `delete`. Sólo tras un 2xx la fila se considera quitada; un rechazo (409)
   * se muestra EN la fila y la fila permanece en la lista.
   */
  const handleQuitarDelegado = async (delegadoId: string) => {
    setQuitarPendientes((prev) => [...prev, delegadoId]);
    setQuitarErrores((prev) => {
      const next = { ...prev };
      delete next[delegadoId];
      return next;
    });

    try {
      await quitarDelegado.quitar({ delegado_id: delegadoId });
      setDelegadosRemovidos((prev) =>
        prev.includes(delegadoId) ? prev : [...prev, delegadoId],
      );
    } catch (error) {
      setQuitarErrores((prev) => ({
        ...prev,
        [delegadoId]: handleApiError(error).message,
      }));
    } finally {
      setQuitarPendientes((prev) => prev.filter((id) => id !== delegadoId));
    }
  };

  return (
    <AppFormModal
      open={open}
      onOpenChange={onOpenChange}
      title="Delegados de la Liquidación"
      description="Delegados asociados a esta liquidación. Puede quitar un delegado que no tenga registros financieros asociados."
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
          onQuitarDelegado={handleQuitarDelegado}
          quitarDelegadoPendientes={quitarPendientes}
          quitarDelegadoErrores={quitarErrores}
        />
      )}
    </AppFormModal>
  );
}
