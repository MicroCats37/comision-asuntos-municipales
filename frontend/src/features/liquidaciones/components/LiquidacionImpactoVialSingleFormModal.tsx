"use client";

/**
 * LiquidacionImpactoVialSingleFormModal — Single continuous form for IV.
 *
 * UI/UX Redesign:
 * - Replace 4-step stepper with single-form modal with two sections:
 *   `Datos del Trámite` (cotizacion inside) + `Datos del Proyecto`
 * - Cotizacion fires via Enter key on area input
 * - Out-of-sync indicator when area changes after quoting
 * - Auto-select single enabled tarifa and hide selector
 * - No proyectistas UI; send `proyectistas: []` in payload
 * - Contacts as compact chip section
 * - Post-create direct print via onCreated callback
 *
 * Architecture preserved:
 * - Zustand store (useImpactoVialStepperStore): proyecto, contactos
 * - React Hook Form: liquidacion fields
 * - Child modal: ContactoFormModal
 *
 * User confirmed decisions:
 * - IV-specific cotizacion section component (not shared)
 * - IV cotizacion is area-based (m² × costo_por_m2 + derecho min/max)
 * - Proyectistas: removed from UI, `proyectistas: []` in payload
 * - Post-create direct print
 */

import {
  Building2,
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
import { AreaInput } from "@/components/genericForm/inputs/AreaInput";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { GenericForm } from "@/components/genericForm/GenericForm";
import { notify } from "@/errors";
import { useCrearImpactoVialPrimeraRevision } from "../hooks/useImpactoVial";
import { useCotizarImpactoVialPrimeraRevision } from "../hooks/useImpactoVial";
import { useMunicipalidades } from "../hooks/useMunicipalidades";
import { useVariablesFinancieras } from "../hooks/useVariablesFinancieras";
import { useTarifasVigentesImpactoVial } from "../hooks/useTarifasVigentes";
import {
  useImpactoVialStepperStore,
} from "../store/stepper-ui-store-factory";
import type { ContactoInline } from "../types/contacto";
import type {
  CotizacionImpactoVialResponse,
  CrearImpactoVialPrimeraRevisionIn,
  CrearImpactoVialResponse,
  TarifaVigenteImpactoVial,
} from "../types/liquidacion-impacto-vial.types";
import { ContactoFormModal } from "./ContactoFormModal";
import { ContactosSection } from "./ContactosSection";
import { DatosDelProyectoSection } from "./DatosDelProyectoSection";
import { EntidadLookupField } from "./EntidadLookupField";
import { ImpactoVialCotizacionSection } from "./ImpactoVialCotizacionSection";
import { ImpactoVialTarifaSelector } from "./ImpactoVialTarifaSelector";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatMunicipalidadLabel(m: {
  codigo?: string | null;
  nombre: string;
  provincia?: { nombre: string } | null;
  distrito?: { nombre: string } | null;
}) {
  const args: string[] = [];
  if (m.codigo) args.push(m.codigo);
  args.push(m.nombre);
  const sub: string[] = [];
  if (m.provincia?.nombre) sub.push(m.provincia.nombre);
  if (m.distrito?.nombre) sub.push(m.distrito.nombre);
  return args.join(" - ") + (sub.length ? ` - ${sub.join(" / ")}` : "");
}

// ── Props ─────────────────────────────────────────────────────────────────────

export interface LiquidacionImpactoVialSingleFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  /** Called after successful creation with the API response data */
  onCreated?: (created: CrearImpactoVialResponse) => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function LiquidacionImpactoVialSingleFormModal({
  open,
  onOpenChange,
  onSuccess,
  onCreated,
}: LiquidacionImpactoVialSingleFormModalProps) {
  // ── Store (only proyecto + contactos — cotizacion is local to this modal) ───
  const store = useImpactoVialStepperStore();
  const {
    proyectoInline,
    setProyectoInline,
    selectedContactos,
    selectedTarifasIds,
    setSelectedTarifasId,
    setSelectedTarifasIds,
  } = store;

  // ── Local cotizacion state (IV cotizacion type differs from store CotizacionQuote) ───
  const [cotizacionQuote, setCotizacionQuote] = useState<CotizacionImpactoVialResponse | null>(null);
  const [cotizacionError, setCotizacionError] = useState<string | null>(null);
  const [cotizacionCalculating, setCotizacionCalculating] = useState(false);

  // ── Child modal state ─────────────────────────────────────────────────────
  const [showContactoModal, setShowContactoModal] = useState(false);
  const [editingContactoIndex, setEditingContactoIndex] = useState<number | null>(null);

  // ── Form schema (local to avoid type mismatches from extra fields) ───────────
  const formSchema = z.object({
    municipalidad_id: z.string().uuid("Debe seleccionar una municipalidad"),
    area_solicitada: z.number().positive("El área debe ser positiva"),
    expediente: z.string().optional(),
    observacion: z.string().optional(),
    tarifas_ids: z.array(z.string().uuid()).min(1, "Debe seleccionar al menos una tarifa"),
    // Inline proyecto fields (not in schema but registered with RHF)
    proy_denominacion: z.string().min(1, "Denominación es requerida"),
    proy_direccion: z.string().optional(),
    proy_distrito_id: z.string().optional(),
    proy_nombre_propietario: z.string().min(1, "Nombre del propietario es requerido"),
    entidad_tipo_documento: z.enum(["RUC", "DNI"]),
    entidad_numero_documento: z.string().min(1, "Número de documento es requerido"),
    entidad_razon_social: z.string().min(1, "Razón social es requerida"),
  });

  type FormData = z.infer<typeof formSchema>;

  // ── RHF ───────────────────────────────────────────────────────────────────
  const formMethods = useForm<FormData>({
    resolver: zodResolver(formSchema) as never,
    defaultValues: {
      municipalidad_id: "" as never,
      area_solicitada: 0 as never,
      expediente: "",
      observacion: "",
      tarifas_ids: [] as never,
      proy_denominacion: "",
      proy_direccion: "",
      proy_distrito_id: "",
      proy_nombre_propietario: "",
      entidad_tipo_documento: "RUC" as never,
      entidad_numero_documento: "",
      entidad_razon_social: "",
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

  // ── Data hooks ─────────────────────────────────────────────────────────────
  const { data: variablesFinancieras, isLoading: isLoadingVariables } =
    useVariablesFinancieras();
  const { data: municipalidades, isLoading: isLoadingMunicipalidades } =
    useMunicipalidades();

  // ── Watched values ──────────────────────────────────────────────────────────
  const watchedMunicipalidadId = liqWatch("municipalidad_id");
  const watchedAreaSolicitada = liqWatch("area_solicitada");

  // ── Proyecto inline sync ───────────────────────────────────────────────────
  const watchedProyDenominacion = useWatch({ control: liqControl as never, name: "proy_denominacion" });
  const watchedProyDireccion = useWatch({ control: liqControl as never, name: "proy_direccion" });
  const watchedProyNombrePropietario = useWatch({ control: liqControl as never, name: "proy_nombre_propietario" });
  const watchedProyDistritoId = useWatch({ control: liqControl as never, name: "proy_distrito_id" });
  const watchedEntidadTipoDoc = useWatch({ control: liqControl as never, name: "entidad_tipo_documento" });
  const watchedEntidadNumDoc = useWatch({ control: liqControl as never, name: "entidad_numero_documento" });
  const watchedEntidadRazonSocial = useWatch({ control: liqControl as never, name: "entidad_razon_social" });

  useEffect(() => {
    const denominacion = (watchedProyDenominacion as string) || "";
    const direccion = (watchedProyDireccion as string) || "";
    const nombrePropietario = (watchedProyNombrePropietario as string) || "";
    const distritoId = (watchedProyDistritoId as string) || undefined;
    const tipoDoc = (watchedEntidadTipoDoc as string) || "RUC";
    const numDoc = (watchedEntidadNumDoc as string) || "";
    const razonSocial = (watchedEntidadRazonSocial as string) || "";

    const current = proyectoInline ?? {
      denominacion: "",
      direccion: "",
      nombre_propietario: "",
      entidad: { tipo_documento: "RUC" as const, numero_documento: "", razon_social: "" },
    };

    if (
      current.denominacion !== denominacion ||
      current.direccion !== direccion ||
      current.nombre_propietario !== nombrePropietario ||
      current.distrito_id !== distritoId ||
      current.entidad.tipo_documento !== tipoDoc ||
      current.entidad.numero_documento !== numDoc ||
      current.entidad.razon_social !== razonSocial
    ) {
      setProyectoInline({
        denominacion,
        direccion,
        nombre_propietario: nombrePropietario,
        distrito_id: distritoId,
        entidad: {
          tipo_documento: tipoDoc as "RUC" | "DNI",
          numero_documento: numDoc,
          razon_social: razonSocial,
        },
      });
    }
  }, [
    watchedProyDenominacion,
    watchedProyDireccion,
    watchedProyNombrePropietario,
    watchedProyDistritoId,
    watchedEntidadTipoDoc,
    watchedEntidadNumDoc,
    watchedEntidadRazonSocial,
    proyectoInline,
    setProyectoInline,
  ]);

  // ── Tarifas ────────────────────────────────────────────────────────────────
  const { data: tarifasVigentes, isLoading: isLoadingTarifas } =
    useTarifasVigentesImpactoVial();

  const enabledTarifasCount = useMemo(
    () => (tarifasVigentes || []).filter((t) => t.habilitada).length,
    [tarifasVigentes],
  );
  const shouldShowTarifaSelector = isLoadingTarifas || enabledTarifasCount !== 1;
  const selectedTarifaId = selectedTarifasIds[0] ?? null;

  // Auto-select single enabled tarifa — also sync to RHF field so validation passes
  const hasInitializedTarifa = useRef(false);
  useEffect(() => {
    if (!open) return;
    if (!isLoadingTarifas && tarifasVigentes && !hasInitializedTarifa.current) {
      hasInitializedTarifa.current = true;
      const habiles = tarifasVigentes.filter((t) => t.habilitada);
      if (habiles.length === 1) {
        const tarifaId = habiles[0].tarifa_id;
        setSelectedTarifasId(tarifaId);
        liqSetValue("tarifas_ids", [tarifaId]);
      }
    }
  }, [open, isLoadingTarifas, tarifasVigentes, setSelectedTarifasId, liqSetValue]);

  // ── Cotización mutation ────────────────────────────────────────────────────
  const cotizacionMutation = useCotizarImpactoVialPrimeraRevision();

  // ── Cotizacion handler ─────────────────────────────────────────────────────
  const handleCotizar = useCallback(async () => {
    const areaSolicitada = Number(liqGetValues("area_solicitada"));
    if (areaSolicitada <= 0) {
      notify.error("Ingresa un área válida (mayor a 0)");
      return;
    }
    if (selectedTarifasIds.length !== 1) {
      notify.error("Selecciona una tarifa");
      return;
    }

    setCotizacionError(null);
    setCotizacionCalculating(true);
    try {
      const result = await cotizacionMutation.mutateAsync({
        area_solicitada: areaSolicitada,
        tarifas_ids: selectedTarifasIds,
      });
      setCotizacionQuote(result);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Error al calcular la cotización";
      setCotizacionError(msg);
      notify.error(msg);
    } finally {
      setCotizacionCalculating(false);
    }
  }, [
    liqGetValues,
    selectedTarifasIds,
    cotizacionMutation,
  ]);

  // ── Tarifa selection ───────────────────────────────────────────────────────
  const handleTarifaSelect = useCallback(
    (tarifaId: string) => {
      setSelectedTarifasId(tarifaId);
      liqSetValue("tarifas_ids", [tarifaId]);
    },
    [setSelectedTarifasId, liqSetValue],
  );

  // ── Entidad field sync ─────────────────────────────────────────────────────────
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

  // ── Contact handlers ────────────────────────────────────────────────────────
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

  // ── Submit ────────────────────────────────────────────────────────────────
  const crearMutation = useCrearImpactoVialPrimeraRevision();

  const handleClose = (nextOpen: boolean) => {
    if (!nextOpen) onOpenChange(false);
  };

  const handleSubmit = useCallback(
    async (data: FormData) => {
      // Inline proyecto is always used (no existing proyecto selection in this flow)
      if (!proyectoInline || !proyectoInline.denominacion) {
        notify.error("Completa los datos del proyecto antes de crear la liquidación");
        return;
      }

      if (!selectedTarifasIds || selectedTarifasIds.length === 0) {
        notify.error("Debe seleccionar exactamente una tarifa");
        return;
      }

      const contactosPayload = selectedContactos.map(
        ({ localId: _localId, ...contacto }) => contacto,
      );

      const submitData: CrearImpactoVialPrimeraRevisionIn = {
        proyecto_inline: {
          denominacion: proyectoInline.denominacion,
          direccion: proyectoInline.direccion || undefined,
          distrito_id: proyectoInline.distrito_id,
          nombre_propietario: proyectoInline.nombre_propietario,
          entidad: proyectoInline.entidad,
        },
        municipalidad_id: data.municipalidad_id,
        area_solicitada: Number(data.area_solicitada),
        expediente: data.expediente,
        observacion: data.observacion,
        tarifas_ids: selectedTarifasIds,
        contactos: contactosPayload,
        // Proyectistas: omitted from this form — API accepts empty array via extended type
      } as unknown as CrearImpactoVialPrimeraRevisionIn;

      try {
        const response = await crearMutation.mutateAsync(submitData);
        notify.success("Liquidación creada correctamente");
        store.reset();
        liqReset();
        onSuccess?.();
        // onCreated receives the API response data (only if present)
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

  // ── Reset on close ─────────────────────────────────────────────────────────
  const resetStepper = useImpactoVialStepperStore((state) => state.reset);
  useEffect(() => {
    if (!open) {
      hasInitializedTarifa.current = false;
      setSelectedTarifasIds([]);
      setCotizacionQuote(null);
      setCotizacionError(null);
      setCotizacionCalculating(false);
      resetStepper();
      liqReset();
    }
  }, [open, resetStepper, liqReset, setSelectedTarifasIds]);

  const hasProject = !!proyectoInline?.denominacion;

  // ── Initial data ──────────────────────────────────────────────────────────
  const initialData = useMemo<DefaultValues<FormData>>(() => ({
    municipalidad_id: "",
    area_solicitada: 0,
    expediente: "",
    observacion: "",
    tarifas_ids: [],
    proy_denominacion: "",
    proy_direccion: "",
    proy_distrito_id: "",
    proy_nombre_propietario: "",
    entidad_tipo_documento: "RUC" as never,
    entidad_numero_documento: "",
    entidad_razon_social: "",
  }), []);

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <>
      <GenericModal
        open={open}
        onOpenChange={handleClose}
        preventClose={crearMutation.isPending}
      >
        <GenericModal.Content
          size="xl"
          className="sm:w-[min(1500px,calc(100vw-32px))]"
        >
          {/* ── Header ────────────────────────────────────────────────────── */}
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

          {/* ── Body ─────────────────────────────────────────────────────── */}
          <GenericModal.Body>
            <GenericForm<FormData>
              formId="liquidacion-impacto-vial-form"
              schema={formSchema as never}
              initialData={initialData}
              formMethods={formMethods as never}
              onSubmit={handleSubmit as never}
              skipFooter
              formClassName="flex flex-col"
            >
              {() => {
                const {
                  register: liqReg,
                  control: liqControl,
                  formState: { errors: liqErrors },
                } = formMethods;

                return (
                  <div className="grid grid-areas-liquidacion-modal grid-cols-1 gap-4 min-h-0">
                    {/* ── Datos del Trámite ──────────────────────────────── */}
                    <div className="grid-area-tramite rounded-xl border border-border/50 bg-card p-4 space-y-4">
                      <div className="flex items-center gap-2 border-b border-border/40 pb-2 text-primary">
                        <FileText className="h-4 w-4" />
                        <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">
                          Datos del Trámite
                        </h3>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Left column */}
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
                              options: (municipalidades || []).map((municipalidad) => ({
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
                          <AreaInput
                            name="area_solicitada"
                            label="Área Solicitada (m²)"
                            icon={MapPin}
                            placeholder="Ej: 500 — presiona Enter para cotizar"
                            required
                            min={0}
                            defaultValue={0}
                            control={liqControl}
                            onEnter={handleCotizar}
                            error={liqErrors.area_solicitada as { message?: string } | undefined}
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

                        {/* Right column — Cotizacion */}
                        <div className="space-y-4 min-w-0">
                          {/* Tarifa selector — only show when multiple enabled */}
                          {shouldShowTarifaSelector && (
                            <ImpactoVialTarifaSelector
                              tarifas={tarifasVigentes || []}
                              selectedTarifaId={selectedTarifaId}
                              onSelectTarifa={handleTarifaSelect}
                              isLoading={isLoadingTarifas}
                            />
                          )}

                          {/* Cotizacion display — cotizacion fires on Enter in area_solicitada */}
                          <ImpactoVialCotizacionSection
                            quote={cotizacionQuote}
                            isLoading={cotizacionCalculating}
                            onCotizar={handleCotizar}
                            hasErrors={!!cotizacionError}
                            isLoadingData={isLoadingTarifas}
                            variablesFinancieras={variablesFinancieras}
                            isLoadingVariables={isLoadingVariables}
                            areaSolicitadaActual={Number(watchedAreaSolicitada) || 0}
                            hideButton
                            compact
                          />
                        </div>
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
                          razonSocialSideSlot={
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
                          }
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

          {/* ── Footer ───────────────────────────────────────────────────── */}
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

      {/* ── Child Modals ────────────────────────────────────────────────────── */}
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
