"use client";

import { Trash2 } from "lucide-react";
import { useCallback } from "react";
import { z } from "zod";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { notify } from "@/errors";
import { useEliminarLiquidacion } from "../../hooks/useEliminarLiquidacion";

export const EliminarLiquidacionSchema = z.object({
  motivo: z.string().max(500).optional(),
});
export type EliminarLiquidacionData = z.infer<typeof EliminarLiquidacionSchema>;

interface EliminarLiquidacionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  liquidacion: {
    id: string;
    publicId: string;
  };
  entidadNombre?: string;
  onSuccess?: () => void;
}

export function EliminarLiquidacionModal({
  open,
  onOpenChange,
  liquidacion,
  entidadNombre,
  onSuccess,
}: EliminarLiquidacionModalProps) {
  const eliminarMutation = useEliminarLiquidacion(liquidacion.id);

  const handleSubmit = useCallback(
    async (data: EliminarLiquidacionData) => {
      try {
        await eliminarMutation.mutateAsync({ motivo: data.motivo });
        notify.success("Liquidación eliminada correctamente");
        onSuccess?.();
      } catch {
        // Error handled by mutation
      }
    },
    [eliminarMutation, onSuccess],
  );

  return (
    <AppFormModal<EliminarLiquidacionData>
      open={open}
      onOpenChange={onOpenChange}
      title="Eliminar Liquidación"
      description={
        entidadNombre
          ? `¿Estás seguro de que deseas eliminar la liquidación ${liquidacion.publicId} de ${entidadNombre}? Esta acción no se puede deshacer.`
          : `¿Estás seguro de que deseas eliminar la liquidación ${liquidacion.publicId}? Esta acción no se puede deshacer.`
      }
      eyebrow="Eliminar"
      icon={<Trash2 className="h-5 w-5 text-destructive" />}
      primaryLabel="Eliminar"
      primaryLoadingLabel="Eliminando..."
      primaryLoading={eliminarMutation.isPending}
      onPrimary={() => undefined}
      schema={EliminarLiquidacionSchema}
      initialData={{ motivo: "" }}
      onSubmit={handleSubmit}
      size="md"
    >
      {({ methods }) => (
        <div className="space-y-2">
          <Label htmlFor="motivo">
            Motivo de eliminación{" "}
            <span className="text-muted-foreground font-normal">
              (opcional)
            </span>
          </Label>
          <Textarea
            id="motivo"
            placeholder="Ingresa el motivo de la eliminación (opcional, máximo 500 caracteres)"
            rows={3}
            {...methods.register("motivo")}
          />
          {methods.formState.errors.motivo && (
            <p className="text-xs text-destructive">
              {methods.formState.errors.motivo.message}
            </p>
          )}
        </div>
      )}
    </AppFormModal>
  );
}
