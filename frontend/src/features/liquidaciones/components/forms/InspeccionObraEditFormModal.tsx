"use client";

import {
  Building2,
  FilePenLine,
  FileText,
  HardHat,
  MapPin,
  Phone,
} from "lucide-react";
import type { FieldErrors } from "react-hook-form";
import { useController } from "react-hook-form";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { notify } from "@/errors";
import { useDistritos } from "../../hooks/useDistritos";
import { useEditarInspeccionObra } from "../../hooks/useEditarInspeccionObra";
import { useMunicipalidades } from "../../hooks/useMunicipalidades";
import type { ContactoInline } from "../../schemas/liquidacion-form-base.schema";
import type { LiquidacionInspeccionObraListItem } from "../../schemas/liquidacion-inspeccion-obra.schema";
import {
  type VisitasFormData,
  visitasFormSchema,
} from "../../schemas/liquidacion-visitas-form.schema";
import { EntidadLookupField } from "./EntidadLookupSmartField";
import { SeleccionarInspectorModal } from "./SeleccionarInspectorModal";
import { TarifasVisitasNuevaRevisionSmartField } from "./TarifasVisitasNuevaRevisionSmartField";
import { useCallback, useMemo, useState } from "react";

interface InspeccionObraEditFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  item: LiquidacionInspeccionObraListItem;
  onSuccess?: () => void;
}

const toContactoInline = (
  contacto: LiquidacionInspeccionObraListItem["liquidacion_general"]["contacto"],
): ContactoInline | null => {
  if (!contacto?.nombres) return null;
  return {
    nombres: contacto.nombres,
    apellidos: contacto.apellidos ?? undefined,
    dni: contacto.dni ?? undefined,
    cargo: contacto.cargo ?? undefined,
    telefono: contacto.telefono ?? undefined,
    celular: contacto.celular ?? undefined,
    email: contacto.email ?? undefined,
  };
};

// ── Field helpers (replicated from LiquidacionFormBodyBase) ──────────────────

function ExpedienteField({ control }: { control: any }) {
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

function RetencionField({ control }: { control: any }) {
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

function ObservacionField({ control }: { control: any }) {
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

function DenominacionField({ control }: { control: any }) {
  const { field, fieldState } = useController({
    name: "denominacion",
    control,
    defaultValue: "",
  });
  return (
    <div className="space-y-2">
      <Label htmlFor="denominacion">Denominación</Label>
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

function NombrePropietarioInline({ control }: { control: any }) {
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

function DireccionField({ control }: { control: any }) {
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
      <Textarea
        id="direccion"
        placeholder="Dirección del proyecto"
        rows={2}
        {...field}
      />
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

function buildInitialData(
  item: LiquidacionInspeccionObraListItem,
): VisitasFormData {
  const { liquidacion_general: lg, liquidacion_tipo: lt } = item;

  // Normalizar la categoría que viene del backend ("1" -> "C1", 1 -> "C1")
  // El backend puede enviar el número 1 o la cadena "1" — ambos deben normalizarse
  let catNormalizada = String(lt.categoria);
  if (
    catNormalizada === "1" ||
    catNormalizada === "2" ||
    catNormalizada === "3" ||
    catNormalizada === "4"
  ) {
    catNormalizada = `C${catNormalizada}`;
  }
  const categoriaValida = ["C1", "C2", "C3", "C4"].includes(
    catNormalizada ?? "",
  )
    ? catNormalizada
    : undefined;

  return {
    denominacion: lg.denominacion_de_proyecto ?? "",
    municipalidad_id: lg.municipalidad?.id ?? "",
    expediente: lg.expediente ?? "",
    observacion: lg.observacion ?? "",
    retencion: lg.retencion ?? false,
    nombre_propietario: lg.proyecto.nombre_propietario,
    direccion: lg.proyecto.direccion,
    distrito_id: lg.proyecto.distrito?.id ?? "",
    urbanizacion: lg.proyecto.urbanizacion ?? undefined,
    entidad_tipo_documento:
      lg.proyecto.entidad?.tipo_documento === "DNI" ? "DNI" : "RUC",
    entidad_numero_documento: lg.proyecto.entidad?.numero_documento ?? "",
    entidad_razon_social: lg.proyecto.entidad?.razon_social ?? "",
    cantidad_visitas: lt.cantidad_visitas,
    categoria: categoriaValida as VisitasFormData["categoria"],
    tarifa_visitas_id: lt.tarifa_aplicada_id,
  };
}

export function InspeccionObraEditFormModal({
  open,
  onOpenChange,
  item,
  onSuccess,
}: InspeccionObraEditFormModalProps) {
  const liquidacionId = item.liquidacion_general.id;
  const editarMutation = useEditarInspeccionObra(liquidacionId);

  const lg = item.liquidacion_general;
  const lt = item.liquidacion_tipo;

  // Contacto state (editable now — keep read-only for this PR, passed through on submit)
  const [contacto] = useState<ContactoInline | null>(() =>
    toContactoInline(lg.contacto),
  );

  // Inspector state
  const [inspectorModalOpen, setInspectorModalOpen] = useState(false);
  const [inspectorOperacionId, setInspectorOperacionId] = useState<
    string | null
  >(lt.inspectores?.[0]?.inspector_operacion_id ?? null);
  const [inspectorNombre] = useState<string>(
    lt.inspectores?.[0]?.perfil_ingeniero?.nombre_completo ?? "",
  );

  // Local state for the unified motor — mirrors form values via setValue
  const initialData = useMemo(() => buildInitialData(item), [item]);
  const [cantidadVisitas, setCantidadVisitas] = useState(
    initialData.cantidad_visitas,
  );
  const [categoria, setCategoria] = useState(initialData.categoria);
  const [tarifaVisitasId, setTarifaVisitasId] = useState<string | null>(
    initialData.tarifa_visitas_id || null,
  );

  const handleSubmit = useCallback(
    async (data: VisitasFormData) => {
      try {
        await editarMutation.mutateAsync({
          ...data,
          contacto: contacto ?? undefined,
          inspector_operacion_id: inspectorOperacionId ?? undefined,
        });
        notify.success("Liquidación editada correctamente");
        onSuccess?.();
      } catch {
        // Error handled by mutation
      }
    },
    [editarMutation, contacto, inspectorOperacionId, onSuccess],
  );

  return (
    <AppFormModal<VisitasFormData>
      open={open}
      onOpenChange={onOpenChange}
      title="Editar Liquidación — Inspección de Obra"
      eyebrow="Inspección de Obra"
      icon={<FilePenLine className="h-5 w-5 text-primary" />}
      primaryLabel="Guardar cambios"
      primaryLoadingLabel="Guardando..."
      primaryLoading={editarMutation.isPending}
      onPrimary={() => undefined}
      schema={visitasFormSchema}
      initialData={initialData}
      onSubmit={handleSubmit}
      size="lg"
    >
      {({ methods }) => {
        const {
          register,
          control,
          formState: { errors },
        } = methods;

        return (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* ── Columna Izquierda (lg:col-span-5): Datos editables ── */}
              <div className="lg:col-span-5 space-y-4">
                {/* Datos del Trámite */}
                <div className="rounded-xl border border-border/50 bg-card p-4 space-y-4">
                  <div className="flex items-center gap-2 border-b border-border/40 pb-2">
                    <FileText className="h-4 w-4 text-primary" />
                    <h3 className="text-sm font-semibold uppercase tracking-wide">
                      Datos del Trámite
                    </h3>
                  </div>

                  <div className="flex flex-col gap-4">
                    {/* Municipalidad */}
                    <MunicipalidadField
                      register={register}
                      control={control}
                      errors={errors}
                    />

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {/* Expediente */}
                      <ExpedienteField control={control} />
                      {/* Retencion */}
                      <RetencionField control={control} />
                    </div>

                    {/* Observación */}
                    <ObservacionField control={control} />
                  </div>
                </div>

                {/* Datos del Proyecto */}
                <div className="rounded-xl border border-border/50 bg-card p-4 space-y-4">
                  <div className="flex items-center gap-2 border-b border-border/40 pb-2">
                    <Building2 className="h-4 w-4 text-primary" />
                    <h3 className="text-sm font-semibold uppercase tracking-wide">
                      Datos del Proyecto
                    </h3>
                  </div>

                  <EntidadLookupField
                    control={control as never}
                    errors={errors}
                    razonSocialSideSlot={
                      <NombrePropietarioInline control={control} />
                    }
                  />

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="sm:col-span-2">
                      <DenominacionField control={control} />
                    </div>
                    <DistritoField
                      register={register}
                      control={control}
                      errors={errors}
                    />
                    <div className="sm:col-span-2">
                      <DireccionField control={control} />
                    </div>
                  </div>

                  {/* Contacto principal (read-only in edit modal) */}
                  <div className="space-y-3 pt-2 border-t border-border/60">
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      <Phone className="h-3.5 w-3.5 text-primary/70" />
                      <span>Contacto Principal</span>
                      {contacto && (
                        <span className="inline-flex items-center rounded-full bg-primary/10 border border-primary/20 px-2 py-0.5 text-[9px] font-bold text-primary">
                          Agregado
                        </span>
                      )}
                    </div>

                    {contacto ? (
                      <div className="rounded-lg border border-border/60 bg-background px-3 py-2">
                        <p className="text-sm font-medium truncate">
                          {contacto.nombres} {contacto.apellidos}
                        </p>
                        <p className="text-xs text-muted-foreground truncate">
                          {[
                            contacto.dni ? `DNI ${contacto.dni}` : null,
                            contacto.telefono || null,
                            contacto.celular || null,
                            contacto.email || null,
                            contacto.cargo || null,
                          ]
                            .filter(Boolean)
                            .join(" · ") || "Sin datos"}
                        </p>
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground/70 italic">
                        Sin contacto principal registrado.
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* ── Columna Derecha (lg:col-span-7): Inspector + Cálculo ── */}
              <div className="lg:col-span-7 space-y-4">
                {/* Inspector Asignado */}
                <div className="rounded-xl border border-border/50 bg-card p-4 space-y-3">
                  <div className="flex items-center gap-2 border-b border-border/40 pb-2">
                    <HardHat className="h-4 w-4 text-primary" />
                    <h3 className="text-sm font-semibold uppercase tracking-wide">
                      Inspector Asignado
                    </h3>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setInspectorModalOpen(true)}
                    className="w-full gap-2"
                  >
                    <HardHat className="h-4 w-4" />
                    {inspectorNombre
                      ? `Inspector: ${inspectorNombre}`
                      : "Seleccionar inspector"}
                  </Button>
                </div>

                {/* Tarifa + Cálculo de Visitas */}
                <TarifasVisitasNuevaRevisionSmartField
                  cantidadVisitas={cantidadVisitas}
                  categoria={categoria}
                  tarifaVisitasId={tarifaVisitasId}
                  onCantidadVisitasChange={(v) => {
                    setCantidadVisitas(v);
                    methods.setValue("cantidad_visitas", v, {
                      shouldValidate: true,
                    });
                  }}
                  onCategoriaChange={(c) => {
                    setCategoria(c as VisitasFormData["categoria"]);
                    methods.setValue(
                      "categoria",
                      c as VisitasFormData["categoria"],
                      {
                        shouldValidate: true,
                      },
                    );
                  }}
                  onTarifaChange={(id) => {
                    setTarifaVisitasId(id);
                    methods.setValue("tarifa_visitas_id", id, {
                      shouldValidate: true,
                    });
                  }}
                  mode="edit"
                  liquidacionId={liquidacionId}
                />
              </div>
            </div>

            {/* Modal de selección de inspector */}
            <SeleccionarInspectorModal
              open={inspectorModalOpen}
              onOpenChange={setInspectorModalOpen}
              tipoLiquidacion={lg.tipo_liquidacion?.codigo ?? undefined}
              categoriaForm={categoria || null}
              selectedId={inspectorOperacionId ?? undefined}
              onSelect={(id) => {
                setInspectorOperacionId(id);
              }}
            />
          </>
        );
      }}
    </AppFormModal>
  );
}
