"use client";

/**
 * LiquidacionImpactoVialSingleFormModal — Single continuous form for Impacto Vial.
 * Clone of LiquidacionEdificacionesSingleFormModal with IV-specific module substitutions.
 *
 * UI/UX Redesign (this pass):
 * - Desktop: proportional grid-areas layout
 *   - Top row: Liquidación (2/3) | Cotización (1/3)
 *   - Bottom row: Proyecto (left) | Contactos (right)
 * - Mobile: fully stacked vertical flow
 * - Proyecto: inline creation only (no search-by-id path)
 * - Proyectistas: REMOVED from this form
 * - Cotización: reactive/automatic — fires via useEffect when inputs change (no button)
 * - Smart MoneyInput for amount fields
 * - No hardcoded heights — content-driven modal sizing
 *
 * Architecture preserved:
 * - Zustand store (useImpactoVialStepperStore): proyecto, contactos, cotización, tarifas
 * - React Hook Form: liquidacion fields
 * - Child modals: ContactoFormModal, InstitucionFormModal, PersonaNaturalFormModal
 */

import {
  Banknote,
  Building2,
  Calculator,
  CheckCircle2,
  FileText,
  Loader2,
  MapPin,
  MessageSquare,
  Truck,
  User,
  X,
} from "lucide-react";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { DefaultValues } from "react-hook-form";
import { useForm, useWatch } from "react-hook-form";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { MoneyInput } from "@/components/genericForm/inputs/MoneyInput";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { GenericForm } from "@/components/genericForm/GenericForm";
import { notify } from "@/errors";
import { useCrearImpactoVialPrimeraRevision } from "../hooks/useImpactoVial";
import { useCotizarImpactoVialPrimeraRevision } from "../hooks/useImpactoVial";
import { useMunicipalidades } from "../hooks/useMunicipalidades";
import { useRevisionesVigentesIV } from "../hooks/useRevisionesVigentesIV";
import { useVariablesFinancieras } from "../hooks/useVariablesFinancieras";
import {
  useImpactoVialStepperStore,
} from "../store/stepper-ui-store-factory";
import type { ContactoInline } from "../types/contacto";
import type { CrearImpactoVialPrimeraRevisionIn } from "../types/liquidacion-impacto-vial.types";
import type { CrearImpactoVialResponse } from "../types/liquidacion-impacto-vial.types";
import { liquidacionEdificacionFormSchema } from "../schemas/liquidacion-edificaciones-form.schema";
import { ContactoFormModal } from "./ContactoFormModal";
import { CotizacionSection } from "./CotizacionSection";
import { DatosDelProyectoSection } from "./DatosDelProyectoSection";
import { EntidadLookupField } from "./EntidadLookupField";
import { RevisionesVigentesTable } from "./RevisionesVigentesTable";

// ── Schema & Types ─────────────────────────────────────────────────────────────

const formSchema = liquidacionEdificacionFormSchema;
type FormData = z.infer<typeof formSchema>;

// ── Constants ───────────────────────────────────────────────────────────────────

const TIPO_TRAMITE_OPTIONS = [
  { value: "OBRA_NUEVA", label: "Obra nueva" },
  { value: "DEMOLICION", label: "Demolición" },
  { value: "AMPLIACION", label: "Ampliación" },
  { value: "REMODELACION", label: "Remodelación" },
  { value: "MODIFICACION_LICENCIA", label: "Modificación de licencia" },
  { value: "REINTEGRO", label: "Reintegro" },
   { value: "PROYECTO_CON_PLANTAS_TIPICAS", label: "Proyecto con plantas típicas" }
] as const;

const PROYECTO_CON_PLANTAS_TIPICAS_TIPO = "PROYECTO_CON_PLANTAS_TIPICAS";

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
  let label = codigo ? `${codigo} - ${nombre}` : nombre;
  if (provincia && distrito) {
    label += ` - ${provincia} / ${distrito}`;
  } else if (provincia) {
    label += ` - ${provincia}`;
  } else if (distrito) {
    label += ` - ${distrito}`;
  }
  return label;
}

// ── Props ─────────────────────────────────────────────────────────────────────

export interface LiquidacionImpactoVialSingleFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  onCreated?: (created: CrearImpactoVialResponse) => void;
}

// ── Component ──────────────────────────────────────────────────────────────────

export function LiquidacionImpactoVialSingleFormModal({
  open,
  onOpenChange,
  onSuccess,
  onCreated,
}: LiquidacionImpactoVialSingleFormModalProps) {
  // ── Store (stepper state — survives form re-renders) ───────────────────────
  const store = useImpactoVialStepperStore();
  const {
    proyectoInline,
    setProyectoInline,
    selectedContactos,
    cotizacion,
    selectedTarifasIds,
    setSelectedTarifasId,
    setCotizacionQuote,
    setCotizacionError,
  } = store;

  // ── Child modal state ────────────────────────────────────────────────────────
  const [showContactoModal, setShowContactoModal] = useState(false);
  const [editingContactoIndex, setEditingContactoIndex] = useState<number | null>(null);

  // ── RHF ─────────────────────────────────────────────────────────────────────
  const formMethods = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      municipalidad_id: "" as never,
      tipo_tramite: "OBRA_NUEVA" as never,
      valor_proyecto: 0 as never,
      expediente: "",
      valor_base_calculo: 0 as never,
      observacion: "",
      revisiones_ids: [] as never,
      proyectistas: [] as never,
      contactos: [] as never,
      delegados_ids: [] as never,
      proyecto_public_id: "",
    },
    mode: "onBlur",
  });

  const {
    control: liqControl,
    formState: { errors: liqErrors },
    getValues: liqGetValues,
    setValue: liqSetValue,
    watch: liqWatch,
    reset: liqReset,
  } = formMethods;

  // This modal intentionally has no Proyectistas UI, but the shared
  // Edificaciones schema still requires the array during RHF validation.
  useEffect(() => {
    if (!open) return;
    if (!Array.isArray(liqGetValues("proyectistas"))) {
      liqSetValue("proyectistas", [] as never, { shouldValidate: false });
    }
  }, [open, liqGetValues, liqSetValue]);

  // ── Data hooks ───────────────────────────────────────────────────────────────
  const { data: variablesFinancieras, isLoading: isLoadingVariables } =
    useVariablesFinancieras();
  const { data: municipalidades, isLoading: isLoadingMunicipalidades } =
    useMunicipalidades();

  // ── Watched values (minimal — only what queries need) ──────────────────────
  const watchedTipoTramite = liqWatch("tipo_tramite");
  const watchedValorProyecto = liqWatch("valor_proyecto");
  const watchedValorBaseCalculo = liqWatch("valor_base_calculo");
  const isPlantasTipicas = watchedTipoTramite === PROYECTO_CON_PLANTAS_TIPICAS_TIPO;

  // ── Proyecto inline sync: watch RHF fields → store (stepper pattern) ───────
  const watchedProyDenominacion = useWatch({ control: liqControl as never, name: "proy_denominacion" });
  const watchedProyDireccion = useWatch({ control: liqControl as never, name: "proy_direccion" });
  const watchedProyNombrePropietario = useWatch({ control: liqControl as never, name: "proy_nombre_propietario" });

  useEffect(() => {
    const denominacion = (watchedProyDenominacion as string) || "";
    const direccion = (watchedProyDireccion as string) || "";
    const nombrePropietario = (watchedProyNombrePropietario as string) || "";

    const current = proyectoInline ?? {
      denominacion: "",
      direccion: "",
      nombre_propietario: "",
      entidad: { tipo_documento: "RUC", numero_documento: "", razon_social: "" },
    };

    if (
      current.denominacion !== denominacion ||
      current.direccion !== direccion ||
      current.nombre_propietario !== nombrePropietario
    ) {
      setProyectoInline({
        ...current,
        denominacion,
        direccion,
        nombre_propietario: nombrePropietario,
      });
    }
  }, [watchedProyDenominacion, watchedProyDireccion, watchedProyNombrePropietario, proyectoInline, setProyectoInline]);

  // ── Revisiones ───────────────────────────────────────────────────────────────
  const { data: revisionesVigentes, isLoading: isLoadingRevisiones } =
    useRevisionesVigentesIV({
      tipo_tramite: watchedTipoTramite || "OBRA_NUEVA",
      tramite_accion: "PRIMERA_REVISION",
    });

  const revisionesHabilitadasCount = useMemo(
    () => (revisionesVigentes || []).filter((rev) => rev.habilitada).length,
    [revisionesVigentes],
  );
  const shouldShowRevisionesSection = isLoadingRevisiones || revisionesHabilitadasCount !== 1;
  const selectedRevision = useMemo(
    () => (revisionesVigentes || []).find((rev) => rev.id === selectedTarifasIds[0]) ?? null,
    [revisionesVigentes, selectedTarifasIds],
  );
  const valorBaseActual = useMemo(() => {
    const valorProyecto = Number(watchedValorProyecto);
    const valorBaseCalculo = Number(watchedValorBaseCalculo);
    return isPlantasTipicas && valorBaseCalculo > 0 ? valorBaseCalculo : valorProyecto;
  }, [isPlantasTipicas, watchedValorBaseCalculo, watchedValorProyecto]);

  // ── Cotización mutation ──────────────────────────────────────────────────────
  const cotizacionMutation = useCotizarImpactoVialPrimeraRevision();

  // ── Pre-select habilitadas revisions (stepper pattern) ───────────────────────
  const hasInitializedRevisiones = useRef(false);
  const [lockedTarifaId, setLockedTarifaId] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (!isLoadingRevisiones && revisionesVigentes && !hasInitializedRevisiones.current) {
      hasInitializedRevisiones.current = true;
      const habiles = revisionesVigentes.filter((rev) => rev.habilitada);
      if (habiles.length === 1) {
        setSelectedTarifasId(habiles[0].id);
        setLockedTarifaId(habiles[0].id);
      } else {
        setLockedTarifaId(null);
        // Clear stale selection from previous tipo_tramite
        useImpactoVialStepperStore.setState({ selectedTarifasIds: [] });
      }
    }
  }, [open, isLoadingRevisiones, revisionesVigentes, setSelectedTarifasId]);

  // Clear selection + lock on tipo_tramite change
  useEffect(() => {
    hasInitializedRevisiones.current = false;
    setLockedTarifaId(null);
  }, [watchedTipoTramite]);

  // ── Manual cotización handler (on-demand, not reactive) ─────────────────────
  const handleCotizar = useCallback(async () => {
    const values = liqGetValues();
    const tipoTramite = values.tipo_tramite as string;
    const isPT = tipoTramite === PROYECTO_CON_PLANTAS_TIPICAS_TIPO;
    const valorProyecto = Number(values.valor_proyecto);
    const valorBaseCalc = isPT && Number(values.valor_base_calculo) > 0
      ? Number(values.valor_base_calculo)
      : valorProyecto;

    if (valorBaseCalc <= 0) {
      notify.error("Ingresa un valor de proyecto válido");
      return;
    }
    if (selectedTarifasIds.length !== 1) {
      notify.error("Selecciona una tarifa");
      return;
    }

    setCotizacionQuote(null);
    try {
      const result = await cotizacionMutation.mutateAsync({
        valor_proyecto: valorBaseCalc,
        tarifas_ids: selectedTarifasIds,
      });
      setCotizacionQuote(result);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Error al calcular la cotización";
      setCotizacionError(msg);
    }
  }, [liqGetValues, selectedTarifasIds, cotizacionMutation, setCotizacionQuote, setCotizacionError]);

  // ── Handlers ─────────────────────────────────────────────────────────────────

  const handleRevisionToggle = useCallback(
    (revisionId: string) => {
      if (store.lockedRevisionIds?.includes(revisionId)) return;
      setSelectedTarifasId(revisionId);
    },
    [setSelectedTarifasId, store.lockedRevisionIds],
  );

  // Sync entidad fields from EntidadLookupField → proyectoInline (stepper pattern)
  const handleFieldChange = useCallback(
    (field: string, value: string) => {
      const current = proyectoInline ?? {
        denominacion: "",
        direccion: "",
        nombre_propietario: "",
        entidad: { tipo_documento: "RUC", numero_documento: "", razon_social: "" },
      };

      if (field === "entidad_tipo_documento") {
        setProyectoInline({
          ...current,
          entidad: { ...current.entidad, tipo_documento: value as "RUC" | "DNI" },
        });
      } else if (field === "entidad_numero_documento") {
        setProyectoInline({
          ...current,
          entidad: { ...current.entidad, numero_documento: value },
        });
      } else if (field === "entidad_razon_social") {
        setProyectoInline({
          ...current,
          entidad: { ...current.entidad, razon_social: value },
        });
      }
    },
    [proyectoInline, setProyectoInline],
  );

  const handleContactoSaved = useCallback(
    (contacto: ContactoInline) => {
      if (editingContactoIndex !== null) {
        store.updateContacto(editingContactoIndex, contacto);
      } else {
        store.addContacto(contacto);
      }
      setShowContactoModal(false);
      setEditingContactoIndex(null);
    },
    [editingContactoIndex, store],
  );

  const handleRemoveContacto = useCallback(
    (index: number) => {
      store.removeContacto(index);
    },
    [store],
  );

  const handleEditContacto = useCallback((index: number) => {
    setEditingContactoIndex(index);
    setShowContactoModal(true);
  }, []);

  const handleAddContacto = useCallback(() => {
    setEditingContactoIndex(null);
    setShowContactoModal(true);
  }, []);

  // ── Submit ───────────────────────────────────────────────────────────────────
  const crearMutation = useCrearImpactoVialPrimeraRevision();

  const handleClose = (nextOpen: boolean) => {
    if (!nextOpen) onOpenChange(false);
  };

  const handleSubmit = useCallback(
    async (data: FormData) => {
      const hasProyectoInline = !!proyectoInline;

      if (!hasProyectoInline) {
        notify.error("Debes crear un proyecto antes de crear la liquidación");
        return;
      }

      if (!selectedTarifasIds || selectedTarifasIds.length === 0) {
        notify.error("Debe seleccionar exactamente una tarifa");
        return;
      }

      const isPlantasTipicasSubmit =
        data.tipo_tramite === PROYECTO_CON_PLANTAS_TIPICAS_TIPO;
      const valorBaseCalculoSubmit = isPlantasTipicasSubmit &&
        data.valor_base_calculo &&
        data.valor_base_calculo > 0
        ? data.valor_base_calculo
        : data.valor_proyecto;

      const contactosPayload = selectedContactos.map(
        ({ localId: _localId, ...contacto }) => contacto,
      );

      const submitData: CrearImpactoVialPrimeraRevisionIn = {
        proyecto_inline: {
          denominacion: proyectoInline!.denominacion,
          direccion: proyectoInline!.direccion || undefined,
          distrito_id: proyectoInline!.distrito_id,
          nombre_propietario: proyectoInline!.nombre_propietario,
          entidad: proyectoInline!.entidad,
        },
        municipalidad_id: data.municipalidad_id,
        valor_proyecto: data.valor_proyecto,
        expediente: data.expediente || undefined,
        observacion: data.observacion || undefined,
        tarifas_ids: selectedTarifasIds,
        contactos: contactosPayload,
      };

      try {
        const response = await crearMutation.mutateAsync(submitData);
        notify.success("Liquidación creada correctamente");
        store.reset();
        liqReset();
        onSuccess?.();
        if (response.data) {
          onCreated?.(response.data);
        }
        onOpenChange(false);
      } catch {
        // Error handled by mutation
      }
    },
    [
      proyectoInline,
      selectedTarifasIds,
      selectedContactos,
      crearMutation,
      store,
      liqReset,
      onSuccess,
      onCreated,
      onOpenChange,
    ],
  );

  // ── Reset on close ───────────────────────────────────────────────────────────
  const resetStepper = useImpactoVialStepperStore((state) => state.reset);
  useEffect(() => {
    if (!open) {
      hasInitializedRevisiones.current = false;
      setLockedTarifaId(null);
      resetStepper();
      liqReset();
    }
  }, [open, resetStepper, liqReset]);

  const hasProject = !!proyectoInline;

  const initialData = useMemo<DefaultValues<FormData>>(() => ({
    municipalidad_id: "",
    tipo_tramite: "OBRA_NUEVA" as never,
    valor_proyecto: 0,
    expediente: "",
    valor_base_calculo: 0,
    observacion: "",
    revisiones_ids: [],
    proyectistas: [],
    contactos: [],
    proyecto_public_id: "",
  }), []);

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <>
      <GenericModal
        open={open}
        onOpenChange={handleClose}
        preventClose={true}
      >
        <GenericModal.Content
          size="xl"
          className="sm:w-[min(1500px,calc(100vw-32px))]"
        >
          {/* ── Header ──────────────────────────────────────────────────────────── */}
          <GenericModal.Header
            title=""
            className="bg-primary/[0.03] border-b border-border px-6 py-4 sm:px-8"
          >
            <div className="flex items-center gap-3 w-full">
              <div className="p-2 sm:p-2.5 bg-primary/10 rounded-xl sm:rounded-2xl border border-primary/20 shadow-sm shrink-0">
                <Truck className="h-5 w-5 text-primary" />
              </div>
              <div className="flex flex-col gap-0.5 min-w-0 flex-1">
                <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                  Impacto Vial
                </span>
                <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-foreground leading-tight">
                  Nueva Liquidación
                </h2>
                <p className="hidden sm:block max-w-prose text-pretty line-clamp-3 text-sm text-muted-foreground leading-relaxed">
                  Registra una nueva liquidación de impacto vial
                </p>
              </div>
              <div className="w-9 sm:w-11 shrink-0" aria-hidden="true" />
            </div>
          </GenericModal.Header>

          {/* ── Body ───────────────────────────────────────────────────────────── */}
          <GenericModal.Body>
            <GenericForm<FormData>
              formId="liquidacion-impacto-vial-form"
              schema={formSchema}
              initialData={initialData}
              formMethods={formMethods}
              onSubmit={handleSubmit}
              skipFooter
              formClassName="flex flex-col"
            >
              {() => {
                const {
                  register: liqReg,
                  control: liqControl,
                  formState: { errors: liqErrors },
                  setValue: liqSetValue,
                  watch: liqWatch,
                } = formMethods;

                return (
                  <div className="grid grid-areas-liquidacion-modal grid-cols-1 gap-4 min-h-0">
                    <div className="grid-area-tramite rounded-xl border border-border/50 bg-card p-4 space-y-4">
                      <div className="flex items-center gap-2 border-b border-border/40 pb-2 text-primary">
                        <FileText className="h-4 w-4" />
                        <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">
                          Datos del Trámite
                        </h3>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-4 min-w-0">
                          <GenericInput
                            field={{
                              name: "municipalidad_id",
                              label: "Municipalidad",
                              type: "searchable-select",
                              required: true,
                              placeholder: isLoadingMunicipalidades
                                ? "Cargando..."
                                : "Seleccione municipalidad",
                              options: (municipalidades || [])
                                .filter((municipalidad) =>
                                  municipalidad.nombre.toUpperCase().includes("SAN MIGUEL")
                                )
                                .map((municipalidad) => ({
                                  label: formatMunicipalidadLabel(municipalidad),
                                  value: municipalidad.id,
                                })),
                              icon: Building2,
                              isLoading: isLoadingMunicipalidades,
                              labelClassName: "text-foreground font-medium",
                              containerClassName: "min-w-0 w-full",
                            }}
                            register={liqReg as never}
                            control={liqControl as never}
                            errors={liqErrors}
                          />
                          <GenericInput
                            field={{
                              name: "expediente",
                              label: "Expediente",
                              type: "text",
                              placeholder: "Número de expediente (opcional)",
                              icon: FileText,
                              labelClassName: "text-foreground font-medium",
                              containerClassName: "min-w-0 w-full",
                            }}
                            register={liqReg as never}
                            control={liqControl as never}
                            errors={liqErrors}
                          />
                          <GenericInput
                            field={{
                              name: "observacion",
                              label: "Observación",
                              type: "textarea",
                              placeholder: "Observaciones adicionales (opcional)",
                              icon: MessageSquare,
                              labelClassName: "text-foreground font-medium",
                              containerClassName: "min-w-0 w-full",
                            }}
                            register={liqReg as never}
                            control={liqControl as never}
                            errors={liqErrors}
                          />
                        </div>

                        <div className="space-y-4 min-w-0">

                          <MoneyInput
                            name="valor_proyecto"
                            label="Valor del Proyecto (S/)"
                            icon={Banknote}
                            placeholder="S/ 0.00"
                            required
                            min={0}
                            defaultValue={0}
                            control={liqControl}
                            onEnter={handleCotizar}
                            error={liqErrors.valor_proyecto as { message?: string } | undefined}
                          />
                          {isPlantasTipicas && (
                            <MoneyInput
                              name="valor_base_calculo"
                              label="Valor Declarado (S/)"
                              icon={Calculator}
                              placeholder="S/ 0.00"
                              required
                              min={0}
                              defaultValue={0}
                              control={liqControl}
                              error={liqErrors.valor_base_calculo as { message?: string } | undefined}
                            />
                          )}
                        </div>
                      </div>

                      {shouldShowRevisionesSection && (
                        <div className="space-y-3">
                          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                            <FileText className="h-3.5 w-3.5 text-primary/70" />
                            Revisión / Tarifa
                          </div>
                          <RevisionesVigentesTable
                            revisiones={revisionesVigentes || []}
                            selectedId={selectedTarifasIds[0] ?? null}
                            onSelectRevision={handleRevisionToggle}
                            isLoading={isLoadingRevisiones}
                            lockedIds={lockedTarifaId ? [lockedTarifaId] : []}
                          />
                        </div>
                      )}

                      <div className="rounded-xl border border-primary/20 bg-primary/[0.03] p-4 shadow-sm">
                        <CotizacionSection
                          quote={cotizacion.quote}
                          isLoading={cotizacionMutation.isPending}
                          onCotizar={handleCotizar}
                          hasErrors={!!cotizacion.lastError}
                          isLoadingData={isLoadingRevisiones || isLoadingVariables}
                          variablesFinancieras={variablesFinancieras}
                          isLoadingVariables={isLoadingVariables}
                          valorBaseActual={valorBaseActual}
                          tarifaSeleccionada={selectedRevision}
                          hideButton
                          compact
                        />
                      </div>
                    </div>
                    <div className="h-4"></div>
                    <DatosDelProyectoSection
                      register={liqReg}
                      control={liqControl as never}
                      errors={liqErrors as never}
                      denominacionField={{
                        name: "proy_denominacion",
                        label: "Denominación",
                        placeholder: "Nombre del proyecto",
                        required: true,
                      }}
                      direccionField={{
                        name: "proy_direccion",
                        label: "Dirección",
                        placeholder: "Dirección del proyecto (opcional)",
                      }}
                      entidadSlot={
                        <EntidadLookupField
                          control={liqControl as never}
                          errors={liqErrors as never}
                          onFieldChange={handleFieldChange}
                          razonSocialSideSlot={(
                            <GenericInput
                              field={{
                                name: "proy_nombre_propietario",
                                label: "Nombre del Propietario",
                                type: "text",
                                required: true,
                                placeholder: "Nombre del propietario o representante legal",
                                icon: User,
                                labelClassName: "text-foreground font-medium",
                                containerClassName: "min-w-0 w-full",
                              }}
                              register={liqReg as never}
                              control={liqControl as never}
                              errors={liqErrors}
                            />
                          )}
                        />
                      }
                      selectedContactos={selectedContactos}
                      onAddContacto={handleAddContacto}
                      onRemoveContacto={handleRemoveContacto}
                      onEditContacto={handleEditContacto}
                    />
                  </div>
                );
              }}
            </GenericForm>
          </GenericModal.Body>

          {/* ── Footer ──────────────────────────────────────────────────────────── */}
          <GenericModal.Footer className="px-6 py-3.5 sm:px-8 bg-muted/20 border-t border-border">
            <div className="flex flex-row sm:justify-end items-center gap-2 sm:gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={crearMutation.isPending}
                className="flex-1 h-10 sm:h-11 rounded-xl font-semibold border border-border/60 hover:border-border hover:bg-background transition-all duration-200 sm:max-w-[120px] text-muted-foreground hover:text-foreground"
                aria-label="Cancelar"
              >
                <X className="h-4 w-4 sm:hidden" />
                <span className="hidden sm:inline">Cancelar</span>
              </Button>
              <Button
                type="submit"
                form="liquidacion-impacto-vial-form"
                disabled={crearMutation.isPending || !hasProject}
                className="flex-1 h-10 sm:h-12 rounded-xl sm:rounded-2xl font-bold shadow-lg shadow-primary/25 gap-2 sm:max-w-[200px] text-base transition-all duration-200 hover:shadow-xl hover:shadow-primary/30 hover:-translate-y-0.5 active:translate-y-0 disabled:hover:translate-y-0 disabled:hover:shadow-lg"
                aria-label="Crear Liquidación"
              >
                {crearMutation.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
                {!crearMutation.isPending && (
                  <CheckCircle2 className="h-4 w-4 sm:hidden" />
                )}
                <span className="hidden sm:inline">
                  {crearMutation.isPending ? "Creando..." : "Crear Liquidación"}
                </span>
              </Button>
            </div>
          </GenericModal.Footer>

          <GenericModal.CloseX />
        </GenericModal.Content>
      </GenericModal>

      {/* ── Child Modals ─────────────────────────────────────────────────────── */}
      <ContactoFormModal
        open={showContactoModal}
        onOpenChange={setShowContactoModal}
        onSaved={handleContactoSaved}
        initialData={
          editingContactoIndex !== null
            ? selectedContactos[editingContactoIndex]
            : undefined
        }
      />
    </>
  );
}
