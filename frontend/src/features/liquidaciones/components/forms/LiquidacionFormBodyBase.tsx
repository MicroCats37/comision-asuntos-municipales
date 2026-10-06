"use client";

import { Building2, FileText, MapPin } from "lucide-react";
import type { ReactNode } from "react";
/**
 * LiquidacionFormBodyBase — Body GENERAL reutilizable para los 6 forms de liquidación.
 *
 * Renderiza UNA vez:
 *  - Columna izquierda: Datos del Trámite (municipalidad, expediente, retención, observación)
 *    + slot `specificSection` (la parte del motor: tarifas + cotización)
 *  - Columna derecha: Datos del Proyecto (entidad, denominación, distrito, dirección) + Contacto
 *
 * Cada FormModal de tipo solo pasa el schema + los Smart Fields específicos del motor.
 */
import { useEffect } from "react";
import type { Control, FieldErrors, UseFormReturn } from "react-hook-form";
import { useController } from "react-hook-form";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useDistritos } from "../../hooks/useDistritos";
import { useMunicipalidades } from "../../hooks/useMunicipalidades";
import { ContactoSmartField } from "./ContactoSmartField";
import { EntidadLookupField } from "./EntidadLookupSmartField";

// ── Generic fields (useController pattern) ──────────────────────────────

export function ExpedienteField({ control }: { control: Control<any> }) {
  const { field, fieldState } = useController({
    name: "expediente",
    control,
    defaultValue: "",
  });
  return (
    <div className="space-y-2">
      <Label htmlFor="expediente">Expediente</Label>
      <div className="relative">
        <FileText className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          id="expediente"
          placeholder="Número de expediente"
          className="pl-10 w-full"
          {...field}
        />
      </div>
      {fieldState.error && (
        <p className="text-xs text-destructive">{fieldState.error.message}</p>
      )}
    </div>
  );
}

export function MunicipalidadField({
  register,
  control,
  errors,
}: {
  register: any;
  control: any;
  errors: FieldErrors<any>;
}) {
  const { data: municipalidades, isLoading } = useMunicipalidades();
  return (
    <GenericInput
      field={{
        name: "municipalidad_id",
        label: "Municipalidad",
        type: "searchable-select",
        containerClassName: "sm:col-span-1",
        placeholder: isLoading ? "Cargando..." : "Seleccione municipalidad",
        icon: Building2,
        required: true,
        options: (municipalidades || []).map((m) => ({
          label: m.codigo ? `${m.codigo} - ${m.nombre}` : m.nombre,
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

export function ObservacionField({ control }: { control: Control<any> }) {
  const { field } = useController({
    name: "observacion",
    control,
    defaultValue: "",
  });
  return (
    <div className="space-y-2">
      <Label htmlFor="observacion">Observación</Label>
      <Textarea
        id="observacion"
        placeholder="Observaciones adicionales (opcional)"
        rows={2}
        {...field}
      />
    </div>
  );
}

export function RetencionField({ control }: { control: Control<any> }) {
  const { field } = useController({
    name: "retencion",
    control,
    defaultValue: false,
  });
  return (
    <div className="space-y-2">
      <Label>Retención</Label>
      <div className="flex items-center gap-3 rounded-lg border border-border/60 bg-background px-3 h-8">
        <Checkbox
          id="retencion"
          checked={!!field.value}
          onCheckedChange={(checked) => field.onChange(!!checked)}
        />
        <Label
          htmlFor="retencion"
          className="text-sm font-medium cursor-pointer"
        >
          ¿La liquidación tiene retención?
        </Label>
      </div>
    </div>
  );
}

export function DenominacionField({
  control,
  disabled,
}: {
  control: Control<any>;
  disabled?: boolean;
}) {
  const { field, fieldState } = useController({
    name: "denominacion",
    control,
    defaultValue: "",
    disabled,
  });
  return (
    <div className="space-y-2">
      <Label htmlFor="denominacion">Denominación</Label>
      <div className="relative">
        <FileText className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          id="denominacion"
          placeholder="NOMBRE DEL PROYECTO"
          className="pl-10 w-full uppercase"
          disabled={field.disabled}
          value={field.value ?? ""}
          onChange={(e) => {
            // Forzar UPPER CASE en cada keystroke para mantener consistencia en BD y UI
            field.onChange(e.target.value.toUpperCase());
          }}
          onBlur={field.onBlur}
          name={field.name}
          ref={field.ref}
        />
      </div>
      {fieldState.error && (
        <p className="text-xs text-destructive">{fieldState.error.message}</p>
      )}
    </div>
  );
}

export function UrbanizacionField({
  control,
  disabled,
}: {
  control: Control<any>;
  disabled?: boolean;
}) {
  const { field } = useController({
    name: "urbanizacion",
    control,
    defaultValue: "",
    disabled,
  });
  return (
    <div className="space-y-2">
      <Label htmlFor="urbanizacion">Urbanización</Label>
      <div className="relative">
        <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          id="urbanizacion"
          placeholder="Nombre de la urbanización (opcional)"
          className="pl-10 w-full"
          disabled={field.disabled}
          {...field}
        />
      </div>
    </div>
  );
}

export function NombrePropietarioInline({
  control,
}: {
  control: Control<any>;
}) {
  const { field } = useController({
    name: "nombre_propietario",
    control,
    defaultValue: "",
  });
  return (
    <div className="space-y-2">
      <Label htmlFor="nombre_propietario">
        Propietario <span className="text-destructive">*</span>
      </Label>
      <Input
        id="nombre_propietario"
        placeholder="Nombre del propietario"
        className="w-full"
        {...field}
      />
    </div>
  );
}

export function DireccionField({
  control,
  disabled,
}: {
  control: Control<any>;
  disabled?: boolean;
}) {
  const { field, fieldState } = useController({
    name: "direccion",
    control,
    defaultValue: "",
    disabled,
  });
  return (
    <div className="space-y-2">
      <Label htmlFor="direccion">
        Dirección <span className="text-destructive">*</span>
      </Label>
      <Textarea
        id="direccion"
        placeholder="Dirección del proyecto"
        rows={2}
        disabled={field.disabled}
        {...field}
      />
      {fieldState.error && (
        <p className="text-xs text-destructive">{fieldState.error.message}</p>
      )}
    </div>
  );
}

export function DistritoField({
  register,
  control,
  errors,
  disabled,
}: {
  register: any;
  control: any;
  errors: FieldErrors<any>;
  disabled?: boolean;
}) {
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
          label: `${d.nombre} - ${d.provinciaNombre}`,
          value: d.id,
        })),
        isLoading,
        disabled,
      }}
      register={register as never}
      control={control as never}
      errors={errors}
    />
  );
}

// ── Base Body ───────────────────────────────────────────────────────────

interface LiquidacionFormBodyBaseProps {
  control: Control<any>;
  methods: UseFormReturn<any>;
  /** Campo específico del motor (valor_declarado o area_solicitada) — va en el grid del trámite */
  tramiteField: ReactNode;
  /** Sección completa del motor (tarifas + cotización) — se renderiza FUERA del grid 2 columnas,
   *  ocupando todo el ancho del modal. Esto permite que las especialidades se distribuyan mejor. */
  motorSection: ReactNode;
  /** Campos extra del tipo (p.ej. tipo_tramite) — se renderizan al inicio de "Datos del Proyecto" */
  proyectoFieldsExtra?: ReactNode;
  /** Solo Habilitación Urbana y Mecánica de Suelos: renderiza el campo urbanización */
  showUrbanizacion?: boolean;
  /** Sección de valores actuales ya calculados (subtotal/total) — se renderiza al final de la columna izquierda */
  valoresActualesSection?: ReactNode;
  /** When false, project fields are visually disabled and excluded from PATCH payload (revisions > 1) */
  canEditProyecto?: boolean;
}

export function LiquidacionFormBodyBase({
  control,
  methods,
  tramiteField,
  motorSection,
  proyectoFieldsExtra,
  showUrbanizacion = false,
  valoresActualesSection,
  canEditProyecto = true,
}: LiquidacionFormBodyBaseProps) {
  const {
    formState: { errors },
    register,
    watch,
    setValue,
  } = methods;

  const { data: municipalidades } = useMunicipalidades();
  const municipalidadId = watch("municipalidad_id");
  const currentDistritoId = watch("distrito_id");

  // Autofill distrito when municipalidad_id changes and the selected municipalidad has a distrito.
  useEffect(() => {
    if (!canEditProyecto) return;
    if (!municipalidadId) return;

    // Do not overwrite a manual selection or pre-existing edit data.
    if (currentDistritoId) return;

    const selected = municipalidades?.find((m) => m.id === municipalidadId);
    if (selected?.distrito?.id) {
      setValue("distrito_id", selected.distrito.id, { shouldValidate: true });
    }
    // If municipalidad has no distrito, do nothing — keep current distrito list available.
  }, [
    municipalidadId,
    currentDistritoId,
    municipalidades,
    canEditProyecto,
    setValue,
  ]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* ── Columna Izquierda: Trámite + Motor ── */}
      <div className="space-y-4">
        {/* Datos del Trámite */}
        <div className="rounded-xl border border-border/50 bg-card p-4 space-y-4">
          <div className="flex items-center gap-2 border-b border-border/40 pb-2">
            <FileText className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold uppercase tracking-wide">
              Datos del Trámite
            </h3>
          </div>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <MunicipalidadField
                register={register}
                control={control}
                errors={errors}
              />
              <ExpedienteField control={control} />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {tramiteField}
              <RetencionField control={control} />
            </div>
            <ObservacionField control={control} />
          </div>
        </div>

        {/* Sección específica del motor (tarifas + cotización) — cada tipo la define */}
        {valoresActualesSection}
        {motorSection}
      </div>

      {/* ── Columna Derecha: Entidad + Proyecto ── */}
      <div className="space-y-4">
        <div className="rounded-xl border border-border/50 bg-card p-4 space-y-4">
          <div className="flex items-center gap-2 border-b border-border/40 pb-2">
            <FileText className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold uppercase tracking-wide">
              Datos del Proyecto
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {proyectoFieldsExtra ? (
              <>
                <div className="sm:col-span-1">{proyectoFieldsExtra}</div>
                <div className="sm:col-span-1">
                  <DenominacionField
                    control={control}
                    disabled={!canEditProyecto}
                  />
                </div>
              </>
            ) : (
              <div className="sm:col-span-2">
                <DenominacionField
                  control={control}
                  disabled={!canEditProyecto}
                />
              </div>
            )}
          </div>

          <EntidadLookupField
            control={control as never}
            errors={errors}
            disabled={!canEditProyecto}
            razonSocialSideSlot={<NombrePropietarioInline control={control} />}
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {showUrbanizacion && (
              <div className="sm:col-span-2">
                <UrbanizacionField
                  control={control}
                  disabled={!canEditProyecto}
                />
              </div>
            )}
            <DistritoField
              register={register}
              control={control}
              errors={errors}
              disabled={!canEditProyecto}
            />
            <div className="sm:col-span-2">
              <DireccionField control={control} disabled={!canEditProyecto} />
            </div>
          </div>

          {/* Contacto principal (singular) — SmartField RHF-bound */}
          <ContactoSmartField methods={methods} />
        </div>
      </div>
    </div>
  );
}
