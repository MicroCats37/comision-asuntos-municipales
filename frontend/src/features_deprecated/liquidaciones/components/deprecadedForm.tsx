"use client";

import { FileText, Banknote, MessageSquare, User, X, Building2, Calculator, Search, CheckCircle2, Loader2, MapPin, Phone } from "lucide-react";
import { useCallback, useState, useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { GenericForm } from "@/components/genericForm/GenericForm";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useCrearPrimeraRevision } from "../hooks/useCrearLiquidacion";
import { useCotizacionPrimeraRevision } from "../hooks/useCotizacion";
import { useProyectoCrear } from "../hooks/useProyecto";
import { useRevisionesVigentes } from "../hooks/useRevisionesVigentes";
import { useVariablesFinancieras } from "../hooks/useVariablesFinancieras";
import { useMunicipalidades } from "../hooks/useMunicipalidades";
import { useDelegadosVigentes } from "../hooks/useDelegadosVigentes";
import { useDistritos } from "@/features/entidades/hooks/useDistritos";
import { liquidacionEdificacionFormSchema } from "../schemas/liquidacion-edificaciones-form.schema";
import type {
  LiquidacionEdificacionFormModalProps,
  LiquidacionEdificacionSubmitData,
  ProyectoResumen,
} from "../types/liquidacion-edificaciones-form.types";
import type { ProyectistaInline } from "../types/proyectista";
import type { ContactoInline } from "../types/contacto";
import type { CotizacionQuote } from "../types/liquidacion-edificaciones";
import type { EntidadResult } from "@/features/entidades/types/entidad";
import { ProyectistaFormModal } from "./ProyectistaFormModal";
import { ContactosSection } from "./ContactosSection";
import { ContactoFormModal } from "./ContactoFormModal";
import { RevisionesVigentesTable } from "./RevisionesVigentesTable";
import { CotizacionSection } from "./CotizacionSection";
import { ProyectistasSection } from "./ProyectistasSection";
import { DelegadosSection } from "./DelegadosSection";
import { useProyectoBuscar } from "../hooks/useProyecto";
import { normalizeProyectoResponse } from "../services/proyecto.service";
import { InstitucionFormModal } from "@/features/entidades/components/InstitucionFormModal";
import { PersonaNaturalFormModal } from "@/features/entidades/components/PersonaNaturalFormModal";
import { notify } from "@/errors";

const formSchema = liquidacionEdificacionFormSchema;

type FormData = z.infer<typeof formSchema>;

const TIPO_TRAMITE_OPTIONS = [
  { value: "OBRA_NUEVA", label: "Obra nueva" },
  { value: "DEMOLICION", label: "Demolición" },
  { value: "AMPLIACION", label: "Ampliación" },
  { value: "REMODELACION", label: "Remodelación" },
  { value: "MODIFICACION_LICENCIA", label: "Modificación de licencia" },
  { value: "REINTEGRO", label: "Reintegro" },
  { value: "PROYECTO_CON_PLANTAS_TIPICAS", label: "Proyecto con plantas típicas" },
] as const;

// Tipo trámite que permite valor_base_calculo diferente a valor_proyecto
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
  // Child modal state (only for proyectista now)
  const [showProyectistaModal, setShowProyectistaModal] = useState(false);
  const [showContactoModal, setShowContactoModal] = useState(false);
  /** Index of contact being edited, or null if adding new */
  const [editingContactoIndex, setEditingContactoIndex] = useState<number | null>(null);

  // Entidad state for inline proyecto form
  const [entidad, setEntidad] = useState<EntidadResult | undefined>();
  const [showInstitucionModal, setShowInstitucionModal] = useState(false);
  const [showPersonaNaturalModal, setShowPersonaNaturalModal] = useState(false);

  // Selected proyecto (local state for display, synced to form)
  const [selectedProyecto, setSelectedProyecto] = useState<
    ProyectoResumen | undefined
  >();

  // Selected proyectistas (local state for multi-select)
  const [selectedProyectistas, setSelectedProyectistas] = useState<
    ProyectistaInline[]
  >([]);

  // Selected contactos (local state for multi-select)
  const [selectedContactos, setSelectedContactos] = useState<ContactoInline[]>([]);

  // Selected delegados (local state for multi-select)
  const [selectedDelegados, setSelectedDelegados] = useState<string[]>([]);

  // Locked revision IDs (mandatory/habilitadas) — cannot be toggled
  const [lockedRevisionIds, setLockedRevisionIds] = useState<string[]>([]);

  // Project search state for selector tab
  const [publicIdSearch, setPublicIdSearch] = useState("");
  const buscarMutation = useProyectoBuscar();

  // Active tab for proyecto section
  const [activeProyectoTab, setActiveProyectoTab] = useState<"gestionar" | "proyecto-seleccionado">("gestionar");

  // Data hooks
  const { data: variablesFinancieras, isLoading: isLoadingVariables } =
    useVariablesFinancieras();
  const { data: revisionesVigentes, isLoading: isLoadingRevisiones } =
    useRevisionesVigentes();
  const { data: municipalidades, isLoading: isLoadingMunicipalidades } =
    useMunicipalidades();
  const { data: distritosData, isLoading: isLoadingDistritos } = useDistritos();
  const crearMutation = useCrearPrimeraRevision();
  const proyectoCrearMutation = useProyectoCrear();

  // Distrito options for proyecto form
  const distritoOptions = distritosData
    ? distritosData.map((d) => ({
        label: `${d.nombre} (${d.provincia.departamento.nombre} - ${d.provincia.nombre})`,
        value: d.id,
      }))
    : [];

  // Especialidad options for proyectista form (from revisiones vigentes)
  // Now revisions have M2M especialidades - extract all unique specialties
  const especialidadOptions = revisionesVigentes
    ? [...new Map(
        revisionesVigentes.flatMap((rev) =>
          rev.especialidades.map((esp) => ({
            label: esp.nombre,
            value: esp.id,
          }))
        ).map((opt) => [opt.value, opt])
      ).values()]
    : [];

  // Especialidad labels map for display in ProyectistasSection
  const especialidadLabels: Record<string, string> = {};
  if (revisionesVigentes) {
    for (const rev of revisionesVigentes) {
      for (const esp of rev.especialidades) {
        especialidadLabels[esp.id] = esp.nombre;
      }
    }
  }

  // Cotización state (clear when form fields change)
  const [cotizacionQuote, setCotizacionQuote] = useState<CotizacionQuote | null>(null);

  // ── Pre-select all habilitadas revisiones when data first loads ─────────────
  // Uses a ref so this only fires once (first load), not on subsequent refetches.
  const hasInitializedRevisiones = useRef(false);
  useEffect(() => {
    if (!isLoadingRevisiones && revisionesVigentes && !hasInitializedRevisiones.current) {
      hasInitializedRevisiones.current = true;
      const habilesIds = revisionesVigentes
        .filter((rev) => rev.habilitada)
        .map((rev) => rev.id);
      liqSetValue("revisiones_ids", habilesIds, { shouldValidate: false, shouldDirty: true });
      setLockedRevisionIds(habilesIds); // Lock the default mandatory revisions
    }
  }, [isLoadingRevisiones, revisionesVigentes]);

  // Handle entidad saved from child modal
  const handleEntidadSaved = useCallback((newEntidad: EntidadResult) => {
    setEntidad(newEntidad);
    setShowInstitucionModal(false);
    setShowPersonaNaturalModal(false);
  }, []);

  // Handle proyectista saved (created or selected)
  const handleProyectistaSaved = useCallback((proyectista: ProyectistaInline) => {
    setSelectedProyectistas((prev) => {
      if (prev.some((p) => p.cip === proyectista.cip)) {
        return prev;
      }
      return [...prev, proyectista];
    });
    setShowProyectistaModal(false);
  }, []);

  // Remove proyectista from selection
  const handleRemoveProyectista = useCallback((cip: string) => {
    setSelectedProyectistas((prev) => prev.filter((p) => p.cip !== cip));
  }, []);

  // Handle contacto saved (create or edit)
  const handleContactoSaved = useCallback((contacto: ContactoInline) => {
    setSelectedContactos((prev) => {
      // If editing an existing contact, replace it; otherwise append
      if (editingContactoIndex !== null) {
        const updated = [...prev];
        updated[editingContactoIndex] = contacto;
        return updated;
      }
      // Generate localId for new contacts (not from backend)
      const newContacto: ContactoInline = {
        ...contacto,
        localId: contacto.localId || `local-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      };
      return [...prev, newContacto];
    });
    setShowContactoModal(false);
    setEditingContactoIndex(null);
  }, [editingContactoIndex]);

  // Remove contacto from selection
  const handleRemoveContacto = useCallback((index: number) => {
    setSelectedContactos((prev) => prev.filter((_, i) => i !== index));
  }, []);

  // Edit contacto - open modal pre-filled
  const handleEditContacto = useCallback((index: number) => {
    setEditingContactoIndex(index);
    setShowContactoModal(true);
  }, []);

  // Add contacto - open empty modal
  const handleAddContacto = useCallback(() => {
    setEditingContactoIndex(null);
    setShowContactoModal(true);
  }, []);

  // Toggle delegado selection
  const handleToggleDelegado = useCallback((delegadoId: string) => {
    setSelectedDelegados((prev) =>
      prev.includes(delegadoId)
        ? prev.filter((id) => id !== delegadoId)
        : [...prev, delegadoId]
    );
  }, []);

  // Handle search existing project
  const handleSearch = async () => {
    if (!publicIdSearch.trim()) return;

    try {
      const result = await buscarMutation.mutateAsync(publicIdSearch);
      const proyectoData = normalizeProyectoResponse(result);
      if (proyectoData?.public_id) {
        const proyecto: ProyectoResumen = {
          id: proyectoData.id,
          public_id: proyectoData.public_id,
          denominacion: proyectoData.denominacion,
          direccion: proyectoData.direccion || "",
          distrito: proyectoData.distrito || undefined,
          entidad: proyectoData.entidad || undefined,
        };
        handleProyectoSaved(proyecto);
        setPublicIdSearch("");
      } else {
        alert("No se encontró un proyecto con ese ID");
      }
    } catch {
      alert("Error al buscar el proyecto");
    }
  };

  // ----------------------------------------------------------------
  // PROYECTO FORM — separate GenericForm, sibling to liquidacion form.
  // Runs its own react-hook-form context, submits independently.
  // On success: calls handleProyectoSaved which updates selectedProyecto
  // and switches to the "proyecto-seleccionado" tab.
  // ----------------------------------------------------------------
  const proyectoSchema = z.object({
    denominacion: z.string().min(1, "La denominación es requerida"),
    direccion: z.string().optional(),
    distrito_id: z.string().optional(),
  });

  const handleProyectoSubmit = async (data: z.infer<typeof proyectoSchema>) => {
    const result = await proyectoCrearMutation.mutateAsync({
      denominacion: data.denominacion,
      direccion: data.direccion || undefined,
      distrito_id: data.distrito_id,
      entidad_id: entidad?.id,
    });

    // Defensively extract proyecto — handles both wrapped {success,data} and direct
    const proyectoData = normalizeProyectoResponse(result);
    if (proyectoData?.public_id) {
      const proyecto: ProyectoResumen = {
        id: proyectoData.id,
        public_id: proyectoData.public_id,
        denominacion: proyectoData.denominacion,
        direccion: proyectoData.direccion || "",
        distrito: proyectoData.distrito || undefined,
        entidad: proyectoData.entidad || undefined,
      };
      handleProyectoSaved(proyecto);
      notify.success("Proyecto creado correctamente");
    }
  };

  // ----------------------------------------------------------------
  // LIQUIDACION FORM — uses GenericModal.Footer submit button
  // via form="liquidacion-form".  selectedProyecto is accessed
  // directly (not via hidden field) since the liquidacion submit
  // handler has closure access to the outer component state.
  // ----------------------------------------------------------------
  const handleLiquidacionSubmit = async (data: FormData) => {
    if (!selectedProyecto) {
      // Validation: proyecto must be selected — show alert (toast would need context)
      alert("Debe seleccionar un proyecto antes de crear la liquidación");
      return;
    }

    // Map inline proyectistas to backend payload (only cip, especialidad_id, descripcion)
    const proyectistasPayload = selectedProyectistas.map((p) => ({
      cip: p.cip,
      especialidad_id: p.especialidad_id,
      descripcion: p.descripcion,
    }));

    // Map contactos to backend payload, stripping localId (not a backend field)
    const contactosPayload = selectedContactos.map(({ localId: _localId, ...contacto }) => contacto);

    // Determine valor_base_calculo:
    // - For PROYECTO_CON_PLANTAS_TIPICAS: use the user-entered value (must be > 0)
    // - For normal types: must be equal to valor_proyecto (backend validates this)
    const isPlantasTipicas = data.tipo_tramite === PROYECTO_CON_PLANTAS_TIPICAS_TIPO;
    const valorBaseCalculo = isPlantasTipicas
      ? (data.valor_base_calculo && data.valor_base_calculo > 0 ? data.valor_base_calculo : data.valor_proyecto)
      : data.valor_proyecto; // Normal types: valor_base_calculo equals valor_proyecto

    const submitData: LiquidacionEdificacionSubmitData = {
      proyecto_public_id: selectedProyecto.public_id,
      municipalidad_id: data.municipalidad_id,
      tipo_tramite: data.tipo_tramite,
      valor_proyecto: data.valor_proyecto,
      expediente: data.expediente || undefined,
      valor_base_calculo: valorBaseCalculo,
      observacion: data.observacion || undefined,
      revisiones_ids: data.revisiones_ids || [],
      proyectistas: proyectistasPayload,
      contactos: contactosPayload,
      // delegadas_ids fue eliminado del tipo LiquidacionEdificacionSubmitData
      // TODO: Este formulario deprecated no soporta tarifas_ids - se mantiene por compatibilidad
      tarifas_ids: [],
    };

    await crearMutation.mutateAsync(submitData as import("../types/liquidacion-edificaciones").PrimeraRevisionFormData);
    notify.success("Liquidación creada correctamente");
    onSuccess?.();
    setSelectedProyecto(undefined);
    setSelectedProyectistas([]);
    setSelectedContactos([]);
    setSelectedDelegados([]);
    setEditingContactoIndex(null);
    setCotizacionQuote(null);
    // Reset form's proyecto_public_id so validation doesn't fail on next open
    liqSetValue("proyecto_public_id", "", { shouldValidate: false, shouldDirty: false });
  };

  const handleClose = (nextOpen: boolean) => {
    if (!nextOpen) {
      onOpenChange(false);
    }
  };

  // Liquidacion form — useForm instance at component top level so watch/control are available
  // NOTE: formMethods is passed to GenericForm below to ensure the SAME form instance
  // is used. This is critical for setValue (from handleProyectoSaved) to properly
  // update the field that GenericForm's validation checks.
  const liqFormMethods = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      municipalidad_id: "",
      tipo_tramite: "OBRA_NUEVA",
      valor_proyecto: 0,
      expediente: "",
      valor_base_calculo: 0,
      observacion: "",
      revisiones_ids: [],
      proyectistas: [],
      contactos: [],
      delegados_ids: [],
      proyecto_public_id: "",
    },
  });
  const {
    control: liqControl,
    formState: { errors: liqErrors },
    watch: liqWatch,
    setValue: liqSetValue,
  } = liqFormMethods;

  // Watch municipalidad_id for fetching delegates (must be after liqWatch is defined)
  const watchedMunicipalidadId = liqWatch("municipalidad_id");
  const selectedRevisionIds =
    (liqWatch("revisiones_ids") as string[]) || [];
  
  // Watch tipo_tramite for conditional valor_base_calculo display
  const watchedTipoTramite = liqWatch("tipo_tramite");
  const isPlantasTipicas = watchedTipoTramite === PROYECTO_CON_PLANTAS_TIPICAS_TIPO;

  // Use first selected revision for delegate filtering if exactly one is selected
  const singleRevisionId =
    selectedRevisionIds.length === 1 ? selectedRevisionIds[0] : null;

  const { data: delegadosVigentes, isLoading: isLoadingDelegados } = useDelegadosVigentes(
    watchedMunicipalidadId || null,
    "edificacion",
    singleRevisionId,
  );

  // ── Handle proyecto created inline or selected from search ──────────────────
  // NOTE: Must be defined after useForm so it has access to liqSetValue.
  // This callback syncs the selected proyecto to react-hook-form's
  // proyecto_public_id field so validation passes and watchedValues effect
  // (cotizacion clearing) triggers correctly.
  // Guard: only sync if public_id is non-empty to avoid clearing the field.
  // IMPORTANT: liqSetValue comes from liqFormMethods which is passed to GenericForm
  // as formMethods, so this setValue call updates the SAME form instance that
  // GenericForm uses for validation. This was the root cause of the bug.
  const handleProyectoSaved = useCallback((proyecto: ProyectoResumen) => {
    if (!proyecto?.public_id) {
      console.error("[LiquidacionEdificacionFormModal] handleProyectoSaved called without public_id", proyecto);
      return;
    }
    setSelectedProyecto(proyecto);
    setActiveProyectoTab("proyecto-seleccionado");
    // Sync to form state so validation passes and cotizacion clears
    // liqSetValue updates the same form instance that GenericForm validates against
    liqSetValue("proyecto_public_id", proyecto.public_id, { shouldValidate: true, shouldDirty: true });
  }, [liqSetValue]);

  const handleRevisionToggle = (revisionId: string) => {
    const current = selectedRevisionIds;
    const updated = current.includes(revisionId)
      ? current.filter((id) => id !== revisionId)
      : [...current, revisionId];
    liqSetValue("revisiones_ids", updated, { shouldValidate: true });
  };

  // Cotizacion hook inside render prop (needs access to watch)
  const cotizacionMutation = useCotizacionPrimeraRevision();

  // Clear cotizacion when relevant form fields change
  const watchedValues = liqWatch([
    "proyecto_public_id",
    "valor_proyecto",
    "revisiones_ids",
  ]);
  const watchedValuesRef = useRef(watchedValues);
  useEffect(() => {
    const prev = watchedValuesRef.current;
    const changed = prev.some((val, i) => val !== watchedValues[i]);
    if (changed && cotizacionQuote !== null) {
      setCotizacionQuote(null);
    }
    watchedValuesRef.current = watchedValues;
  }, [watchedValues, cotizacionQuote]);

  // Clear cotizacion when selectedProyecto changes (fallback effect).
  // This handles edge cases where setValue might not trigger watch properly,
  // and ensures cotizacion is cleared when project is changed/removed.
  useEffect(() => {
    if (cotizacionQuote !== null) {
      setCotizacionQuote(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProyecto?.id]);

  const handleCotizar = useCallback(async () => {
    const proyectoPublicId = selectedProyecto?.public_id;
    const valorProyecto = liqWatch("valor_proyecto");
    const valorBaseCalculo = liqWatch("valor_base_calculo");

    if (!proyectoPublicId || !valorProyecto || valorProyecto <= 0) {
      return;
    }

    // For cotizacion, use valor_base_calculo if provided (> 0), otherwise use valor_proyecto
    // This matches the backend logic where valor_base_calculo defaults to valor_proyecto
    const valorBase = (valorBaseCalculo && valorBaseCalculo > 0) ? valorBaseCalculo : valorProyecto;

    try {
      const result = await cotizacionMutation.mutateAsync({
        tipo_tramite: undefined,
        valor_proyecto: valorProyecto,
        valor_base_calculo: valorBase,
        tarifas_ids: [],
      });
      // Service now returns CotizacionQuote directly (unwrapped from {success, data, error})
      setCotizacionQuote(result);
    } catch {
      // Error is handled by the mutation
    }
  }, [cotizacionMutation, selectedProyecto]);

  const hasProject = !!selectedProyecto;
  const valorBaseCalculo = liqWatch("valor_base_calculo");
  const hasValidValorBase = !!valorBaseCalculo && Number(valorBaseCalculo) > 0;

  return (
    <>
    <GenericModal
      open={open}
      onOpenChange={handleClose}
      preventClose={true}
    >
      <GenericModal.Content size="lg">
        {/* ── Header ─────────────────────────────────────────────── */}
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
                Edificaciones
              </span>
              <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-foreground leading-tight">
                Nueva Liquidación
              </h2>
              <p className="hidden sm:block max-w-prose text-pretty line-clamp-3 text-sm text-muted-foreground leading-relaxed">
                Registra una nueva liquidación de edificación
              </p>
            </div>
            <div className="w-9 sm:w-11 shrink-0" aria-hidden="true" />
          </div>
        </GenericModal.Header>

        {/* ── Body — two sibling GenericForms, no DOM nesting ─────── */}
        <GenericModal.Body>
          <div className="h-full flex flex-col min-h-0">

            {/* Grid layout: responsive 2-column grid with explicit area placement
                Mobile order (single column, DOM order):
                  1. Proyecto
                  2. Datos de Liquidación
                  3. Revisiones / Especialidades
                  4. Proyectistas
                  5. Delegados (full width)
                  6. Cotización
                Desktop layout (2 columns with grid-template-areas):
                  "proyecto datos"
                  "revisiones proyectistas"
                  "delegados delegados"
                  "cotizacion cotizacion"
            */}
            <style>{`
              @media (min-width: 768px) {
                .liquidacion-grid {
                  grid-template-areas:
                    "proyecto datos"
                    "revisiones proyectistas"
                    "contactos contactos"
                    "delegados cotizacion";
                  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
                }
              }
              @media (max-width: 767px) {
                .liquidacion-grid {
                  grid-template-areas:
                    "proyecto"
                    "datos"
                    "revisiones"
                    "proyectistas"
                    "contactos"
                    "delegados"
                    "cotizacion";
                  grid-template-columns: 1fr;
                }
              }
            `}</style>

            <div className="liquidacion-grid grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 min-h-0">

              {/* ── PROYECTO SECTION (Tabbed) ────────────────────────
                  Uses its own GenericForm — NOT nested inside liquidacion form.
                  formId="proyecto-form" so its submit button targets the right form.
              */}
              <div
                className="rounded-xl border border-primary/20 bg-card p-4 space-y-4 overflow-auto min-h-0"
                style={{ gridArea: 'proyecto' }}
              >
                <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
                  <Building2 className="h-4 w-4" />
                  <h3 className="text-sm font-semibold uppercase tracking-wide">
                    Proyecto
                  </h3>
                </div>

                <Tabs
                  value={activeProyectoTab}
                  onValueChange={(v) => setActiveProyectoTab(v as "gestionar" | "proyecto-seleccionado")}
                  orientation="horizontal"
                >
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="gestionar">Gestionar Proyecto</TabsTrigger>
                    <TabsTrigger value="proyecto-seleccionado">Proyecto Seleccionado</TabsTrigger>
                  </TabsList>

                  {/* Tab 1: Gestionar Proyecto */}
                  <TabsContent value="gestionar" className="space-y-4">
                    {/* Search existing project */}
                    <div className="rounded-xl border border-border bg-card p-4 space-y-3">
                      <p className="text-sm font-semibold text-foreground">
                        Buscar Proyecto Existente
                      </p>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          placeholder="Ej: PROY-2026-00001"
                          className="flex h-11 flex-1 rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                          value={publicIdSearch}
                          onChange={(e) => setPublicIdSearch(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              handleSearch();
                            }
                          }}
                        />
                        <Button
                          type="button"
                          variant="default"
                          size="default"
                          className="h-11 rounded-xl gap-2"
                          onClick={handleSearch}
                          disabled={buscarMutation.isPending}
                        >
                          <Search className="h-4 w-4" />
                          Buscar
                        </Button>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Ingresa el ID público del proyecto existente
                      </p>
                    </div>

                    {/* Create new project — GenericForm for Proyecto */}
                    <div className="rounded-xl border border-border bg-card p-4 space-y-3">
                      <p className="text-sm font-semibold text-foreground">
                        Crear Nuevo Proyecto
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Completa el formulario para crear un nuevo proyecto.
                      </p>

                      {/* ─── GenericForm for proyecto — NO nesting, sibling form ─── */}
                      <GenericForm
                        formId="proyecto-form"
                        schema={proyectoSchema}
                        initialData={{
                          denominacion: "",
                          direccion: "",
                          distrito_id: undefined,
                        }}
                        onSubmit={handleProyectoSubmit}
                        skipFooter
                        formClassName="space-y-3"
                      >
                        {({ methods: proyectoMethods, isSubmitting: proyectoSubmitting }) => {
                          const {
                            register: reg,
                            control: projControl,
                            formState: { errors: projErrors },
                          } = proyectoMethods;

                          return (
                            <div className="space-y-3">
                              <GenericInput
                                field={{
                                  name: "denominacion",
                                  label: "Denominación",
                                  type: "text",
                                  required: true,
                                  placeholder: "Nombre del proyecto",
                                  icon: Building2,
                                  labelClassName: "text-primary font-semibold",
                                }}
                                register={reg as any}
                                control={projControl as any}
                                errors={projErrors}
                              />
                              <GenericInput
                                field={{
                                  name: "direccion",
                                  label: "Dirección",
                                  type: "text",
                                  placeholder: "Dirección del proyecto",
                                  icon: MapPin,
                                  labelClassName: "text-primary font-semibold",
                                }}
                                register={reg as any}
                                control={projControl as any}
                                errors={projErrors}
                              />
                              <GenericInput
                                field={{
                                  name: "distrito_id",
                                  label: "Distrito",
                                  type: "searchable-select",
                                  placeholder: "Buscar distrito...",
                                  options: distritoOptions,
                                  isLoading: isLoadingDistritos,
                                  icon: MapPin,
                                  labelClassName: "text-primary font-semibold",
                                }}
                                register={reg as any}
                                control={projControl as any}
                                errors={projErrors}
                              />

                              {/* Entidad */}
                              <div className="space-y-2">
                                <span className="text-sm font-medium">Entidad</span>
                                {entidad ? (
                                  <div className="space-y-2">
                                    <div className="p-3 rounded-lg border border-border bg-muted/30">
                                      <p className="font-medium">{entidad.nombre_completo}</p>
                                      <p className="text-xs text-muted-foreground">
                                        {entidad.tipo_documento}: {entidad.numero_documento}
                                      </p>
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                      <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        onClick={() => setShowInstitucionModal(true)}
                                        className="h-8 rounded-lg gap-1.5"
                                      >
                                        Cambiar Institución
                                      </Button>
                                      <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        onClick={() => setShowPersonaNaturalModal(true)}
                                        className="h-8 rounded-lg gap-1.5"
                                      >
                                        Cambiar Persona
                                      </Button>
                                    </div>
                                  </div>
                                ) : (
                                  <div className="space-y-3">
                                    <p className="text-sm text-muted-foreground italic">
                                      No hay entidad seleccionada
                                    </p>
                                    <div className="flex flex-wrap gap-2">
                                      <Button
                                        type="button"
                                        variant="default"
                                        size="sm"
                                        onClick={() => setShowInstitucionModal(true)}
                                        className="h-8 rounded-lg gap-1.5"
                                      >
                                        <Building2 className="h-3.5 w-3.5" />
                                        Crear Institución
                                      </Button>
                                      <Button
                                        type="button"
                                        variant="default"
                                        size="sm"
                                        onClick={() => setShowPersonaNaturalModal(true)}
                                        className="h-8 rounded-lg gap-1.5"
                                      >
                                        <User className="h-3.5 w-3.5" />
                                        Crear Persona Natural
                                      </Button>
                                    </div>
                                  </div>
                                )}
                              </div>

                              {/* Submit button for proyecto form — inside the form body */}
                              <div className="flex justify-end">
                                <Button
                                  type="submit"
                                  form="proyecto-form"
                                  variant="default"
                                  size="sm"
                                  disabled={proyectoSubmitting || proyectoCrearMutation.isPending}
                                  className="rounded-lg gap-1.5"
                                >
                                  {proyectoSubmitting || proyectoCrearMutation.isPending
                                    ? "Guardando..."
                                    : "Guardar Proyecto"}
                                </Button>
                              </div>
                            </div>
                          );
                        }}
                      </GenericForm>
                    </div>
                  </TabsContent>

                  {/* Tab 2: Proyecto Seleccionado */}
                  <TabsContent value="proyecto-seleccionado" className="space-y-4 h-full">
                    {selectedProyecto ? (
                      <div className="p-4 rounded-xl border border-border bg-card">
                        <div className="space-y-2">
                          <div className="flex items-start justify-between">
                            <div>
                              <p className="font-semibold text-foreground">
                                {selectedProyecto.denominacion}
                              </p>
                              <p className="text-sm text-muted-foreground">
                                {selectedProyecto.public_id}
                              </p>
                            </div>
                          </div>
                          <p className="text-sm text-muted-foreground">
                            {selectedProyecto.direccion || "Sin dirección"}
                            {selectedProyecto.distrito && ` - ${selectedProyecto.distrito}`}
                          </p>
                          {selectedProyecto.entidad && (
                            <div className="flex items-center gap-2 mt-2 text-sm">
                              <Building2 className="h-4 w-4 text-muted-foreground" />
                              <span>{selectedProyecto.entidad.nombre}</span>
                              {selectedProyecto.entidad.tipo && (
                                <span className="text-xs text-muted-foreground">
                                  ({selectedProyecto.entidad.tipo})
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center p-8 rounded-xl border border-dashed border-border">
                        <div className="text-center">
                          <Building2 className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                          <p className="text-sm text-muted-foreground">
                            No hay proyecto seleccionado
                          </p>
                          <Button
                            type="button"
                            variant="link"
                            size="sm"
                            onClick={() => setActiveProyectoTab("gestionar")}
                            className="mt-1"
                          >
                            Seleccionar o crear proyecto
                          </Button>
                        </div>
                      </div>
                    )}
                  </TabsContent>
                </Tabs>
              </div>

              {/* ── LIQUIDACION FORM ────────────────────────────────
                  formId="liquidacion-form" so GenericModal.Footer button
                  with form="liquidacion-form" triggers this form's submit.
                  Uses skipFooter — footer submit button is in GenericModal.Footer.
              */}
              <div
                className="rounded-xl border border-primary/20 bg-card p-4 space-y-4 overflow-auto min-h-0"
                style={{ gridArea: 'datos' }}
              >
                <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
                  <Banknote className="h-4 w-4" />
                  <h3 className="text-sm font-semibold uppercase tracking-wide">
                    Datos de Liquidación
                  </h3>
                </div>

                <GenericForm
                  formId="liquidacion-form"
                  schema={formSchema}
                  formMethods={liqFormMethods}
                  initialData={{
                    municipalidad_id: "",
                    tipo_tramite: "OBRA_NUEVA",
                    valor_proyecto: 0,
                    expediente: "",
                    valor_base_calculo: 0,
                    observacion: "",
                    revisiones_ids: [],
                    proyectistas: [],
                    contactos: [],
                    delegados_ids: [],
                    proyecto_public_id: "",
                  }}
                  onSubmit={handleLiquidacionSubmit}
                  skipFooter
                  formClassName="space-y-4"
                >
                  {({ methods: liqMethods }) => {
                    const {
                      register: liqReg,
                      control: liqControl,
                      formState: { errors: liqErrors },
                    } = liqMethods;

                    return (
                      <>
                        {/* Hidden field for proyecto_public_id — synced from selectedProyecto */}
                        <input
                          type="hidden"
                          {...liqReg("proyecto_public_id")}
                          value={selectedProyecto?.public_id ?? ""}
                        />
                        {liqErrors.proyecto_public_id && (
                          <p className="text-sm text-destructive px-1">
                            {liqErrors.proyecto_public_id.message as string}
                          </p>
                        )}

                        {/* Row: Municipalidad + Tipo de Trámite + Valor del Proyecto */}
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                          <GenericInput
                            field={{
                              name: "municipalidad_id",
                              label: "Municipalidad",
                              type: "searchable-select",
                              required: true,
                              placeholder: isLoadingMunicipalidades
                                ? "Cargando municipalidades..."
                                : "Seleccione municipalidad",
                              options: (municipalidades || []).map((municipalidad) => ({
                                label: formatMunicipalidadLabel(municipalidad),
                                value: municipalidad.id,
                              })),
                              icon: Building2,
                              isLoading: isLoadingMunicipalidades,
                              labelClassName: "text-primary font-semibold",
                            }}
                            register={liqReg as any}
                            control={liqControl as any}
                            errors={liqErrors}
                          />

                          {/* Hidden tipo_tramite field — always defaults to OBRA_NUEVA */}
                          <input type="hidden" {...liqReg("tipo_tramite")} value="OBRA_NUEVA" />

                          <GenericInput
                            field={{
                              name: "valor_proyecto",
                              label: "Valor del Proyecto (S/)",
                              type: "number",
                              required: true,
                              placeholder: "Ej: 500000",
                              icon: Banknote,
                              labelClassName: "text-primary font-semibold",
                            }}
                            register={liqReg as any}
                            control={liqControl as any}
                            errors={liqErrors}
                          />
                        </div>

                          {/* Row: Expediente + Valor Base de Cálculo (solo para plantas típicas) */}
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <GenericInput
                              field={{
                                name: "expediente",
                                label: "Expediente",
                                type: "text",
                                required: false,
                                placeholder: "Número de expediente (opcional)",
                                icon: FileText,
                                labelClassName: "text-primary font-semibold",
                              }}
                              register={liqReg as any}
                              control={liqControl as any}
                              errors={liqErrors}
                            />

                            {isPlantasTipicas && (
                              <GenericInput
                                field={{
                                  name: "valor_base_calculo",
                                  label: "Valor Declarado (S/)",
                                  type: "number",
                                  required: true,
                                  placeholder: "Valor base alternativo (requerido)",
                                  icon: Calculator,
                                  labelClassName: "text-primary font-semibold",
                                }}
                                register={liqReg as any}
                                control={liqControl as any}
                                errors={liqErrors}
                              />
                            )}
                          </div>

                        <GenericInput
                          field={{
                            name: "observacion",
                            label: "Observación",
                            type: "textarea",
                            placeholder: "Observaciones adicionales...",
                            icon: MessageSquare,
                            labelClassName: "text-primary font-semibold",
                          }}
                          register={liqReg as any}
                          control={liqControl as any}
                          errors={liqErrors}
                        />
                      </>
                    );
                  }}
                </GenericForm>
              </div>

              {/* ── Revisiones/Especialidades ─────────────────────────── */}
              <div
                className="rounded-xl border border-primary/20 bg-card p-4 space-y-4 overflow-auto min-h-0"
                style={{ gridArea: 'revisiones' }}
              >
                <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
                  <FileText className="h-4 w-4" />
                  <h3 className="text-sm font-semibold uppercase tracking-wide">
                    Revisiones / Especialidades
                  </h3>
                  <span className="ml-auto text-[10px] font-medium opacity-75">
                    (obligatorias)
                  </span>
                </div>

                <RevisionesVigentesTable
                  revisiones={revisionesVigentes || []}
                  selectedId={selectedRevisionIds[0] ?? null}
                  onSelectRevision={(id) => handleRevisionToggle(id)}
                  isLoading={isLoadingRevisiones}
                  lockedIds={lockedRevisionIds}
                />
              </div>

              {/* ── Proyectistas ──────────────────────────────────────── */}
              <div
                className="rounded-xl border border-primary/20 bg-card p-4 space-y-4 overflow-auto min-h-0"
                style={{ gridArea: 'proyectistas' }}
              >
                <ProyectistasSection
                  selectedProyectistas={selectedProyectistas}
                  onAddProyectista={() => setShowProyectistaModal(true)}
                  onRemoveProyectista={handleRemoveProyectista}
                  especialidadLabels={especialidadLabels}
                />
              </div>

              {/* ── Contactos (full width) ───────────────────────────── */}
              <div
                className="rounded-xl border border-primary/20 bg-card p-4 space-y-4 overflow-auto min-h-0"
                style={{ gridArea: 'contactos' }}
              >
                <ContactosSection
                  selectedContactos={selectedContactos}
                  onAddContacto={handleAddContacto}
                  onRemoveContacto={handleRemoveContacto}
                  onEditContacto={handleEditContacto}
                />
              </div>

              {/* ── Delegados (full width) ─────────────────────────────── */}
              <div
                className="rounded-xl border border-primary/20 bg-card p-4 space-y-4 overflow-auto min-h-0"
                style={{ gridArea: 'delegados' }}
              >
                <DelegadosSection
                  delegados={delegadosVigentes || []}
                  selectedIds={selectedDelegados}
                  isLoading={isLoadingDelegados}
                  hasMunicipalidad={!!watchedMunicipalidadId}
                  onToggleDelegado={handleToggleDelegado}
                />
              </div>

              {/* ── Cotizar / Resumen de Cálculo ────────────────────────── */}
              <div
                className="overflow-auto min-h-0"
                style={{ gridArea: 'cotizacion' }}
              >
                <CotizacionSection
                  quote={cotizacionQuote}
                  isLoading={cotizacionMutation.isPending}
                  onCotizar={handleCotizar}
                  hasErrors={Object.keys(liqErrors).length > 0}
                  hasValidValorBase={hasValidValorBase}
                  variablesFinancieras={variablesFinancieras}
                  isLoadingVariables={isLoadingVariables}
                />
              </div>
            </div>
          </div>
        </GenericModal.Body>

        {/* ── Footer — single submit button targeting liquidacion form ─── */}
        <GenericModal.Footer className="px-6 py-4 sm:px-8 bg-muted/30 border-t border-border">
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
              form="liquidacion-form"
              onClick={() => {}}
              disabled={crearMutation.isPending}
              className="flex-1 h-10 sm:h-12 rounded-xl sm:rounded-2xl font-bold shadow-lg shadow-primary/25 gap-2 sm:max-w-[160px] text-base transition-all duration-200 hover:shadow-xl hover:shadow-primary/30 hover:-translate-y-0.5 active:translate-y-0 disabled:hover:translate-y-0 disabled:hover:shadow-lg"
              aria-label="Crear Liquidación"
            >
              {crearMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              {!crearMutation.isPending && <CheckCircle2 className="h-4 w-4 sm:hidden" />}
              <span className="hidden sm:inline">
                {crearMutation.isPending ? "Creando..." : "Crear Liquidación"}
              </span>
            </Button>
          </div>
        </GenericModal.Footer>

        <GenericModal.CloseX />
      </GenericModal.Content>
    </GenericModal>

    {/* Child Modals for Entidad */}
    <InstitucionFormModal
      open={showInstitucionModal}
      onOpenChange={setShowInstitucionModal}
      onSaved={handleEntidadSaved}
    />

    <PersonaNaturalFormModal
      open={showPersonaNaturalModal}
      onOpenChange={setShowPersonaNaturalModal}
      onSaved={handleEntidadSaved}
    />

    {/* Child Modal: Proyectista */}
    <ProyectistaFormModal
      open={showProyectistaModal}
      onOpenChange={setShowProyectistaModal}
      onSaved={handleProyectistaSaved}
      especialidadOptions={especialidadOptions}
    />

    {/* Child Modal: Contacto */}
    <ContactoFormModal
      open={showContactoModal}
      onOpenChange={setShowContactoModal}
      onSaved={handleContactoSaved}
      initialData={editingContactoIndex !== null ? selectedContactos[editingContactoIndex] : undefined}
    />
    </>
  );
}
