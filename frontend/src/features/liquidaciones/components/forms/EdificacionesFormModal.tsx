"use client";

/**
 * EdificacionesFormModal — Modal shell that wires everything together.
 *
 * Architecture:
 * - AppFormModal = shell (open/close, footer with submit button)
 * - GenericForm = orchestrator (useForm + zodResolver)
 * - Smart Fields = self-contained components connected via `control` using useController
 */
import { useCallback } from "react";
import type { Control, UseFormReturn } from "react-hook-form";
import { useController } from "react-hook-form";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { notify } from "@/errors";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { MoneyInput } from "@/components/genericForm/inputs/MoneyInput";
import { useCrearEdificaciones } from "../../hooks/useCrearEdificaciones";
import {
  type EdificacionesFormData,
  edificacionesFormSchema,
} from "../../schemas/liquidacion-edificaciones-form.schema";
import { CotizacionPorcentajeSmartField } from "./CotizacionPorcentajeSmartField";
import { Building2, FileText } from "lucide-react";
import { TarifasPorcentajePrimeraRevisionSmartField } from "./TarifasPorcentajePrimeraRevisionSmartField";
import { ProyectoSmartField } from "./ProyectoSmartField";

interface EdificacionesFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  onCreated?: () => void;
}

export function EdificacionesFormModal({
  open,
  onOpenChange,
  onSuccess,
  onCreated,
}: EdificacionesFormModalProps) {
  const crearMutation = useCrearEdificaciones();

  const handleSubmit = useCallback(
    async (data: EdificacionesFormData) => {
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
      title="Nueva Liquidación — Edificaciones"
      eyebrow="Edificaciones"
      icon={<FileText className="h-5 w-5 text-primary" />}
      primaryLabel="Crear Liquidación"
      primaryLoadingLabel="Creando..."
      primaryLoading={crearMutation.isPending}
      onPrimary={() => {}}
      schema={edificacionesFormSchema}
      initialData={{ valor_declarado: 0 }}
      onSubmit={handleSubmit}
    >
      {({ methods, isSubmitting }) => (
        <EdificacionesFormBody control={methods.control} isSubmitting={isSubmitting} methods={methods} />
      )}
    </AppFormModal>
  );
}

// ── Smart Inputs (useController pattern) ─────────────────────────────────

function ExpedienteField({ control }: { control: Control<EdificacionesFormData> }) {
  const { field, fieldState } = useController({ name: "expediente", control });
  return (
    <div className="space-y-2">
      <Label htmlFor="expediente">
        Expediente <span className="text-destructive">*</span>
      </Label>
      <div className="relative">
        <FileText className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input id="expediente" placeholder="Número de expediente" className="pl-10" {...field} />
      </div>
      {fieldState.error && <p className="text-xs text-destructive">{fieldState.error.message}</p>}
    </div>
  );
}

function MunicipalidadField({ control }: { control: Control<EdificacionesFormData> }) {
  const { field, fieldState } = useController({ name: "municipalidad_id", control });
  return (
    <div className="space-y-2">
      <Label htmlFor="municipalidad_id">
        Municipalidad <span className="text-destructive">*</span>
      </Label>
      <div className="relative">
        <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          id="municipalidad_id"
          placeholder="ID de la municipalidad (UUID)"
          className="pl-10"
          {...field}
        />
      </div>
      {fieldState.error && <p className="text-xs text-destructive">{fieldState.error.message}</p>}
    </div>
  );
}

function ObservacionField({ control }: { control: Control<EdificacionesFormData> }) {
  const { field } = useController({ name: "observacion", control });
  return (
    <div className="space-y-2 md:col-span-2">
      <Label htmlFor="observacion">Observación</Label>
      <Textarea id="observacion" placeholder="Observaciones adicionales (opcional)" rows={2} {...field} />
    </div>
  );
}

// ── Form Body ────────────────────────────────────────────────────────────

interface EdificacionesFormBodyProps {
  control: Control<EdificacionesFormData>;
  isSubmitting: boolean;
  methods: UseFormReturn<EdificacionesFormData>;
}

function EdificacionesFormBody({ control, isSubmitting, methods }: EdificacionesFormBodyProps) {
  return (
    <div className="space-y-4">
      {/* Proyecto Section */}
      <ProyectoSmartField methods={methods} />

      {/* Datos del Trámite */}
      <div className="space-y-4 rounded-xl border border-border/50 bg-card p-4">
        <div className="flex items-center gap-2 border-b border-border/40 pb-2">
          <FileText className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold uppercase tracking-wide">Datos del Trámite</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <MunicipalidadField control={control} />
          <ExpedienteField control={control} />
          <div className="space-y-2">
            <MoneyInput
              name="valor_declarado"
              label="Valor Declarado"
              placeholder="S/ 0.00"
              control={control}
              required
              defaultValue={0}
            />
          </div>
          <ObservacionField control={control} />
        </div>
      </div>

      {/* Tarifas Section */}
      <TarifasPorcentajePrimeraRevisionSmartField methods={methods} />

      {/* Cotización Preview */}
      <CotizacionPorcentajeSmartField methods={methods} />
    </div>
  );
}
