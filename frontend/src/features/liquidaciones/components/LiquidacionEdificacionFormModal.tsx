"use client";

import { FileText, Banknote, MessageSquare, User, Plus, X, Building2, Calculator } from "lucide-react";
import { useCallback, useState, useRef, useEffect } from "react";
import type { z } from "zod";
import { Button } from "@/components/ui/button";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { useCrearPrimeraRevision } from "../hooks/useCrearLiquidacion";
import { useCotizacionPrimeraRevision } from "../hooks/useCotizacion";
import { useRevisionesVigentes } from "../hooks/useRevisionesVigentes";
import { useVariablesFinancieras } from "../hooks/useVariablesFinancieras";
import { useMunicipalidades } from "../hooks/useMunicipalidades";
import { liquidacionEdificacionFormSchema } from "../schemas/liquidacion-edificaciones-form.schema";
import type {
  LiquidacionEdificacionFormModalProps,
  LiquidacionEdificacionSubmitData,
  ProyectoResumen,
} from "../types/liquidacion-edificaciones-form.types";
import type { ProyectistaResult } from "../types/proyectista";
import type { CotizacionQuote } from "../types/liquidacion-edificaciones";
import { ProyectoFormModal } from "./ProyectoFormModal";
import { ProyectistaFormModal } from "./ProyectistaFormModal";
import { ProyectoSelectorSection } from "./ProyectoSelectorSection";
import { RevisionesVigentesTable } from "./RevisionesVigentesTable";
import { VariablesFinancierasCard } from "./VariablesFinancierasCard";
import { CotizacionSection } from "./CotizacionSection";

const formSchema = liquidacionEdificacionFormSchema;

type FormData = z.infer<typeof formSchema>;

const TIPO_TRAMITE_OPTIONS = [
  { value: "OBRA_NUEVA", label: "Obra nueva" },
  { value: "DEMOLICION", label: "Demolición" },
  { value: "AMPLIACION", label: "Ampliación" },
  { value: "REMODELACION", label: "Remodelación" },
  { value: "MODIFICACION_LICENCIA", label: "Modificación de licencia" },
] as const;

function formatMunicipalidadLabel(municipalidad: {
  codigo?: string | null;
  nombre: string;
  provincia?: { nombre: string } | null;
  distrito?: { nombre: string } | null;
}) {
  const codigo = municipalidad.codigo;
  const nombre = municipalidad.nombre;
  const provincia = municipalidad.provincia?.nombre;
  const distrito = municipalidad.distrito?.nombre;

  // Base: CODIGO - NOMBRE or just NOMBRE
  let label = codigo ? `${codigo} - ${nombre}` : nombre;

  // Append location info with proper formatting
  if (provincia && distrito) {
    label += ` - ${provincia} / ${distrito}`;
  } else if (provincia) {
    label += ` - ${provincia}`;
  } else if (distrito) {
    label += ` - ${distrito}`;
  }

  return label;
}

export function LiquidacionEdificacionFormModal({
  open,
  onOpenChange,
  onSuccess,
}: LiquidacionEdificacionFormModalProps) {
  // Child modal state
  const [showProyectoModal, setShowProyectoModal] = useState(false);
  const [showProyectistaModal, setShowProyectistaModal] = useState(false);

  // Selected proyecto (local state for display, synced to form)
  const [selectedProyecto, setSelectedProyecto] = useState<
    ProyectoResumen | undefined
  >();

  // Selected proyectistas (local state for multi-select)
  const [selectedProyectistas, setSelectedProyectistas] = useState<
    ProyectistaResult[]
  >([]);

  // Ref to store submit handler configured with methods from render prop
  const submitHandlerRef = useRef<{
    (data: FormData): Promise<void>;
  } | null>(null);

  // Data hooks
  const { data: variablesFinancieras, isLoading: isLoadingVariables } =
    useVariablesFinancieras();
  const { data: revisionesVigentes, isLoading: isLoadingRevisiones } =
    useRevisionesVigentes();
  const { data: municipalidades, isLoading: isLoadingMunicipalidades } =
    useMunicipalidades();
  const crearMutation = useCrearPrimeraRevision();

  // Cotización state (clear when form fields change)
  const [cotizacionQuote, setCotizacionQuote] = useState<CotizacionQuote | null>(null);

  // Sync proyecto_public_id when selectedProyecto changes
  const handleProyectoSaved = useCallback((proyecto: ProyectoResumen) => {
    setSelectedProyecto(proyecto);
    setShowProyectoModal(false);
  }, []);

  // Handle proyectista saved (created or selected)
  const handleProyectistaSaved = useCallback((proyectista: ProyectistaResult) => {
    // Add to selected if not already selected
    setSelectedProyectistas((prev) => {
      if (prev.some((p) => p.id === proyectista.id)) {
        return prev;
      }
      return [...prev, proyectista];
    });
    setShowProyectistaModal(false);
  }, []);

  // Remove proyectista from selection
  const handleRemoveProyectista = useCallback((proyectistaId: string) => {
    setSelectedProyectistas((prev) => prev.filter((p) => p.id !== proyectistaId));
  }, []);

  return (
    <>
      <AppFormModal<FormData>
        open={open}
        onOpenChange={onOpenChange}
        title="Nueva Liquidación"
        description="Registra una nueva liquidación de edificación"
        eyebrow="Edificaciones"
        icon={<FileText className="h-5 w-5 text-primary" />}
        primaryLabel="Crear Liquidación"
        primaryLoadingLabel="Creando..."
        primaryLoading={crearMutation.isPending}
        onPrimary={() => {}}
        schema={formSchema}
        initialData={{
          municipalidad_id: "",
          tipo_tramite: "OBRA_NUEVA",
          valor_proyecto: 0,
          observacion: "",
          revisiones_ids: [],
          proyectistas_ids: [],
          proyecto_public_id: "",
        }}
        onSubmit={(data) => submitHandlerRef.current?.(data)}
        size="lg"
        preventClose={crearMutation.isPending}
      >
        {({ methods, isSubmitting }) => {
          // Configure submit handler with access to methods.setError
          submitHandlerRef.current = async (data: FormData) => {
            if (!selectedProyecto) {
              methods.setError("proyecto_public_id", {
                type: "manual",
                message: "Debe seleccionar un proyecto",
              });
              return;
            }

            const submitData: LiquidacionEdificacionSubmitData = {
              proyecto_public_id: data.proyecto_public_id,
              municipalidad_id: data.municipalidad_id,
              tipo_tramite: data.tipo_tramite,
              valor_proyecto: data.valor_proyecto,
              observacion: data.observacion || undefined,
              revisiones_ids: data.revisiones_ids || [],
              proyectistas_ids: selectedProyectistas.map((p) => p.id),
            };

            await crearMutation.mutateAsync(submitData);
            onSuccess?.();
            // Reset local state
            setSelectedProyecto(undefined);
            setSelectedProyectistas([]);
          };

          const {
            register,
            control,
            formState: { errors },
            watch,
            setValue,
          } = methods;

          const selectedRevisionIds =
            (watch("revisiones_ids") as string[]) || [];
          const selectedMunicipalidadId = watch("municipalidad_id");

          // Sync proyecto_public_id when selectedProyecto changes
          if (
            selectedProyecto &&
            watch("proyecto_public_id") !== selectedProyecto.public_id
          ) {
            setValue("proyecto_public_id", selectedProyecto.public_id, {
              shouldValidate: true,
            });
          }

          const handleRevisionToggle = (revisionId: string) => {
            const current = selectedRevisionIds;
            const updated = current.includes(revisionId)
              ? current.filter((id) => id !== revisionId)
              : [...current, revisionId];
            setValue("revisiones_ids", updated, { shouldValidate: true });
          };

          // Cotizacion hook inside render prop (needs access to watch)
          const cotizacionMutation = useCotizacionPrimeraRevision();

          // Clear cotizacion when relevant form fields change
          const watchedValues = watch([
            "proyecto_public_id",
            "valor_proyecto",
            "revisiones_ids",
          ]);
          useEffect(() => {
            // Clear quote if any watched field changes (form was modified after quote)
            if (cotizacionQuote !== null) {
              setCotizacionQuote(null);
            }
          }, [watchedValues, cotizacionQuote]);

          // Handle cotizar button click
          const handleCotizar = useCallback(async () => {
            const proyectoPublicId = watch("proyecto_public_id");
            const valorProyecto = watch("valor_proyecto");

            if (!proyectoPublicId || !valorProyecto || valorProyecto <= 0) {
              return;
            }

            try {
              const result = await cotizacionMutation.mutateAsync({
                proyecto_public_id: proyectoPublicId,
                valor_proyecto: valorProyecto,
              });
              setCotizacionQuote(result.data);
            } catch {
              // Error is handled by the mutation
            }
          }, [cotizacionMutation, watch]);

          return (
            <div className="space-y-6">
              {/* Variables Financieras Info Banner */}
              <VariablesFinancierasCard
                variables={variablesFinancieras}
                isLoading={isLoadingVariables}
              />

              {/* Sección: Datos de Liquidación */}
              <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4">
                <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
                  <Banknote className="h-4 w-4" />
                  <h3 className="text-sm font-semibold uppercase tracking-wide">
                    Datos de Liquidación
                  </h3>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <SearchableSelect
                    id="municipalidad_id"
                    label="Municipalidad"
                    value={selectedMunicipalidadId || null}
                    onValueChange={(value) =>
                      setValue("municipalidad_id", value ?? "", {
                        shouldValidate: true,
                      })
                    }
                    options={(municipalidades || []).map((municipalidad) => ({
                      value: municipalidad.id,
                      label: formatMunicipalidadLabel(municipalidad),
                    }))}
                    placeholder={
                      isLoadingMunicipalidades
                        ? "Cargando municipalidades..."
                        : "Seleccione municipalidad"
                    }
                    icon={Building2}
                    disabled={isLoadingMunicipalidades}
                    error={!!errors.municipalidad_id}
                    errorMessage={errors.municipalidad_id?.message as string | undefined}
                  />

                  <GenericInput
                    field={{
                      name: "tipo_tramite",
                      label: "Tipo de Trámite",
                      type: "select",
                      required: true,
                      placeholder: "Seleccione tipo de trámite",
                      icon: FileText,
                      options: [...TIPO_TRAMITE_OPTIONS],
                    }}
                    register={register as any}
                    control={control as any}
                    errors={errors}
                  />
                </div>

                <GenericInput
                  field={{
                    name: "valor_proyecto",
                    label: "Valor del Proyecto (S/)",
                    type: "number",
                    required: true,
                    placeholder: "Ej: 500000",
                    icon: Banknote,
                  }}
                  register={register as any}
                  control={control as any}
                  errors={errors}
                />

                <GenericInput
                  field={{
                    name: "observacion",
                    label: "Observación",
                    type: "textarea",
                    placeholder: "Observaciones adicionales...",
                    icon: MessageSquare,
                  }}
                  register={register as any}
                  control={control as any}
                  errors={errors}
                />
              </div>

              {/* Hidden field for proyecto_public_id validation */}
              <input type="hidden" {...register("proyecto_public_id")} />
              {errors.proyecto_public_id && (
                <p className="text-sm text-destructive">
                  {errors.proyecto_public_id.message as string}
                </p>
              )}

              {/* Sección: Proyecto */}
              <ProyectoSelectorSection
                proyecto={selectedProyecto}
                onOpenProyectoModal={() => setShowProyectoModal(true)}
              />

              {/* Sección: Proyectistas */}
              <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4">
                <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
                  <User className="h-4 w-4" />
                  <h3 className="text-sm font-semibold uppercase tracking-wide">
                    Proyectistas
                  </h3>
                </div>

                {/* Selected proyectistas */}
                {selectedProyectistas.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {selectedProyectistas.map((proyectista) => (
                      <div
                        key={proyectista.id}
                        className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-secondary/50 border border-border"
                      >
                        <span className="text-sm font-medium">
                          {proyectista.nombres} {proyectista.apellidos}
                        </span>
                        {proyectista.cip && (
                          <span className="text-xs text-muted-foreground">
                            CIP: {proyectista.cip}
                          </span>
                        )}
                        <button
                          type="button"
                          onClick={() => handleRemoveProyectista(proyectista.id)}
                          className="ml-1 hover:bg-destructive/10 rounded p-0.5"
                        >
                          <X className="h-3 w-3 text-muted-foreground hover:text-destructive" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {selectedProyectistas.length === 0 && (
                  <p className="text-sm text-muted-foreground italic">
                    No hay proyectistas seleccionados
                  </p>
                )}

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowProyectistaModal(true)}
                  className="gap-2 h-9 rounded-lg"
                >
                  <Plus className="h-4 w-4" />
                  Agregar Proyectista
                </Button>
              </div>

              {/* Sección: Revisiones/Especialidades */}
              <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4">
                <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
                  <FileText className="h-4 w-4" />
                  <h3 className="text-sm font-semibold uppercase tracking-wide">
                    Revisiones / Especialidades
                  </h3>
                </div>

                <RevisionesVigentesTable
                  revisiones={revisionesVigentes || []}
                  selectedIds={selectedRevisionIds}
                  onToggleRevision={handleRevisionToggle}
                  isLoading={isLoadingRevisiones}
                />
              </div>

              {/* Sección: Cotizar / Resumen de Cálculo */}
              <CotizacionSection
                quote={cotizacionQuote}
                isLoading={cotizacionMutation.isPending}
                onCotizar={handleCotizar}
                hasErrors={Object.keys(errors).length > 0}
              />
            </div>
          );
        }}
      </AppFormModal>

      {/* Child Modal: Proyecto */}
      <ProyectoFormModal
        open={showProyectoModal}
        onOpenChange={setShowProyectoModal}
        onSaved={handleProyectoSaved}
      />

      {/* Child Modal: Proyectista */}
      <ProyectistaFormModal
        open={showProyectistaModal}
        onOpenChange={setShowProyectistaModal}
        onSaved={handleProyectistaSaved}
      />
    </>
  );
}
