"use client";

import { Building2, FileText, MapPin, Phone, Plus, Trash2 } from "lucide-react";
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
import type { Control, FieldErrors, UseFormReturn } from "react-hook-form";
import { useController } from "react-hook-form";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useDistritos } from "../../hooks/useDistritos";
import { useMunicipalidades } from "../../hooks/useMunicipalidades";
import type { ContactoInline } from "../../schemas/liquidacion-form-base.schema";
import { EntidadLookupField } from "./EntidadLookupSmartField";

// ── Generic fields (useController pattern) ──────────────────────────────

function ExpedienteField({ control }: { control: Control<any> }) {
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

function MunicipalidadField({
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

function ObservacionField({ control }: { control: Control<any> }) {
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

function RetencionField({ control }: { control: Control<any> }) {
  const { field } = useController({
    name: "retencion",
    control,
    defaultValue: false,
  });
  return (
    <div className="flex items-center gap-3 rounded-lg border border-border/60 bg-background px-3 py-2.5">
      <Checkbox
        id="retencion"
        checked={!!field.value}
        onCheckedChange={(checked) => field.onChange(!!checked)}
      />
      <Label htmlFor="retencion" className="text-sm font-medium cursor-pointer">
        ¿La liquidación tiene retención?
      </Label>
    </div>
  );
}

function DenominacionField({ control }: { control: Control<any> }) {
  const { field, fieldState } = useController({
    name: "denominacion",
    control,
    defaultValue: "",
  });
  return (
    <div className="space-y-2">
      <Label htmlFor="denominacion">
        Denominación <span className="text-destructive">*</span>
      </Label>
      <div className="relative">
        <FileText className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          id="denominacion"
          placeholder="Nombre del proyecto"
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

function NombrePropietarioInline({ control }: { control: Control<any> }) {
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

function DireccionField({ control }: { control: Control<any> }) {
  const { field, fieldState } = useController({
    name: "direccion",
    control,
    defaultValue: "",
  });
  return (
    <div className="space-y-2">
      <Label htmlFor="direccion">
        Dirección <span className="text-destructive">*</span>
      </Label>
      <div className="relative">
        <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          id="direccion"
          placeholder="Dirección del proyecto"
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

function DistritoField({
  register,
  control,
  errors,
}: {
  register: any;
  control: any;
  errors: FieldErrors<any>;
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
  contacto: ContactoInline | null;
  onAddContacto: () => void;
  onRemoveContacto: () => void;
  /** Campo específico del motor (valor_declarado o area_solicitada) — va en el grid del trámite */
  tramiteField: ReactNode;
  /** Sección completa del motor (tarifas + cotización) — va debajo del trámite, ocupa todo el ancho */
  motorSection: ReactNode;
  /** Campos extra del tipo (p.ej. tipo_tramite) — se renderizan al inicio de "Datos del Proyecto" */
  proyectoFieldsExtra?: ReactNode;
}

export function LiquidacionFormBodyBase({
  control,
  methods,
  contacto,
  onAddContacto,
  onRemoveContacto,
  tramiteField,
  motorSection,
  proyectoFieldsExtra,
}: LiquidacionFormBodyBaseProps) {
  const {
    formState: { errors },
    register,
  } = methods;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
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
            <MunicipalidadField
              register={register}
              control={control}
              errors={errors}
            />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <ExpedienteField control={control} />
              {tramiteField}
            </div>
            <RetencionField control={control} />
            <ObservacionField control={control} />
          </div>
        </div>

        {/* Sección específica del motor (tarifas + cotización) — cada tipo la define */}
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

          {proyectoFieldsExtra && (
            <div className="space-y-4">{proyectoFieldsExtra}</div>
          )}

          <EntidadLookupField
            control={control as never}
            errors={errors}
            razonSocialSideSlot={<NombrePropietarioInline control={control} />}
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <DenominacionField control={control} />
            <DistritoField
              register={register}
              control={control}
              errors={errors}
            />
            <div className="sm:col-span-2">
              <DireccionField control={control} />
            </div>
          </div>

          {/* Contacto principal (singular) */}
          <div className="space-y-3 pt-2 border-t border-border/60">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <Phone className="h-3.5 w-3.5 text-primary/70" />
                <span>Contacto Principal</span>
                {contacto && (
                  <span className="inline-flex items-center rounded-full bg-primary/10 border border-primary/20 px-2 py-0.5 text-[9px] font-bold text-primary">
                    Agregado
                  </span>
                )}
              </div>
              {!contacto ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={onAddContacto}
                  className="h-8 gap-1 text-xs"
                >
                  <Plus className="h-3 w-3" />
                  Agregar
                </Button>
              ) : null}
            </div>

            {contacto ? (
              <div className="flex items-center justify-between gap-2 rounded-lg border border-border/60 bg-background px-3 py-2">
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">
                    {contacto.nombres} {contacto.apellidos}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">
                    {[contacto.cargo, contacto.email, contacto.celular]
                      .filter(Boolean)
                      .join(" · ") || "Sin datos"}
                  </p>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs"
                    onClick={onAddContacto}
                  >
                    Editar
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0 text-destructive hover:text-destructive"
                    onClick={onRemoveContacto}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground/70 italic">
                Sin contacto. Agrega el contacto principal de referencia.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
