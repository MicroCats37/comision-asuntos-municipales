"use client";

import { useMutation, useQueries, useQueryClient } from "@tanstack/react-query";
import { Users } from "lucide-react";
import { useCallback, useMemo } from "react";
import type { UseFormReturn } from "react-hook-form";
import { z } from "zod";

import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { handleApiError, notify } from "@/errors";
import api from "@/lib/api";
import { delegadosVigentesResponseSchema } from "../hooks/useDelegadosVigentes";
import type { DelegadoVigente } from "../types/liquidacion-edificaciones";
import { DelegadosSection } from "./DelegadosSection";

interface HasId {
  id: string;
}

const gestionarDelegadosSchema = z.object({
  delegados_ids: z.array(z.string()),
});

interface GestionarDelegadosModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  liquidacionId: string;
  municipalidadId: string;
  tipoLiquidacion: string;
  revisionIds: string[];
  delegadosActuales: HasId[];
  onSuccess?: () => void;
}

export function GestionarDelegadosModal({
  open,
  onOpenChange,
  liquidacionId,
  municipalidadId,
  tipoLiquidacion,
  revisionIds,
  delegadosActuales,
  onSuccess,
}: GestionarDelegadosModalProps) {
  const queryClient = useQueryClient();

  const currentDelegadosIds = useMemo(
    () => new Set(delegadosActuales.map((d) => d.id)),
    [delegadosActuales],
  );

  const delegadosQueries = useQueries({
    queries: revisionIds.map((revisionId) => ({
      queryKey: [
        "delegados-vigentes",
        municipalidadId,
        tipoLiquidacion,
        revisionId,
      ],
      queryFn: async () => {
        const { data } = await api.get("/liquidaciones/delegados/vigentes", {
          params: {
            municipalidad_id: municipalidadId,
            tipo_liquidacion: tipoLiquidacion,
            revision_id: revisionId,
          },
        });
        const parsed = delegadosVigentesResponseSchema.parse(data);
        return parsed.data?.delegados ?? [];
      },
      enabled: open && !!municipalidadId && !!revisionId,
      staleTime: 1000 * 60 * 5,
    })),
  });

  const isLoading = delegadosQueries.some((q) => q.isLoading);
  const allDelegados = useMemo(() => {
    const seen = new Map<string, DelegadoVigente>();
    for (const q of delegadosQueries) {
      if (q.data) {
        for (const d of q.data) {
          if (!seen.has(d.id)) {
            seen.set(d.id, d);
          }
        }
      }
    }
    return Array.from(seen.values());
  }, [delegadosQueries]);

  const batchMutation = useMutation({
    mutationFn: async (selectedIds: string[]) => {
      const create = selectedIds
        .filter((id) => !currentDelegadosIds.has(id))
        .map((id) => ({ delegado_id: id }));

      const deleteItems = Array.from(currentDelegadosIds)
        .filter((id) => !selectedIds.includes(id))
        .map((id) => ({ delegado_id: id }));

      const payload: Record<string, unknown[]> = {};
      if (create.length > 0) payload.create = create;
      if (deleteItems.length > 0) payload.delete = deleteItems;

      if (Object.keys(payload).length === 0) return null;

      const { data } = await api.patch(
        `/liquidaciones/${liquidacionId}/delegados`,
        payload,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["liquidaciones"] });
      onSuccess?.();
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      notify.error(apiError.message);
    },
  });

  const handleSubmit = useCallback(
    async (data: { delegados_ids: string[] }) => {
      await batchMutation.mutateAsync(data.delegados_ids);
    },
    [batchMutation],
  );

  const renderContent = useCallback(
    ({
      methods,
      isSubmitting,
    }: {
      methods: UseFormReturn<{ delegados_ids: string[] }>;
      isSubmitting: boolean;
      onSubmit: () => void;
      submissionMessage: { type: "success" | "error"; message: string } | null;
    }) => {
      const selectedIds = methods.watch("delegados_ids");

      const handleToggle = (id: string) => {
        const current = methods.getValues("delegados_ids");
        const updated = current.includes(id)
          ? current.filter((i) => i !== id)
          : [...current, id];
        methods.setValue("delegados_ids", updated, { shouldDirty: true });
      };

      return (
        <DelegadosSection
          delegados={allDelegados}
          selectedIds={selectedIds}
          isLoading={isLoading}
          hasMunicipalidad={!!municipalidadId}
          onToggleDelegado={handleToggle}
        />
      );
    },
    [allDelegados, isLoading, municipalidadId],
  );

  return (
    <AppFormModal
      open={open}
      onOpenChange={onOpenChange}
      title="Gestionar Delegados"
      description="Selecciona los delegados a asociar a esta liquidación. Los cambios se aplican en lote."
      eyebrow="Liquidación"
      icon={<Users className="h-5 w-5 text-primary" />}
      primaryLabel="Guardar cambios"
      primaryLoadingLabel="Guardando..."
      primaryLoading={batchMutation.isPending}
      onPrimary={() => {}}
      schema={gestionarDelegadosSchema}
      initialData={{ delegados_ids: delegadosActuales.map((d) => d.id) }}
      onSubmit={handleSubmit}
      size="xl"
    >
      {renderContent}
    </AppFormModal>
  );
}
