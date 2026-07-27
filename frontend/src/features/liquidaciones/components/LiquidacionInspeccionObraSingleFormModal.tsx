/**
 * LiquidacionInspeccionObraSingleFormModal — Single continuous form for Inspección de Obra.
 *
 * Refactored Phase 5 to AppFormModal pattern with previous-liquidation search:
 *   1. Previous Liquidation Search — DNI/RUC search + result selection
 *   2. IO Fields — categoria, cantidad_visitas, tarifa/cotización, expediente, observacion, contactos
 *
 * Changes from previous version:
 * - Replaced GenericModal/GenericForm with AppFormModal pattern
 * - Added previous-liquidation search section (DNI/RUC only digits, 8 or 11 chars)
 * - Removed inline proyecto and municipalidad fields (derived from liquidacion_previa_id)
 * - Submit payload includes liquidacion_previa_id
 * - Keeps existing cotizacion, tarifa selector, contactos functionality
 */
"use client";

import {
  Calculator,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  FileText,
  Loader2,
  MessageSquare,
  Search,
  Tag,
  UserCheck,
  X,
} from "lucide-react";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { DefaultValues } from "react-hook-form";
import { useForm, useWatch } from "react-hook-form";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { notify } from "@/errors";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { useCrearInspeccionObraPrimeraRevision } from "../hooks/useInspeccionObra";
import { useCotizarInspeccionObraPrimeraRevision } from "../hooks/useInspeccionObra";
import { useTarifasVigentesInspeccionObra } from "../hooks/useTarifasVigentes";
import { useInspeccionObraStepperStore } from "../store";
import type { ContactoInline } from "../types/contacto";
import type { InspectorVigente } from "../types/liquidacion-general";
import type {
  CotizacionIOResponse,
  CrearInspeccionObraPrimeraRevisionIn,
  CrearInspeccionObraResponse,
  LiquidacionPreviaIOListItem,
  TarifaVigenteInspeccionObra,
} from "../types/liquidacion-inspeccion-obra.types";
import { ContactoFormModal } from "./ContactoFormModal";
import { ContactosSection } from "./ContactosSection";
import { useBuscarLiquidacionesPreviasIO } from "../hooks/useBuscarLiquidacionesPreviasIO";
import {
  formatCurrency,
  formatDate,
  getEstadoBadgeClass,
  kindLabel,
} from "./LiquidacionGeneralCard";
import { InspectorSelectorModal } from "./InspectorSelectorModal";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatSoles(value: number) {
  return `S/ ${value.toLocaleString("es-PE", { minimumFractionDigits: 2 })}`;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const CATEGORIA_OPTIONS = [
  { value: "C1", label: "Categoría C1" },
  { value: "C2", label: "Categoría C2" },
  { value: "C3", label: "Categoría C3" },
  { value: "C4", label: "Categoría C4" },
] as const;

const TIPO_LABEL = "Inspección de Obra";

// ── Form Schema ────────────────────────────────────────────────────────────────

const cantidadVisitasSchema = z
  .union([z.number(), z.nan()])
  .refine((value) => Number.isFinite(value), {
    message: "Cantidad de visitas es requerida",
  })
  .pipe(
    z
      .number()
      .int("Cantidad de visitas debe ser un número entero")
      .min(1, "Cantidad de visitas debe ser al menos 1"),
  );

const formSchema = z.object({
  cantidad_visitas: cantidadVisitasSchema,
  categoria: z.enum(["C1", "C2", "C3", "C4"], {
    message: "Categoría es requerida",
  }),
  expediente: z.string().optional(),
  observacion: z.string().optional(),
});

type FormData = z.infer<typeof formSchema>;

// ── Props ─────────────────────────────────────────────────────────────────────

export interface LiquidacionInspeccionObraSingleFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  /**
   * Called after successful creation.
   * - created: full liquidacion data (flat list item) with proyecto, municipalidad,
   *   valores, revisiones[0].tarifa for immediate post-create PDF — no refetch needed.
   */
  onCreated?: (created: CrearInspeccionObraResponse) => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function LiquidacionInspeccionObraSingleFormModal({
  open,
  onOpenChange,
  onSuccess,
  onCreated,
}: LiquidacionInspeccionObraSingleFormModalProps) {
  // ── Store ──────────────────────────────────────────────────────────────────
  const store = useInspeccionObraStepperStore();
  const {
    selectedContactos,
    selectedTarifasIds,
    setSelectedTarifasId,
    setSelectedTarifasIds,
  } = store;

  // ── Previous liquidation search state ───────────────────────────────────────
  const [searchDocNumber, setSearchDocNumber] = useState("");
  const [selectedLiquidacionPrevia, setSelectedLiquidacionPrevia] =
    useState<LiquidacionPreviaIOListItem | null>(null);
  const [liquidacionPreviaId, setLiquidacionPreviaId] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  // ── Inspector selection state ───────────────────────────────────────────────
  const [selectedInspectorId, setSelectedInspectorId] = useState<string | null>(null);
  const [selectedInspector, setSelectedInspector] = useState<InspectorVigente | null>(null);
  const [showInspectorModal, setShowInspectorModal] = useState(false);

  // ── Local cotizacion state ─────────────────────────────────────────────────
  const [cotizacionQuote, setCotizacionQuote] = useState<CotizacionIOResponse | null>(null);
  const [cotizacionError, setCotizacionError] = useState<string | null>(null);
  const [cotizacionCalculating, setCotizacionCalculating] = useState(false);

  // ── Child modal state ──────────────────────────────────────────────────────
  const [showContactoModal, setShowContactoModal] = useState(false);
  const [editingContactoIndex, setEditingContactoIndex] = useState<number | null>(null);

  // ── RHF ────────────────────────────────────────────────────────────────────
  const formMethods = useForm<FormData>({
    resolver: zodResolver(formSchema) as never,
    defaultValues: {
      cantidad_visitas: 1 as never,
      categoria: undefined as never,
      expediente: "",
      observacion: "",
    },
    mode: "onBlur",
  });

  const {
    control: liqControl,
    getValues: liqGetValues,
    reset: liqReset,
  } = formMethods;

  // ── Watched values ──────────────────────────────────────────────────────────
  const watchedCategoria = useWatch({ control: liqControl, name: "categoria" });
  const watchedCantidadVisitas = useWatch({ control: liqControl, name: "cantidad_visitas" });

  // Keep latest watched values to avoid stale closures (stepper pattern).
  // Declared after useWatch so the initial assignment captures real values.
  const latestRef = useRef({ categoria: null as string | null, cantidad_visitas: null as number | null });
  latestRef.current = { categoria: watchedCategoria, cantidad_visitas: watchedCantidadVisitas };

  // ── Previous liquidation search ────────────────────────────────────────────
  const canSearch = searchDocNumber.length === 8 || searchDocNumber.length === 11;
  const {
    items: searchResults,
    total: searchTotal,
    isLoading: isSearching,
    refetch: searchLiquidacionesPrevias,
    page: currentPage,
    totalPages: totalPages,
    setPage,
  } = useBuscarLiquidacionesPreviasIO({
    numeroDocumento: canSearch ? searchDocNumber : undefined,
    enabled: false, // Manual trigger only
  });

  const handleSearch = useCallback(() => {
    if (!canSearch) return;
    setHasSearched(true);
    searchLiquidacionesPrevias();
  }, [canSearch, searchLiquidacionesPrevias]);

  const handleSelectLiquidacionPrevia = useCallback(
    (item: LiquidacionPreviaIOListItem) => {
      setSelectedLiquidacionPrevia(item);
      setLiquidacionPreviaId(item.id);
      // Reset cotization and inspector selection when switching liquidacion previa
      setCotizacionQuote(null);
      setSelectedInspectorId(null);
      setSelectedInspector(null);
      notify.success(`Liquidación previa "${item.proyecto?.nombre ?? item.public_id}" seleccionada`);
    },
    [],
  );

  // ── Tarifas ────────────────────────────────────────────────────────────────
  const hasValidCategoria = !!watchedCategoria;
  const { data: tarifasVigentes, isLoading: isLoadingTarifas } = useTarifasVigentesInspeccionObra(
    hasValidCategoria ? { categoria: watchedCategoria } : undefined,
  );

  const selectedTarifaId = selectedTarifasIds[0] ?? null;

  // Auto-select唯一 enabled tariff when list loads, nothing is selected, and a valid category exists
  useEffect(() => {
    if (!open) return;
    if (!watchedCategoria || isLoadingTarifas || !tarifasVigentes) return;
    if (selectedTarifasIds.length !== 0) return;

    const enabledTarifas = tarifasVigentes.filter((t) => t.habilitada);
    if (enabledTarifas.length === 1) {
      setSelectedTarifasId(enabledTarifas[0].tarifa_id);
    }
  }, [open, watchedCategoria, isLoadingTarifas, tarifasVigentes, selectedTarifasIds, setSelectedTarifasId]);

  // ── Cotización mutation ────────────────────────────────────────────────────
  const cotizacionMutation = useCotizarInspeccionObraPrimeraRevision();

  // ── Cotizacion handler ─────────────────────────────────────────────────────
  // Uses latestRef pattern (stepper form approach) to avoid stale closures.
  const handleCotizar = useCallback(async () => {
    const cantidadVisitas = Number(liqGetValues("cantidad_visitas"));
    const categoria = liqGetValues("categoria") ?? latestRef.current.categoria;

    if (!Number.isFinite(cantidadVisitas) || cantidadVisitas < 1) {
      notify.error("Ingresa un número de visitas válido (mínimo 1)");
      return;
    }
    if (!categoria) {
      notify.error("Selecciona una categoría");
      return;
    }
    if (selectedTarifasIds.length < 1) {
      notify.error("Selecciona una tarifa");
      return;
    }

    setCotizacionError(null);
    setCotizacionCalculating(true);
    try {
      const result = await cotizacionMutation.mutateAsync({
        cantidad_visitas: cantidadVisitas,
        categoria: categoria as "C1" | "C2" | "C3" | "C4",
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
  }, [cotizacionMutation, liqGetValues, selectedTarifasIds]);

  // ── Contact handlers ───────────────────────────────────────────────────────
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
  const crearMutation = useCrearInspeccionObraPrimeraRevision();

  const handleSubmit = useCallback(
    async (data: FormData) => {
      if (!liquidacionPreviaId) {
        notify.error("Selecciona una liquidación previa antes de crear la liquidación");
        return;
      }

      if (!selectedTarifasIds || selectedTarifasIds.length === 0) {
        notify.error("Selecciona una tarifa");
        return;
      }

      const contactosPayload = selectedContactos.map(
        ({ localId: _localId, ...contacto }) => contacto,
      );

      const submitData: CrearInspeccionObraPrimeraRevisionIn = {
        liquidacion_previa_id: liquidacionPreviaId,
        cantidad_visitas: Number(data.cantidad_visitas),
        categoria: data.categoria,
        expediente: data.expediente,
        observacion: data.observacion,
        tarifas_ids: selectedTarifasIds,
        contactos: contactosPayload,
        inspectores_ids: selectedInspectorId ? [selectedInspectorId] : [],
      };

      try {
        const response = await crearMutation.mutateAsync(submitData);
        notify.success("Liquidación creada correctamente");
        store.reset();
        liqReset();
        setSelectedLiquidacionPrevia(null);
        setLiquidacionPreviaId(null);
        setSearchDocNumber("");
        setSelectedInspectorId(null);
        onSuccess?.();
        if (response?.data) {
          onCreated?.(response.data);
        }
      } catch {
        // Error handled by mutation
      }
    },
    [
      liquidacionPreviaId,
      selectedTarifasIds,
      selectedContactos,
      selectedInspectorId,
      crearMutation,
      store,
      liqReset,
      onSuccess,
      onCreated,
    ],
  );

  // ── Reset on close ─────────────────────────────────────────────────────────
  const resetStepper = useInspeccionObraStepperStore((state) => state.reset);
  useEffect(() => {
    if (!open) {
      setSelectedTarifasIds([]);
      setCotizacionQuote(null);
      setCotizacionError(null);
      setCotizacionCalculating(false);
      setSelectedLiquidacionPrevia(null);
      setLiquidacionPreviaId(null);
      setSearchDocNumber("");
      setHasSearched(false);
      setSelectedInspectorId(null);
      setSelectedInspector(null);
      resetStepper();
      liqReset();
    }
  }, [open, resetStepper, liqReset, setSelectedTarifasIds]);

  // ── Tarifa selection ───────────────────────────────────────────────────────
  const handleTarifaSelect = useCallback(
    (tarifaId: string) => {
      setSelectedTarifasId(tarifaId);
    },
    [setSelectedTarifasId],
  );

  const handleSelectInspector = useCallback((id: string | null, inspector: InspectorVigente | null) => {
    setSelectedInspectorId(id);
    setSelectedInspector(inspector);
  }, []);

  // ── Initial data ───────────────────────────────────────────────────────────
  const initialData = useMemo<DefaultValues<FormData>>(() => ({
    cantidad_visitas: 1,
    categoria: undefined as never,
    expediente: "",
    observacion: "",
  }), []);

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <>
      <AppFormModal<FormData>
        open={open}
        onOpenChange={onOpenChange}
        title="Nueva Liquidación"
        description={`Registra una nueva liquidación de ${TIPO_LABEL.toLowerCase()}`}
        eyebrow="Inspección de Obra"
        icon={<ClipboardCheck className="h-5 w-5 text-primary" />}
        primaryLabel="Crear Liquidación"
        primaryLoadingLabel="Creando..."
        primaryLoading={crearMutation.isPending}
        primaryDisabled={!liquidacionPreviaId || crearMutation.isPending}
        onPrimary={() => {}}
        schema={formSchema}
        initialData={initialData}
        formMethods={formMethods}
        onSubmit={handleSubmit}
        size="xl"
        bodyClassName="sm:w-[min(1500px,calc(100vw-32px))]"
        formClassName="flex flex-col"
      >
        {({ methods, isSubmitting }) => {
          const {
            register: liqReg,
            control: liqControl,
            formState: { errors: liqErrors },
          } = methods;

          return (
            <div className="flex flex-col gap-4">
              {/* ── Phase 1: Previous Liquidation Search (always visible) ────────── */}
              <div className="rounded-xl border border-border/50 bg-card p-4 space-y-4">
                <div className="flex items-center gap-2 border-b border-border/40 pb-2 text-primary">
                  <Search className="h-4 w-4" />
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">
                    Liquidación Previa
                  </h3>
                </div>

                <div className="space-y-4">
                  {/* Search input row */}
                  <div className="flex gap-3 items-end">
                    <div className="flex-1 min-w-0 space-y-1.5">
                      <label className="text-sm font-medium text-foreground flex items-center gap-2">
                        <Search className="h-4 w-4 text-muted-foreground" />
                        DNI / RUC
                      </label>
                      <Input
                        type="text"
                        placeholder="Ingrese DNI (8 dígitos) o RUC (11 dígitos)"
                        value={searchDocNumber}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                          const val = e.target.value.replace(/\D/g, "").slice(0, 11);
                          setSearchDocNumber(val);
                          setPage(1);
                          setSelectedLiquidacionPrevia(null);
                          setLiquidacionPreviaId(null);
                        }}
                        className="h-10"
                      />
                    </div>
                    <Button
                      type="button"
                      variant="default"
                      onClick={handleSearch}
                      disabled={!canSearch || isSearching}
                      className="h-10 rounded-xl font-semibold shrink-0 gap-2"
                    >
                      {isSearching ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Search className="h-4 w-4" />
                      )}
                      Buscar
                    </Button>
                  </div>

                  {/* Search results list */}
                  {searchResults.length > 0 && !selectedLiquidacionPrevia && (
                    <div className="border border-border/50 rounded-xl overflow-hidden">
                      <div className="max-h-80 overflow-y-auto divide-y divide-border/30">
                        {searchResults.map((item) => {
                          const firstRevision = item.revisiones?.[0];
                          const especialidades = firstRevision?.especialidades ?? [];
                          const valores = item.valores;
                          return (
                            <button
                              key={item.id}
                              type="button"
                              onClick={() => handleSelectLiquidacionPrevia(item)}
                              className="w-full text-left px-4 py-3 hover:bg-muted/50 transition-colors duration-150"
                            >
                              <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0 flex-1 space-y-1.5">
                                  {/* Header row: kind + estado */}
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                                      {kindLabel(item.tipo_liquidacion)}
                                    </span>
                                    <span
                                      className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${getEstadoBadgeClass(item.estado)}`}
                                    >
                                      {item.estado}
                                    </span>
                                    <span className="text-[10px] text-muted-foreground">
                                      Rev. #{item.numero_revision}
                                    </span>
                                  </div>
                                  {/* Project name */}
                                  <p className="text-sm font-semibold text-foreground truncate">
                                    {item.proyecto?.nombre ?? "Sin nombre"}
                                  </p>
                                  {/* Project code + dirección */}
                                  {item.proyecto && (
                                    <p className="text-[10px] text-muted-foreground font-mono truncate">
                                      {item.proyecto.public_id}
                                      {item.proyecto.direccion && ` · ${item.proyecto.direccion}`}
                                    </p>
                                  )}
                                  {/* Entidad */}
                                  {item.entidad && (
                                    <p className="text-[10px] text-muted-foreground truncate">
                                      {item.entidad.tipo} {item.entidad.ruc ?? ""} · {item.entidad.nombre ?? "—"}
                                    </p>
                                  )}
                                  {/* Municipalidad */}
                                  <p className="text-[10px] text-muted-foreground truncate">
                                    {item.municipalidad?.nombre ?? "Sin municipalidad"}
                                  </p>
                                  {/* Especialidades */}
                                  {especialidades.length > 0 && (
                                    <div className="flex flex-wrap gap-1 pt-0.5">
                                      {especialidades.slice(0, 3).map((esp) => (
                                        <span
                                          key={esp.id}
                                          className="text-[9px] px-1.5 py-0.5 rounded bg-secondary/50 border border-border/60 text-muted-foreground"
                                        >
                                          {esp.nombre}
                                        </span>
                                      ))}
                                      {especialidades.length > 3 && (
                                        <span className="text-[9px] px-1.5 py-0.5 text-muted-foreground">
                                          +{especialidades.length - 3}
                                        </span>
                                      )}
                                    </div>
                                  )}
                                </div>
                                <div className="text-right shrink-0 space-y-1">
                                  <p className="text-[10px] font-mono font-semibold text-primary">
                                    {item.public_id}
                                  </p>
                                  <p className="text-[10px] text-muted-foreground">
                                    {formatDate(item.fecha_registro)}
                                  </p>
                                  {valores && (
                                    <p className="text-[10px] font-semibold text-foreground">
                                      {formatCurrency(valores.total_a_pagar ?? valores.total ?? 0)}
                                    </p>
                                  )}
                                </div>
                              </div>
                            </button>
                          );
                        })}
                      </div>

                      {/* Pagination controls */}
                      {totalPages > 1 && (
                        <div className="px-4 py-2.5 bg-muted/30 border-t border-border/30 flex items-center justify-between">
                          <span className="text-[10px] text-muted-foreground">
                            Página {currentPage} de {totalPages} · {searchTotal} resultados
                          </span>
                          <div className="flex items-center gap-1">
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => setPage(currentPage - 1)}
                              disabled={currentPage <= 1 || isSearching}
                              className="h-7 w-7 p-0 rounded-lg"
                            >
                              <ChevronLeft className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => setPage(currentPage + 1)}
                              disabled={currentPage >= totalPages || isSearching}
                              className="h-7 w-7 p-0 rounded-lg"
                            >
                              <ChevronRight className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </div>
                      )}
                      {searchTotal > searchResults.length && totalPages <= 1 && (
                        <div className="px-4 py-2 bg-muted/30 text-xs text-muted-foreground text-center border-t border-border/30">
                          {searchTotal} resultados — refine tu búsqueda
                        </div>
                      )}
                    </div>
                  )}

                  {/* Selected previous liquidation summary */}
                  {selectedLiquidacionPrevia && (
                    <div className="rounded-xl border-2 border-primary/30 bg-primary/5 p-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-primary" />
                          <span className="text-sm font-semibold text-primary">Liquidación Previa Seleccionada</span>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSelectedLiquidacionPrevia(null);
                            setLiquidacionPreviaId(null);
                            setCotizacionQuote(null);
                            setHasSearched(false);
                          }}
                          className="h-7 px-2 text-xs text-muted-foreground hover:text-destructive"
                        >
                          <X className="h-3 w-3 mr-1" />
                          Cambiar
                        </Button>
                      </div>
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <p className="text-xs text-muted-foreground">Proyecto</p>
                          <p className="font-medium text-foreground truncate">
                            {selectedLiquidacionPrevia.proyecto?.nombre ?? "—"}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Municipalidad</p>
                          <p className="font-medium text-foreground truncate">
                            {selectedLiquidacionPrevia.municipalidad?.nombre ?? "—"}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Revisión</p>
                          <p className="font-medium text-foreground">
                            #{selectedLiquidacionPrevia.numero_revision}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">ID Público</p>
                          <p className="font-medium text-foreground font-mono text-xs">
                            {selectedLiquidacionPrevia.public_id}
                          </p>
                        </div>
                        {selectedLiquidacionPrevia.proyecto?.entidad && (
                          <>
                            <div>
                              <p className="text-xs text-muted-foreground">Entidad</p>
                              <p className="font-medium text-foreground truncate">
                                {selectedLiquidacionPrevia.proyecto.entidad.nombre ??
                                  selectedLiquidacionPrevia.proyecto.entidad.ruc ??
                                  "—"}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-muted-foreground">RUC</p>
                              <p className="font-medium text-foreground font-mono text-xs">
                                {selectedLiquidacionPrevia.proyecto.entidad.ruc ?? "—"}
                              </p>
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  )}

                  {/* No results message */}
                  {hasSearched && canSearch && searchResults.length === 0 && !isSearching && (
                    <p className="text-sm text-muted-foreground italic">
                      No se encontraron liquidaciones previas para este documento.
                    </p>
                  )}
                </div>
              </div>

              {/* ── Phase 2: IO Fields + Contactos (only when previous liquidation selected) ── */}
              {liquidacionPreviaId && (
                <>
                  {/* IO Fields Section */}
                  <div className="rounded-xl border border-border/50 bg-card p-4 space-y-4">
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
                            name: "cantidad_visitas",
                            label: "Cantidad de Visitas",
                            type: "number",
                            required: true,
                            placeholder: "Ej: 3 — presiona Enter",
                            icon: Calculator,
                            min: 1,
                            step: 1,
                            labelClassName: "text-foreground font-medium",
                            containerClassName: "min-w-0 w-full",
                            onKeyDown: (e) => {
                              if (e.key === "Enter") {
                                e.preventDefault();
                                handleCotizar();
                              }
                            },
                          }}
                          register={liqReg as never}
                          control={liqControl as never}
                          errors={liqErrors}
                        />
                        <GenericInput
                          field={{
                            name: "categoria",
                            label: "Categoría",
                            type: "select",
                            required: true,
                            placeholder: "Seleccione categoría",
                            icon: Tag,
                            labelClassName: "text-foreground font-medium",
                            containerClassName: "min-w-0 w-full",
                            options: CATEGORIA_OPTIONS,
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

                      {/* Right column — Cotizacion + Tarifa */}
                      <div className="space-y-4 min-w-0">
                        {/* Tarifa selector */}
                        {!hasValidCategoria ? (
                          <p className="text-xs text-muted-foreground italic">
                            Selecciona una categoría para ver las tarifas disponibles.
                          </p>
                        ) : (
                          <IOCotizacionTarifaSelector
                            tarifas={tarifasVigentes || []}
                            selectedTarifaId={selectedTarifaId}
                            onSelectTarifa={handleTarifaSelect}
                            isLoading={isLoadingTarifas}
                            cantidadVisitas={watchedCantidadVisitas}
                          />
                        )}

                        {/* Cotizacion display */}
                        <IOCotizacionSection
                          quote={cotizacionQuote}
                          hasErrors={!!cotizacionError}
                        />
                      </div>
                    </div>
                  </div>

                  {/* ── Contactos Section ────────────────────────────── */}
                  <ContactosSection
                    selectedContactos={selectedContactos}
                    onAddContacto={handleAddContacto}
                    onRemoveContacto={handleRemoveContacto}
                    onEditContacto={handleEditContacto}
                  />

                  {/* ── Inspector Selector Button/Summary ─────────────────── */}
                  <InspectorSelectorRow
                    selectedInspector={selectedInspector}
                    onOpenModal={() => setShowInspectorModal(true)}
                    onClear={() => {
                      setSelectedInspectorId(null);
                      setSelectedInspector(null);
                    }}
                  />
                </>
              )}
            </div>
          );
        }}
      </AppFormModal>

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
      <InspectorSelectorModal
        open={showInspectorModal}
        onOpenChange={setShowInspectorModal}
        liquidacionPreviaId={liquidacionPreviaId ?? ""}
        selectedInspectorId={selectedInspectorId}
        selectedInspector={selectedInspector}
        onSelectInspector={handleSelectInspector}
      />
    </>
  );
}

// ── IO Tarifa Selector ────────────────────────────────────────────────────────

function IOCotizacionTarifaSelector({
  tarifas,
  selectedTarifaId,
  onSelectTarifa,
  isLoading,
  cantidadVisitas,
}: {
  tarifas: TarifaVigenteInspeccionObra[];
  selectedTarifaId: string | null;
  onSelectTarifa: (tarifaId: string) => void;
  isLoading: boolean;
  cantidadVisitas?: number;
}) {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-border/50 bg-card p-4 animate-pulse space-y-3">
        <div className="h-4 w-32 bg-muted rounded" />
        <div className="grid grid-cols-2 gap-2">
          {[1, 2].map((i) => (
            <div key={i} className="h-14 bg-muted rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (tarifas.length === 0) {
    return (
      <div className="rounded-xl border border-border/50 bg-card p-4">
        <p className="text-xs text-muted-foreground">
          No hay tarifas vigentes disponibles
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 min-w-0">
      <label className="text-sm font-semibold text-foreground flex items-center gap-1">
        <Tag className="h-3.5 w-3.5" />
        Tarifa
      </label>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {tarifas.map((tarifa) => {
          const isSelected = selectedTarifaId === tarifa.tarifa_id;
          const isDisabled = !tarifa.habilitada;
          return (
            <button
              key={tarifa.tarifa_id}
              type="button"
              disabled={isDisabled}
              onClick={() => !isDisabled && onSelectTarifa(tarifa.tarifa_id)}
              className={[
                "rounded-xl border bg-card p-3 transition-all duration-200 text-left w-full flex flex-col gap-2",
                isSelected
                  ? "border-primary ring-1 ring-primary/30 bg-primary/5"
                  : "border-border hover:border-primary/40",
                isDisabled && "opacity-50 cursor-not-allowed",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex flex-col gap-0.5 min-w-0">
                  <span className="text-xs font-semibold text-foreground">
                    {tarifa.categoria}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {cantidadVisitas ?? tarifa.visitas_minimas} visita(s)
                  </span>
                </div>
                <div className="flex flex-col gap-0.5 items-end shrink-0">
                  <span className="text-[10px] text-muted-foreground">
                    Costo/visita:
                  </span>
                  <span className="text-xs font-semibold text-foreground">
                    {formatSoles(tarifa.costo_por_visita)}
                  </span>
                </div>
              </div>
              {isSelected && (
                <div className="text-[10px] font-semibold text-primary pt-1 border-t border-primary/20">
                  ✓ Seleccionada
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── IO Cotizacion Section ─────────────────────────────────────────────────────

function IOCotizacionSection({
  quote,
  hasErrors,
}: {
  quote: CotizacionIOResponse | null;
  hasErrors: boolean;
}) {
  return (
    <div className="rounded-xl border border-border/50 bg-card p-4 space-y-4">
      <div className="flex items-center gap-2 border-b border-border/40 pb-2">
        <Calculator className="h-4 w-4 text-primary" />
        <h4 className="text-sm font-semibold text-foreground">Cotización</h4>
      </div>

      {/* Cotizacion display */}
      <IOCotizacionDisplay quote={quote} />

      {hasErrors && (
        <p className="text-xs text-destructive font-medium">
          Error al calcular la cotización
        </p>
      )}

    </div>
  );
}

// ── IO Cotizacion Display ─────────────────────────────────────────────────────

function IOCotizacionDisplay({
  quote,
}: {
  quote: CotizacionIOResponse | null;
}) {
  if (!quote) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground italic">
        La cotización se calculará automáticamente al completar los datos.
      </div>
    );
  }

  return (
    <div className="space-y-3 border-t pt-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <span className="text-sm font-medium">Revisión #{quote.numero_revision}</span>
        <span className="text-xs text-muted-foreground">
          UIT: S/ {quote._metadata?.uit_valor?.toFixed(2) ?? "—"}
        </span>
      </div>

      {quote.calculo_visitas && (
        <div className="space-y-2 text-sm p-3 rounded-lg border border-border bg-muted/20">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Cant. Visitas</span>
            <span className="font-semibold text-foreground">
              {quote.calculo_visitas.cantidad_visitas}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Visitas base cálculo</span>
            <span className="font-semibold text-foreground">
              {quote.calculo_visitas.visitas_base_calculo}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Derecho</span>
            <span className="font-semibold text-foreground">
              {formatSoles(quote.calculo_visitas.derecho)}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Categoría</span>
            <span className="font-semibold text-foreground">
              {quote.calculo_visitas.categoria}
            </span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 border-t border-border pt-3">
        <div className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground text-xs">Subtotal</span>
          <span className="font-medium">{formatSoles(quote.totales.subtotal)}</span>
        </div>
        <div className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground text-xs">IGV ({quote._metadata.igv_valor * 100}%)</span>
          <span className="font-medium">{formatSoles(quote.totales.igv)}</span>
        </div>
        <div className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground text-xs">Total</span>
          <span className="font-medium">{formatSoles(quote.totales.total)}</span>
        </div>
        <div className="flex flex-col gap-1.5 text-base font-bold p-3 rounded-lg border border-primary bg-primary/5">
          <span className="text-primary text-xs">Total a Pagar</span>
          <span className="text-primary text-lg">{formatSoles(quote.totales.total_a_pagar)}</span>
        </div>
      </div>
    </div>
  );
}

// ── Inspector Selector Row ────────────────────────────────────────────────────

interface InspectorSelectorRowProps {
  selectedInspector: InspectorVigente | null;
  onOpenModal: () => void;
  onClear: () => void;
}

function InspectorSelectorRow({
  selectedInspector,
  onOpenModal,
  onClear,
}: InspectorSelectorRowProps) {
  return (
    <div className="rounded-xl border border-border/50 bg-card p-4 space-y-2">
      <div className="flex items-center gap-2 border-b border-border/40 pb-2 text-primary">
        <UserCheck className="h-4 w-4" />
        <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">
          Inspector
        </h3>
      </div>

      {selectedInspector ? (
        <div className="flex items-center justify-between gap-3 py-1">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <UserCheck className="h-4 w-4" />
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-sm font-semibold text-foreground truncate">
                {selectedInspector.nombre_completo}
              </span>
              <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
                <span className="inline-flex items-center px-2 py-0.5 rounded bg-muted/70 text-foreground/80 font-medium whitespace-nowrap">
                  CIP {selectedInspector.cip}
                </span>
                <span className="inline-flex items-center px-2 py-0.5 rounded bg-secondary/70 text-muted-foreground/80 whitespace-nowrap">
                  Reg. {selectedInspector.numero_registro}
                </span>
                {selectedInspector.especialidad && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded bg-secondary/70 text-muted-foreground/80 whitespace-nowrap">
                    {selectedInspector.especialidad.nombre}
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClear}
              className="h-8 px-2 text-xs text-muted-foreground hover:text-destructive"
            >
              <X className="h-3 w-3 mr-1" />
              Quitar
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onOpenModal}
              className="h-8 px-2 text-xs"
            >
              Cambiar
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-between gap-3 py-2">
          <p className="text-sm text-muted-foreground italic">
            Ningún inspector seleccionado
          </p>
          <Button
            type="button"
            variant="default"
            size="sm"
            onClick={onOpenModal}
            className="h-8 px-3 text-xs gap-1.5"
          >
            <UserCheck className="h-3.5 w-3.5" />
            Seleccionar inspector
          </Button>
        </div>
      )}
    </div>
  );
}
