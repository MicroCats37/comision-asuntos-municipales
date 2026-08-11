"use client";

/**
 * InspeccionObraFormModal — Modal shell for Inspección de Obra liquidaciones.
 *
 * Architecture:
 * - AppFormModal = shell (open/close, footer with submit button)
 * - GenericForm = orchestrator (useForm + zodResolver, layout)
 * - Smart Fields = self-contained components connected via `methods: UseFormReturn`
 */
import { useCallback } from "react";
import type { UseFormReturn } from "react-hook-form";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { notify } from "@/errors";
import { useCrearInspeccionObra } from "../../hooks/useCrearInspeccionObra";
import { visitasFormSchema, type VisitasFormData } from "../../schemas/liquidacion-visitas-form.schema";
import { CotizacionVisitasSmartField } from "./CotizacionVisitasSmartField";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { Building2, ClipboardCheck, FileText, MessageSquare } from "lucide-react";
import { TarifasVisitasSmartField } from "./TarifasVisitasSmartField";
import { ProyectoSmartField } from "./ProyectoSmartField";

interface InspeccionObraFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  onCreated?: () => void;
}

export function InspeccionObraFormModal({
  open,
  onOpenChange,
  onSuccess,
  onCreated,
}: InspeccionObraFormModalProps) {
  const crearMutation = useCrearInspeccionObra();

  const handleSubmit = useCallback(
    async (data: VisitasFormData) => {
      try {
        await crearMutation.mutateAsync(data);
        notify.success("Liquidación creada correctamente");
        onSuccess?.();
        onCreated?.();
      } catch {
        // Error handled by mutation
      }
    },
    [crearMutation, onSuccess, onCreated],
  );

  return (
    <AppFormModal
      open={open}
      onOpenChange={onOpenChange}
      title="Nueva Liquidación — Inspección de Obra"
      eyebrow="Inspección de Obra"
      icon={<ClipboardCheck className="h-5 w-5 text-primary" />}
      primaryLabel="Crear Liquidación"
      primaryLoadingLabel="Creando..."
      primaryLoading={crearMutation.isPending}
      onPrimary={() => {}}
      schema={visitasFormSchema}
      onSubmit={handleSubmit}
    >
      {({ methods, isSubmitting }) => (
        <InspeccionObraFormBody methods={methods} isSubmitting={isSubmitting} />
      )}
    </AppFormModal>
  );
}

interface InspeccionObraFormBodyProps {
  methods: UseFormReturn<VisitasFormData>;
  isSubmitting: boolean;
}

function InspeccionObraFormBody({
  methods,
  isSubmitting,
}: InspeccionObraFormBodyProps) {
  const {
    register,
    control,
    formState: { errors },
  } = methods;

  return (
    <div className="space-y-4">
      {/* Proyecto Section */}
      <ProyectoSmartField methods={methods} />

      {/* Datos del Trámite */}
      <div className="space-y-4 rounded-xl border border-border/50 bg-card p-4">
        <div className="flex items-center gap-2 border-b border-border/40 pb-2 text-primary">
          <FileText className="h-4 w-4" />
          <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">
            Datos del Trámite
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Municipalidades */}
          <GenericInput
            field={{
              name: "municipalidad_id",
              label: "Municipalidad",
              type: "searchable-select",
              placeholder: "Seleccione municipalidad",
              icon: Building2,
              required: true,
              options: [],
            }}
            register={register as never}
            control={control as never}
            errors={errors}
          />

          {/* Expediente */}
          <GenericInput
            field={{
              name: "expediente",
              label: "Expediente",
              type: "text",
              placeholder: "Número de expediente",
              icon: FileText,
              required: true,
            }}
            register={register as never}
            control={control as never}
            errors={errors}
          />

          {/* Cantidad Visitas */}
          <GenericInput
            field={{
              name: "cantidad_visitas",
              label: "Cantidad de Visitas",
              type: "number",
              placeholder: "1",
              icon: ClipboardCheck,
              required: true,
              min: 1,
              step: 1,
            }}
            register={register as never}
            control={control as never}
            errors={errors}
          />

          {/* Categoría */}
          <GenericInput
            field={{
              name: "categoria",
              label: "Categoría",
              type: "select",
              placeholder: "Seleccione categoría",
              icon: ClipboardCheck,
              required: true,
              options: [
                { value: "C1", label: "C1" },
                { value: "C2", label: "C2" },
                { value: "C3", label: "C3" },
                { value: "C4", label: "C4" },
              ],
            }}
            register={register as never}
            control={control as never}
            errors={errors}
          />

          {/* Observación */}
          <GenericInput
            field={{
              name: "observacion",
              label: "Observación",
              type: "textarea",
              placeholder: "Observaciones adicionales (opcional)",
              icon: MessageSquare,
              containerClassName: "md:col-span-2",
            }}
            register={register as never}
            control={control as never}
            errors={errors}
          />
        </div>
      </div>

      {/* Tarifas Section */}
      <TarifasVisitasSmartField methods={methods} />

      {/* Cotización Preview */}
      <CotizacionVisitasSmartField methods={methods} />
    </div>
  );
}
