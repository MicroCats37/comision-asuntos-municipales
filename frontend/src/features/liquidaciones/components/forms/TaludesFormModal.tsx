"use client";

/**
 * TaludesFormModal — Modal shell for Taludes liquidaciones.
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
import { useCrearTaludes } from "../../hooks/useCrearTaludes";
import { porcentajeObraFormSchema, type PorcentajeObraFormData } from "../../schemas/liquidacion-porcentaje-form.schema";
import { CotizacionPorcentajeSmartField } from "./CotizacionPorcentajeSmartField";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { Building2, FileText, MessageSquare, Mountain } from "lucide-react";
import { TarifasPorcentajeSmartField } from "./TarifasPorcentajeSmartField";
import { ProyectoSmartField } from "./ProyectoSmartField";

interface TaludesFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  onCreated?: () => void;
}

export function TaludesFormModal({
  open,
  onOpenChange,
  onSuccess,
  onCreated,
}: TaludesFormModalProps) {
  const crearMutation = useCrearTaludes();

  const handleSubmit = useCallback(
    async (data: PorcentajeObraFormData) => {
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
      title="Nueva Liquidación — Taludes"
      eyebrow="Taludes"
      icon={<Mountain className="h-5 w-5 text-primary" />}
      primaryLabel="Crear Liquidación"
      primaryLoadingLabel="Creando..."
      primaryLoading={crearMutation.isPending}
      onPrimary={() => {}}
      schema={porcentajeObraFormSchema}
      onSubmit={handleSubmit}
    >
      {({ methods, isSubmitting }) => (
        <TaludesFormBody methods={methods} isSubmitting={isSubmitting} />
      )}
    </AppFormModal>
  );
}

interface TaludesFormBodyProps {
  methods: UseFormReturn<PorcentajeObraFormData>;
  isSubmitting: boolean;
}

function TaludesFormBody({
  methods,
  isSubmitting,
}: TaludesFormBodyProps) {
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

          {/* Valor Declarado */}
          <GenericInput
            field={{
              name: "valor_declarado",
              label: "Valor Declarado (S/)",
              type: "number",
              placeholder: "S/ 0.00",
              icon: FileText,
              required: true,
              min: 0,
              step: 0.01,
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
      <TarifasPorcentajeSmartField methods={methods} />

      {/* Cotización Preview */}
      <CotizacionPorcentajeSmartField methods={methods} />
    </div>
  );
}
