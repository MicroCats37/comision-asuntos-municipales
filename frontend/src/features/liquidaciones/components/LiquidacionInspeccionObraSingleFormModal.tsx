/**
 * LiquidacionInspeccionObraSingleFormModal — Single-form experience for Inspección de Obra.
 *
 * Replaces the hard 4-step stepper with a single scrollable form organized into
 * three visually separated (but always-visible) sections:
 *   1. Liquidación  — municipalidad + cantidad_visitas + categoria + cotización
 *   2. Proyecto    — buscar existente (XOR) o crear inline
 *   3. Personas    — proyectistas + contactos
 *
 * A live confirmation preview panel sits on the right (desktop) showing entered
 * data as the user fills the form.
 *
 * ── Arquitectura ─────────────────────────────────────────────────────────────
 * GenericModal shell + GenericForm (manual render prop) + Zustand store
 * React Hook Form + Zod (full-form validation on submit)
 * Same hooks and mutations as the stepper version
 */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  Banknote,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileText,
  Loader2,
  Users,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { FieldValues, UseFormReturn } from "react-hook-form";
import { useForm } from "react-hook-form";
import { useWatch } from "react-hook-form";
import { Button } from "@/components/ui/button";
import {
  GenericModal,
} from "@/components/genericModal/GenericModal";
import { FormSectionHeader } from "@/components-app/forms/FormSectionHeader";
import { notify } from "@/errors";
import { useCrearInspeccionObraPrimeraRevision } from "../hooks/useInspeccionObra";
import { useCotizarInspeccionObraPrimeraRevision } from "../hooks/useInspeccionObra";
import { useMunicipalidades } from "../hooks/useMunicipalidades";
import { useEspecialidadesVigentesLiquidacion } from "../hooks/useEspecialidadesVigentesLiquidacion";
import { stepInspeccionObraSchema } from "../schemas/liquidacion-inspeccion-obra.schema";
import {
  useInspeccionObraStepperStore,
  type CotizacionState,
  type LiquidacionStepperStore,
} from "../store";
import type { ContactoInline } from "../types/contacto";
import type { CotizacionIOResponse } from "../types/liquidacion-inspeccion-obra.types";
import type { CrearInspeccionObraPrimeraRevisionIn } from "../types/liquidacion-inspeccion-obra.types";
import type { ProyectistaInline } from "../types/proyectista";
import { ContactoFormModal } from "./ContactoFormModal";
import { ProyectistaFormModal } from "./ProyectistaFormModal";
import { Step1Proyecto } from "./steps/Step1Proyecto";
import { Step3Personas } from "./steps/Step3Personas";
import { StepInspeccionObraLiquidacion } from "./steps/StepInspeccionObraLiquidacion";
import { Badge } from "@/components/ui/badge";

// ── Types ─────────────────────────────────────────────────────────────────────

type FormData = {
  municipalidad_id: string;
  cantidad_visitas: number;
  categoria: "C1" | "C2" | "C3" | "C4";
  expediente?: string;
  observacion?: string;
};

const CATEGORIA_LABELS: Record<string, string> = {
  C1: "Categoría C1",
  C2: "Categoría C2",
  C3: "Categoría C3",
  C4: "Categoría C4",
};

const TIPO_LABEL = "Inspección de Obra";

// ── Props ─────────────────────────────────────────────────────────────────────

export interface LiquidacionInspeccionObraSingleFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

// ── Confirmation Preview (inline, right panel) ─────────────────────────────────

function formatSoles(value: number) {
  return `S/ ${value.toLocaleString("es-PE", { minimumFractionDigits: 2 })}`;
}

interface ConfirmationPreviewProps {
  methods: UseFormReturn<FormData>;
  store: LiquidacionStepperStore;
  municipalidades: Array<{ id: string; nombre: string }>;
  quote: CotizacionIOResponse | null;
  isOpen: boolean;
  onToggle: () => void;
}

function ConfirmationPreview({
  methods,
  store,
  municipalidades,
  quote,
  isOpen,
  onToggle,
}: ConfirmationPreviewProps) {
  const watchedMunicipalidadId = useWatch({ control: methods.control, name: "municipalidad_id" });
  const watchedCantidadVisitas = useWatch({ control: methods.control, name: "cantidad_visitas" });
  const watchedCategoria = useWatch({ control: methods.control, name: "categoria" });
  const watchedExpediente = useWatch({ control: methods.control, name: "expediente" });

  const municipalidad = municipalidades.find((m) => m.id === watchedMunicipalidadId);
  const { selectedProyecto, proyectoInline, selectedProyectistas, selectedContactos } = store;

  const hasProyecto = !!selectedProyecto || !!proyectoInline;

  const previewItems = [
    { label: "Municipalidad", value: municipalidad?.nombre ?? "—" },
    { label: "Visitas", value: watchedCantidadVisitas ? `${watchedCantidadVisitas} visita(s)` : "—" },
    { label: "Categoría", value: CATEGORIA_LABELS[watchedCategoria] ?? "—" },
    { label: "Expediente", value: watchedExpediente || "—" },
  ];

  return (
    <div className="flex flex-col rounded-xl border border-border bg-card overflow-hidden">
      {/* Preview toggle header */}
      <button
        type="button"
        onClick={onToggle}
        className="flex items-center justify-between w-full px-4 py-3 bg-muted/40 border-b border-border text-left hover:bg-muted/60 transition-colors"
      >
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-primary" />
          <span className="text-sm font-semibold text-foreground">Resumen</span>
        </div>
        {isOpen ? (
          <ChevronUp className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        )}
      </button>

      {/* Preview body */}
      {isOpen && (
        <div className="p-4 space-y-4 overflow-auto max-h-96">
          {/* Liquidación summary */}
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Liquidación
            </p>
            <div className="space-y-1.5">
              {previewItems.map((item) => (
                <div key={item.label} className="flex items-start justify-between gap-2">
                  <span className="text-xs text-muted-foreground shrink-0">{item.label}</span>
                  <span className="text-xs font-medium text-foreground text-right">{item.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Cotización */}
          {quote && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                Cotización
              </p>
              <div className="rounded-lg border border-border bg-muted/20 p-2 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-muted-foreground">Revisión</span>
                  <span className="text-[10px] font-semibold">#{quote.numero_revision}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-muted-foreground">Total</span>
                  <span className="text-xs font-bold text-primary">
                    {formatSoles(quote.totales.total_a_pagar)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Proyecto */}
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Proyecto
            </p>
            {hasProyecto ? (
              <div className="space-y-1">
                <p className="text-xs font-medium text-foreground truncate">
                  {selectedProyecto?.denominacion ?? proyectoInline?.denominacion ?? "—"}
                </p>
                {selectedProyecto && (
                  <p className="text-[10px] text-muted-foreground truncate">
                    {selectedProyecto.public_id}
                  </p>
                )}
                {proyectoInline && (
                  <p className="text-[10px] text-muted-foreground truncate">
                    {proyectoInline.direccion || "Sin dirección"}
                  </p>
                )}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground italic">Sin proyecto</p>
            )}
          </div>

          {/* Personas */}
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Personas
            </p>
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Proyectistas</span>
                <Badge variant="outline" className="text-[10px] h-4">
                  {selectedProyectistas.length}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Contactos</span>
                <Badge variant="outline" className="text-[10px] h-4">
                  {selectedContactos.length}
                </Badge>
              </div>
            </div>
          </div>

          {/* Validation hints */}
          {!hasProyecto && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-2">
              <p className="text-[10px] text-amber-700">
                ⚠️ Selecciona o crea un proyecto antes de enviar
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

export function LiquidacionInspeccionObraSingleFormModal({
  open,
  onOpenChange,
  onSuccess,
}: LiquidacionInspeccionObraSingleFormModalProps) {
  const crearMutation = useCrearInspeccionObraPrimeraRevision();
  const cotizarMutation = useCotizarInspeccionObraPrimeraRevision();
  const { data: municipalidades, isLoading: isLoadingMunicipalidades } =
    useMunicipalidades();

  // ── Especialidades vigentes ────────────────────────────────────────────────
  const { data: especialidadesData } = useEspecialidadesVigentesLiquidacion("inspeccion-obra");
  const especialidadOptions: Array<{ label: string; value: string }> =
    especialidadesData?.items
      ? [
          ...new Map(
            especialidadesData.items.map((esp) => ({
              label: esp.nombre,
              value: esp.id,
            })).map((opt) => [opt.value, opt]),
          ).values(),
        ]
      : [];
  const especialidadLabels: Record<string, string> = {};
  if (especialidadesData?.items) {
    for (const esp of especialidadesData.items) {
      especialidadLabels[esp.id] = esp.nombre;
    }
  }

  // ── Form ─────────────────────────────────────────────────────────────────
  const formMethods = useForm<FormData>({
    resolver: zodResolver(stepInspeccionObraSchema),
    defaultValues: {
      municipalidad_id: "" as never,
      cantidad_visitas: 1 as never,
      categoria: undefined as never,
      expediente: "",
      observacion: "",
    },
    mode: "onBlur",
  });

  const store = useInspeccionObraStepperStore();

  // ── Reset on close ───────────────────────────────────────────────────────
  const resetStepper = useInspeccionObraStepperStore((state) => state.reset);
  const { reset: resetForm } = formMethods;

  useEffect(() => {
    if (!open) {
      resetStepper();
      resetForm();
    }
  }, [open, resetStepper, resetForm]);

  // ── Child modals ─────────────────────────────────────────────────────────
  const [showProyectistaModal, setShowProyectistaModal] = useState(false);
  const [showContactoModal, setShowContactoModal] = useState(false);
  const [editingContactoIndex, setEditingContactoIndex] = useState<number | null>(null);

  const handleProyectistaSaved = useCallback(
    (proyectista: ProyectistaInline) => {
      store.addProyectista(proyectista);
      setShowProyectistaModal(false);
    },
    [store.addProyectista],
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
    [editingContactoIndex, store.addContacto, store.updateContacto],
  );

  // ── Cotización from store ────────────────────────────────────────────────
  const cotizacionQuote: CotizacionIOResponse | null =
    (store.cotizacion.quote as CotizacionIOResponse | null) ?? null;

  // ── Submit ────────────────────────────────────────────────────────────────
  const handleSubmit = useCallback(
    async (data: FormData) => {
      const { selectedProyecto, proyectoInline, selectedProyectistas: _sp, selectedContactos } =
        store;

      const hasProyectoExistente = !!selectedProyecto;
      const hasProyectoInline = !!proyectoInline;

      if (!hasProyectoExistente && !hasProyectoInline) {
        notify.error("Debe seleccionar o crear un proyecto");
        return;
      }

      if (hasProyectoExistente && hasProyectoInline) {
        notify.error("No puede seleccionar y crear un proyecto al mismo tiempo");
        return;
      }

      const contactosPayload = (selectedContactos as ContactoInline[]).map(
        ({ localId: _lid, ...contacto }) => contacto,
      );

      const submitData: CrearInspeccionObraPrimeraRevisionIn = {
        ...(hasProyectoInline
          ? {
              proyecto_inline: {
                denominacion: proyectoInline!.denominacion,
                direccion: proyectoInline!.direccion || undefined,
                distrito_id: proyectoInline!.distrito_id,
                nombre_propietario: proyectoInline!.nombre_propietario,
                entidad: proyectoInline!.entidad,
              },
            }
          : { proyecto_public_id: selectedProyecto!.public_id }),
        municipalidad_id: data.municipalidad_id,
        cantidad_visitas: Number(data.cantidad_visitas),
        categoria: data.categoria,
        expediente: data.expediente,
        observacion: data.observacion,
        tarifas_ids: store.selectedTarifasIds,
        contactos: contactosPayload,
      };

      try {
        await crearMutation.mutateAsync(submitData);
        notify.success("Liquidación creada correctamente");
        store.reset();
        formMethods.reset();
        onSuccess?.();
        onOpenChange(false);
      } catch {
        // Error ya manejado por la mutación
      }
    },
    [store, crearMutation, onSuccess, onOpenChange, formMethods],
  );

  // ── Preview panel toggle ──────────────────────────────────────────────────
  const [previewOpen, setPreviewOpen] = useState(true);

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <>
      <GenericModal
        open={open}
        onOpenChange={onOpenChange}
        preventClose={crearMutation.isPending}
      >
        <GenericModal.Content>
          {/* Header */}
          <GenericModal.Header
            title=""
            className="bg-primary/[0.03] border-b border-border px-6 py-5 sm:px-8"
          >
            <div className="flex items-center gap-3 w-full">
              <div className="p-2 sm:p-2.5 bg-primary/10 rounded-xl sm:rounded-2xl border border-primary/20 shadow-sm shrink-0">
                <FileText className="h-5 w-5 text-primary" />
              </div>
              <div className="flex flex-col gap-0.5 min-w-0 flex-1">
                <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                  Inspección de Obra
                </span>
                <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-foreground leading-tight">
                  Nueva Liquidación {TIPO_LABEL}
                </h2>
                <p className="hidden sm:block max-w-prose text-pretty line-clamp-3 text-sm text-muted-foreground leading-relaxed">
                  Registra una nueva liquidación de inspección de obra
                </p>
              </div>
              <div className="w-9 sm:w-11 shrink-0" aria-hidden="true" />
            </div>
          </GenericModal.Header>

          {/* Body: 2-column layout (form + preview) */}
          <GenericModal.Body className="p-0">
            <form
              id="io-single-form"
              onSubmit={formMethods.handleSubmit(handleSubmit as (data: FieldValues) => unknown)}
              noValidate
              className="flex flex-col lg:grid lg:grid-cols-5 min-h-0"
            >
                {/* ── Left: scrollable form sections ── */}
                <div className="flex flex-col gap-6 p-6 lg:p-8 col-span-3 min-w-0 overflow-auto">
                  {/* Section 1: Liquidación + Cotización */}
                  <section>
                    <FormSectionHeader
                      title="Liquidación"
                      icon={Banknote}
                      variant="soft"
                      className="mb-4"
                    />
                    <StepInspeccionObraLiquidacion
                      methods={formMethods as unknown as UseFormReturn<FieldValues>}
                      isActive={true}
                      municipalidades={municipalidades || []}
                      isLoadingMunicipalidades={isLoadingMunicipalidades}
                      cotizarMutation={cotizarMutation}
                      quote={cotizacionQuote}
                      setCotizacionQuote={(q) =>
                        store.setCotizacionQuote(q as CotizacionState["quote"])
                      }
                      setCotizacionError={store.setCotizacionError}
                      setCotizacionCalculating={store.setCotizacionCalculating}
                    />
                  </section>

                  {/* Section 2: Proyecto */}
                  <section>
                    <FormSectionHeader
                      title="Proyecto"
                      icon={Building2}
                      variant="soft"
                      className="mb-4"
                    />
                    <Step1Proyecto
                      methods={formMethods as unknown as UseFormReturn<FieldValues>}
                      isActive={true}
                      store={store}
                    />
                  </section>

                  {/* Section 3: Personas */}
                  <section>
                    <FormSectionHeader
                      title="Personas"
                      icon={Users}
                      variant="soft"
                      className="mb-4"
                    />
                    <Step3Personas
                      methods={formMethods as unknown as UseFormReturn<FieldValues>}
                      isActive={true}
                      store={store}
                      especialidadOptions={especialidadOptions}
                      especialidadLabels={especialidadLabels}
                      onOpenProyectistaModal={() => setShowProyectistaModal(true)}
                      onRemoveProyectista={(cip) => store.removeProyectista(cip)}
                      onOpenContactoModal={() => {
                        setEditingContactoIndex(null);
                        setShowContactoModal(true);
                      }}
                      onEditContacto={(index) => {
                        setEditingContactoIndex(index);
                        setShowContactoModal(true);
                      }}
                      onRemoveContacto={(index) => store.removeContacto(index)}
                    />
                  </section>
                </div>

                {/* ── Right: live confirmation preview ── */}
                <div className="hidden lg:flex flex-col col-span-2 border-l border-border p-6 lg:p-8 bg-muted/10 min-w-0">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-4">
                    Vista previa
                  </p>
                  <ConfirmationPreview
                    methods={formMethods}
                    store={store}
                    municipalidades={municipalidades?.map((m) => ({ id: m.id, nombre: m.nombre })) ?? []}
                    quote={cotizacionQuote}
                    isOpen={previewOpen}
                    onToggle={() => setPreviewOpen((v) => !v)}
                  />
                </div>

                {/* ── Mobile preview toggle (shown at bottom) ── */}
                <div className="lg:hidden col-span-5 border-t border-border">
                  <ConfirmationPreview
                    methods={formMethods}
                    store={store}
                    municipalidades={municipalidades?.map((m) => ({ id: m.id, nombre: m.nombre })) ?? []}
                    quote={cotizacionQuote}
                    isOpen={previewOpen}
                    onToggle={() => setPreviewOpen((v) => !v)}
                  />
                </div>
              </form>
          </GenericModal.Body>

          {/* Footer */}
          <GenericModal.Footer className="px-6 py-4 sm:px-8 bg-muted/30 border-t border-border">
            <div className="flex flex-row sm:justify-end items-center gap-2 sm:gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={crearMutation.isPending}
                className="flex-1 h-10 sm:h-11 rounded-xl font-semibold border border-border/60 hover:border-border hover:bg-background transition-all duration-200 sm:max-w-[120px] text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4 sm:hidden" />
                <span className="hidden sm:inline">Cancelar</span>
              </Button>

              <Button
                type="submit"
                form="io-single-form"
                disabled={crearMutation.isPending}
                className="flex-1 h-10 sm:h-12 rounded-xl sm:rounded-2xl font-bold shadow-lg shadow-primary/25 gap-2 sm:max-w-[220px] text-base transition-all duration-200 hover:shadow-xl hover:shadow-primary/30 hover:-translate-y-0.5 active:translate-y-0 disabled:hover:translate-y-0 disabled:hover:shadow-lg"
              >
                {crearMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                {crearMutation.isPending ? "Creando..." : "Crear Liquidación"}
              </Button>
            </div>
          </GenericModal.Footer>

          <GenericModal.CloseX />
        </GenericModal.Content>
      </GenericModal>

      <ProyectistaFormModal
        open={showProyectistaModal}
        onOpenChange={setShowProyectistaModal}
        onSaved={handleProyectistaSaved}
        especialidadOptions={especialidadOptions}
      />

      <ContactoFormModal
        open={showContactoModal}
        onOpenChange={setShowContactoModal}
        onSaved={handleContactoSaved}
        initialData={
          editingContactoIndex !== null
            ? store.selectedContactos[editingContactoIndex]
            : undefined
        }
      />
    </>
  );
}
