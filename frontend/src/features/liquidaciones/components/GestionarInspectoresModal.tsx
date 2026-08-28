"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { UserCheck } from "lucide-react";
import { useCallback, useMemo } from "react";
import type { UseFormReturn } from "react-hook-form";
import { z } from "zod";

import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { handleApiError, notify } from "@/errors";
import type { InspectorVigente } from "@/features/inspectores/types/inspectores.types";
import api from "@/lib/api";
import {
  inspectoresVigentesResponseSchema,
  useInspectoresVigentes,
} from "../hooks/useInspectoresVigentes";
import { InspectoresSection } from "./InspectoresSection";

interface HasId {
  id: string;
}

const gestionarInspectoresSchema = z.object({
  inspectores_ids: z.array(z.string()),
});

interface GestionarInspectoresModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** UUID of the liquidacion to manage inspectors for */
  liquidacionId: string;
  /** Currently associated inspector IDs (from liquidacion list item) */
  inspectoresActuales: HasId[];
  onSuccess?: () => void;
}

export function GestionarInspectoresModal({
  open,
  onOpenChange,
  liquidacionId,
  inspectoresActuales,
  onSuccess,
}: GestionarInspectoresModalProps) {
  const queryClient = useQueryClient();

  const currentInspectorIds = useMemo(
    () => new Set(inspectoresActuales.map((i) => i.id)),
    [inspectoresActuales],
  );

  const { data: inspectoresVigentes = [], isLoading } = useInspectoresVigentes(
    open ? liquidacionId : null,
  );

  const batchMutation = useMutation({
    mutationFn: async (selectedIds: string[]) => {
      const create = selectedIds
        .filter((id) => !currentInspectorIds.has(id))
        .map((id) => ({ inspector_id: id }));

      const deleteItems = Array.from(currentInspectorIds)
        .filter((id) => !selectedIds.includes(id))
        .map((id) => ({ inspector_id: id }));

      const payload: Record<string, unknown[]> = {};
      if (create.length > 0) payload.create = create;
      if (deleteItems.length > 0) payload.delete = deleteItems;

      if (Object.keys(payload).length === 0) return null;

      const { data } = await api.patch(
        `/liquidaciones/${liquidacionId}/inspectores`,
        payload,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["liquidaciones"] });
      notify.success("Inspectores actualizados correctamente");
      onSuccess?.();
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      notify.error(apiError.message);
    },
  });

  const handleSubmit = useCallback(
    async (data: { inspectores_ids: string[] }) => {
      await batchMutation.mutateAsync(data.inspectores_ids);
    },
    [batchMutation],
  );

  const renderContent = useCallback(
    ({
      methods,
      isSubmitting,
    }: {
      methods: UseFormReturn<{ inspectores_ids: string[] }>;
      isSubmitting: boolean;
      onSubmit: () => void;
      submissionMessage: { type: "success" | "error"; message: string } | null;
    }) => {
      const selectedIds = methods.watch("inspectores_ids");

      const handleToggle = (id: string) => {
        const current = methods.getValues("inspectores_ids");
        const updated = current.includes(id)
          ? current.filter((i) => i !== id)
          : [...current, id];
        methods.setValue("inspectores_ids", updated, { shouldDirty: true });
      };

      return (
        <InspectoresSection
          inspectores={inspectoresVigentes}
          selectedIds={selectedIds}
          isLoading={isLoading}
          onToggleInspector={handleToggle}
        />
      );
    },
    [inspectoresVigentes, isLoading],
  );

  return (
    <AppFormModal
      open={open}
      onOpenChange={onOpenChange}
      title="Gestionar Inspectores"
      description="Selecciona los inspectores a asociar a esta inspección de obra."
      eyebrow="Inspección de Obra"
      icon={<UserCheck className="h-5 w-5 text-primary" />}
      primaryLabel="Guardar cambios"
      primaryLoadingLabel="Guardando..."
      primaryLoading={batchMutation.isPending}
      onPrimary={() => {}}
      schema={gestionarInspectoresSchema}
      initialData={{ inspectores_ids: inspectoresActuales.map((i) => i.id) }}
      onSubmit={handleSubmit}
      size="xl"
    >
      {renderContent}
    </AppFormModal>
  );
}
