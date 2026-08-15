"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Users } from "lucide-react";
import { useCallback, useMemo } from "react";
import type { UseFormReturn } from "react-hook-form";
import { z } from "zod";

import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { useApiUpdate } from "@/hooks";
import { useDelegadosVigentes } from "../hooks/useDelegadosVigentes";
import { type Asignacion, DelegadosSection } from "./DelegadosSection";

interface HasId {
  id: string;
}

const gestionarDelegadosSchema = z.object({
  asignaciones: z.array(
    z.object({
      delegado_id: z.string(),
      periodo: z.string().optional().nullable(),
      dictamen_revision: z
        .enum(["CONFORME", "NO_CONFORME", "PENDIENTE", "AP_OB"])
        .optional()
        .nullable(),
      fecha_presentacion: z.string().optional().nullable(),
      fecha_revision: z.string().optional().nullable(),
    }),
  ),
});

type GestionarDelegadosFormData = z.infer<typeof gestionarDelegadosSchema>;

interface GestionarDelegadosModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  liquidacionId: string;
  municipalidadId: string;
  tipoLiquidacion: string;
  delegadosActuales: HasId[];
  onSuccess?: () => void;
}

export function GestionarDelegadosModal({
  open,
  onOpenChange,
  liquidacionId,
  municipalidadId,
  tipoLiquidacion,
  delegadosActuales,
  onSuccess,
}: GestionarDelegadosModalProps) {
  const queryClient = useQueryClient();

  const currentDelegadosIds = useMemo(
    () => new Set(delegadosActuales.map((d) => d.id)),
    [delegadosActuales],
  );

  const delegadosQuery = useDelegadosVigentes(
    open ? municipalidadId : null,
    open ? tipoLiquidacion : null,
    null,
  );

  const isLoading = delegadosQuery.isLoading;
  const allDelegados = useMemo(
    () => delegadosQuery.data ?? [],
    [delegadosQuery.data],
  );

  // Lógica de negocio del modal: arma el batch create/update/delete
  const buildBatchPayload = useCallback(
    (
      asignaciones: z.infer<typeof gestionarDelegadosSchema>["asignaciones"],
    ): Record<string, unknown[]> | null => {
      const selectedIds = new Set(asignaciones.map((a) => a.delegado_id));

      // create = selected ids not in currentDelegadosIds (metadata fields omitted)
      const create = asignaciones
        .filter((a) => !currentDelegadosIds.has(a.delegado_id))
        .map((a) => ({ delegado_id: a.delegado_id }));

      // delete = current ids not in selected
      const deleteItems = Array.from(currentDelegadosIds)
        .filter((id) => !selectedIds.has(id))
        .map((id) => ({ delegado_id: id }));

      // update = selected ids that ARE in currentDelegadosIds AND have at least one non-null metadata field
      const update = asignaciones
        .filter(
          (a) =>
            currentDelegadosIds.has(a.delegado_id) &&
            (a.periodo != null ||
              a.dictamen_revision != null ||
              a.fecha_presentacion != null ||
              a.fecha_revision != null),
        )
        .map((a) => {
          const entry: Record<string, string> = { delegado_id: a.delegado_id };
          if (a.periodo != null) entry.periodo = a.periodo;
          if (a.dictamen_revision != null)
            entry.dictamen_revision = a.dictamen_revision;
          if (a.fecha_presentacion != null)
            entry.fecha_presentacion = a.fecha_presentacion;
          if (a.fecha_revision != null) entry.fecha_revision = a.fecha_revision;
          return entry;
        });

      const payload: Record<string, unknown[]> = {};
      if (create.length > 0) payload.create = create;
      if (update.length > 0) payload.update = update;
      if (deleteItems.length > 0) payload.delete = deleteItems;

      return Object.keys(payload).length === 0 ? null : payload;
    },
    [currentDelegadosIds],
  );

  const batchMutation = useApiUpdate<unknown, Record<string, unknown[]>>({
    url: `/liquidaciones/${liquidacionId}/delegados`,
    method: "PATCH",
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["liquidaciones"] });
        onSuccess?.();
      },
    },
  });

  const handleSubmit = useCallback(
    async (data: GestionarDelegadosFormData) => {
      const payload = buildBatchPayload(data.asignaciones);
      if (!payload) return;
      await batchMutation.mutateAsync(payload);
    },
    [buildBatchPayload, batchMutation],
  );

  const renderContent = useCallback(
    ({
      methods,
    }: {
      methods: UseFormReturn<GestionarDelegadosFormData>;
      isSubmitting: boolean;
      onSubmit: () => void;
      submissionMessage: { type: "success" | "error"; message: string } | null;
    }) => {
      const selectedIds = methods
        .watch("asignaciones")
        .map((a) => a.delegado_id);

      const handleToggle = (id: string) => {
        const current = methods.getValues("asignaciones");
        const existing = current.find((a) => a.delegado_id === id);
        if (existing) {
          // Toggle OFF — remove
          methods.setValue(
            "asignaciones",
            current.filter((a) => a.delegado_id !== id),
            { shouldDirty: true },
          );
        } else {
          // Toggle ON — add with null metadata
          methods.setValue(
            "asignaciones",
            [
              ...current,
              {
                delegado_id: id,
                periodo: null,
                dictamen_revision: null,
                fecha_presentacion: null,
                fecha_revision: null,
              },
            ],
            { shouldDirty: true },
          );
        }
      };

      const handleUpdateAsignacion = (
        delegadoId: string,
        field: keyof Omit<Asignacion, "delegado_id">,
        value: string | null,
      ) => {
        const current = methods.getValues("asignaciones");
        const updated = current.map((a) =>
          a.delegado_id === delegadoId ? { ...a, [field]: value } : a,
        );
        methods.setValue("asignaciones", updated, { shouldDirty: true });
      };

      return (
        <DelegadosSection
          delegados={allDelegados}
          selectedIds={selectedIds}
          isLoading={isLoading}
          hasMunicipalidad={!!municipalidadId}
          onToggleDelegado={handleToggle}
          asignaciones={methods.getValues("asignaciones") as Asignacion[]}
          onUpdateAsignacion={handleUpdateAsignacion}
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
      description="Selecciona los delegados a asociar a esta liquidación y completa sus datos. Los cambios se aplican en lote."
      eyebrow="Liquidación"
      icon={<Users className="h-5 w-5 text-primary" />}
      primaryLabel="Guardar cambios"
      primaryLoadingLabel="Guardando..."
      primaryLoading={batchMutation.isPending}
      onPrimary={() => {}}
      schema={gestionarDelegadosSchema}
      initialData={{
        asignaciones: delegadosActuales.map((d) => ({
          delegado_id: d.id,
          periodo: null,
          dictamen_revision: null,
          fecha_presentacion: null,
          fecha_revision: null,
        })),
      }}
      onSubmit={handleSubmit}
      size="xl"
    >
      {renderContent}
    </AppFormModal>
  );
}
