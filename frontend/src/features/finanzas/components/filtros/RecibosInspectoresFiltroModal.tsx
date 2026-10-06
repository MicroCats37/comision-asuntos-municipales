"use client";

/**
 * RecibosInspectoresFiltroModal — Modal de filtros para Recibos Inspectores.
 * Usa AppFormModal como shell.
 *
 * Filtros: inspector_id (UUID)
 * Al aplicar: onApply(filtros) → la vista muestra los filtros activos arriba.
 */
import { Filter } from "lucide-react";
import { useCallback } from "react";
import { z } from "zod";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AppFormModal } from "@/components-app/forms/AppFormModal";

const filtroSchema = z.object({
  inspector_id: z.string().optional(),
});

type FiltroFormData = z.infer<typeof filtroSchema>;

interface RecibosInspectoresFiltroModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialFiltros?: { inspector_id?: string };
  onApply: (filtros: { inspector_id?: string }) => void;
}

export function RecibosInspectoresFiltroModal({
  open,
  onOpenChange,
  initialFiltros,
  onApply,
}: RecibosInspectoresFiltroModalProps) {
  const initialData: FiltroFormData = {
    inspector_id: initialFiltros?.inspector_id ?? "",
  };

  const handleSubmit = useCallback(
    async (data: FiltroFormData) => {
      const filtros: { inspector_id?: string } = {};
      if (data.inspector_id) filtros.inspector_id = data.inspector_id;
      onApply(filtros);
    },
    [onApply],
  );

  return (
    <AppFormModal<FiltroFormData>
      open={open}
      onOpenChange={onOpenChange}
      title="Filtrar Recibos Inspectores"
      description="Filtra por UUID de inspector"
      eyebrow="Finanzas"
      icon={<Filter className="h-5 w-5 text-primary" />}
      primaryLabel="Aplicar Filtros"
      primaryLoadingLabel="Aplicando..."
      primaryLoading={false}
      primaryDisabled={false}
      onPrimary={() => undefined}
      schema={filtroSchema}
      initialData={initialData}
      onSubmit={handleSubmit}
      size="md"
    >
      {({ methods }) => (
        <div className="space-y-4">
          {/* Inspector ID */}
          <div className="space-y-2">
            <Label htmlFor="recibos-inspector-filter-inspector">
              Inspector ID
            </Label>
            <Input
              id="recibos-inspector-filter-inspector"
              placeholder="UUID del inspector"
              className="w-full"
              {...methods.register("inspector_id")}
            />
          </div>
        </div>
      )}
    </AppFormModal>
  );
}
