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
import type { Control, UseFormReturn, FieldErrors } from "react-hook-form";
import { useController } from "react-hook-form";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { notify } from "@/errors";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { MoneyInput } from "@/components/genericForm/inputs/MoneyInput";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { useMunicipalidades } from "../../hooks/useMunicipalidades";
import { useDistritos } from "../../hooks/useDistritos";
import { useCrearEdificaciones } from "../../hooks/useCrearEdificaciones";
import {
  type EdificacionesFormData,
  edificacionesFormSchema,
} from "../../schemas/liquidacion-edificaciones-form.schema";
import { CotizacionPorcentajeSmartField } from "./CotizacionPorcentajeSmartField";
import { Building2, FileText, MapPin, User } from "lucide-react";
import { TarifasPorcentajePrimeraRevisionSmartField } from "./TarifasPorcentajePrimeraRevisionSmartField";
import { EntidadLookupField } from "./EntidadLookupSmartField";

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

function MunicipalidadField({ register, control, errors }: { register: UseFormReturn<EdificacionesFormData>["register"]; control: UseFormReturn<EdificacionesFormData>["control"]; errors: FieldErrors<EdificacionesFormData> }) {
  const { data: municipalidades, isLoading } = useMunicipalidades();

  return (
    <GenericInput
      field={{
        name: "municipalidad_id",
        label: "Municipalidad",
        type: "searchable-select",
        placeholder: isLoading ? "Cargando..." : "Seleccione municipalidad",
        icon: Building2,
        required: true,
        options: (municipalidades || []).map((m) => ({
          label: m.nombre,
          value: m.id,
        })),
        isLoading,
      }}
      register={register as never}
      control={control as never}
      errors={errors}
    />
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

function DenominacionField({ control }: { control: Control<EdificacionesFormData> }) {
  const { field, fieldState } = useController({ name: "denominacion", control });
  return (
    <div className="space-y-2">
      <Label htmlFor="denominacion">Denominación <span className="text-destructive">*</span></Label>
      <div className="relative">
        <FileText className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input id="denominacion" placeholder="Nombre del proyecto" className="pl-10" {...field} />
      </div>
      {fieldState.error && <p className="text-xs text-destructive">{fieldState.error.message}</p>}
    </div>
  );
}

function NombrePropietarioField({ control }: { control: Control<EdificacionesFormData> }) {
  const { field, fieldState } = useController({ name: "nombre_propietario", control });
  return (
    <div className="space-y-2">
      <Label htmlFor="nombre_propietario">Propietario <span className="text-destructive">*</span></Label>
      <div className="relative">
        <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input id="nombre_propietario" placeholder="Nombre del propietario" className="pl-10" {...field} />
      </div>
      {fieldState.error && <p className="text-xs text-destructive">{fieldState.error.message}</p>}
    </div>
  );
}

function DireccionField({ control }: { control: Control<EdificacionesFormData> }) {
  const { field, fieldState } = useController({ name: "direccion", control });
  return (
    <div className="space-y-2 md:col-span-2">
      <Label htmlFor="direccion">Dirección <span className="text-destructive">*</span></Label>
      <div className="relative">
        <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input id="direccion" placeholder="Dirección del proyecto" className="pl-10" {...field} />
      </div>
      {fieldState.error && <p className="text-xs text-destructive">{fieldState.error.message}</p>}
    </div>
  );
}

function DistritoField({ register, control, errors }: { register: UseFormReturn<EdificacionesFormData>["register"]; control: UseFormReturn<EdificacionesFormData>["control"]; errors: FieldErrors<EdificacionesFormData> }) {
  const { data: distritos, isLoading } = useDistritos();

  return (
    <GenericInput
      field={{
        name: "distrito_id",
        label: "Distrito",
        type: "searchable-select",
        placeholder: isLoading ? "Cargando..." : "Seleccione distrito",
        icon: MapPin,
        required: true,
        options: (distritos || []).map((d) => ({
          label: `${d.nombre} - ${d.provincia_nombre}`,
          value: d.id,
        })),
        isLoading,
      }}
      register={register as never}
      control={control as never}
      errors={errors}
    />
  );
}

// ── Form Body ────────────────────────────────────────────────────────────

interface EdificacionesFormBodyProps {
  control: Control<EdificacionesFormData>;
  isSubmitting: boolean;
  methods: UseFormReturn<EdificacionesFormData>;
}

function EdificacionesFormBody({ control, isSubmitting, methods }: EdificacionesFormBodyProps) {
  const { formState: { errors }, register } = methods;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* ── Columna Izquierda: Trámite + Tarifas + Cotización ── */}
      <div className="space-y-4">
        {/* Datos del Trámite */}
        <div className="rounded-xl border border-border/50 bg-card p-4 space-y-4">
          <div className="flex items-center gap-2 border-b border-border/40 pb-2">
            <FileText className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold uppercase tracking-wide">Datos del Trámite</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <MunicipalidadField register={register} control={control} errors={errors} />
            <ExpedienteField control={control} />
            <div className="space-y-2">
              <MoneyInput
                name="valor_declarado"
                label="Valor Declarado (S/)"
                placeholder="S/ 0.00"
                control={control}
                required
                defaultValue={0}
              />
            </div>
            <ObservacionField control={control} />
          </div>
        </div>

        {/* Tarifas */}
        <TarifasPorcentajePrimeraRevisionSmartField methods={methods} />

        {/* Cotización */}
        <CotizacionPorcentajeSmartField methods={methods} />
      </div>

      {/* ── Columna Derecha: Entidad + Proyecto ── */}
      <div className="space-y-4">
        <div className="rounded-xl border border-border/50 bg-card p-4 space-y-4">
          <div className="flex items-center gap-2 border-b border-border/40 pb-2">
            <FileText className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold uppercase tracking-wide">Datos del Proyecto</h3>
          </div>

          {/* Entidad primero (RENIEC/SUNAT) + Nombre Propietario al lado */}
          <EntidadLookupField
            control={control as never}
            errors={errors}
            razonSocialSideSlot={
              <NombrePropietarioField control={control} />
            }
          />

          {/* Denominación + Dirección + Distrito */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <DenominacionField control={control} />
            <DistritoField register={register} control={control} errors={errors} />
            <DireccionField control={control} />
          </div>
        </div>
      </div>
    </div>
  );
}
