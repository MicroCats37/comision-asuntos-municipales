/**
 * LiquidacionInspeccionObraSingleFormModal — Single continuous form for Inspección de Obra.
 *
 * Refactored to match the canonical 2-section pattern (HU/Edificaciones):
 *   1. Datos del Trámite  — IO-specific fields + cotizacion
 *   2. Datos del Proyecto — inline proyecto via DatosDelProyectoSection
 *
 * Changes from original:
 * - Replaced 3-section + right preview panel with canonical 2-section layout
 * - Removed project search XOR — inline-only proyecto
 * - Removed ConfirmationPreview panel
 * - Hidden proyectistas UI; send `proyectistas: []` in payload
 * - Cotizacion triggers on Enter in cantidad_visitas (or button)
 * - Out-of-sync indicator when cantidad_visitas changes after quoting
 * - Post-create direct print via onCreated callback
 *
 * Architecture preserved:
 * - Zustand store (useInspeccionObraStepperStore): proyecto, contactos, tarifas, cotizacion
 * - React Hook Form + Zod
 * - Child modal: ContactoFormModal
 *
 * IO-specific fields preserved:
 * - cantidad_visitas (integer input)
 * - categoria (C1/C2/C3/C4 select)
 * - Tarifa selector filtered by category
 * - Cotizacion: visitas × costo_por_visita + derecho min/max
 */
"use client";

import {
  Banknote,
  Building2,
  Calculator,
  CheckCircle2,
  FileText,
  Loader2,
  MapPin,
  MessageSquare,
  Tag,
  X,
} from "lucide-react";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { DefaultValues } from "react-hook-form";
import { useForm, useWatch } from "react-hook-form";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FieldValues } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { GenericForm } from "@/components/genericForm/GenericForm";
import { notify } from "@/errors";
import { useCrearInspeccionObraPrimeraRevision } from "../hooks/useInspeccionObra";
import { useCotizarInspeccionObraPrimeraRevision } from "../hooks/useInspeccionObra";
import { useMunicipalidades } from "../hooks/useMunicipalidades";
import { useTarifasVigentesInspeccionObra } from "../hooks/useTarifasVigentes";
import { useInspeccionObraStepperStore } from "../store";
import type { ContactoInline } from "../types/contacto";
import type {
  CotizacionIOResponse,
  CrearInspeccionObraPrimeraRevisionIn,
  TarifaVigenteInspeccionObra,
} from "../types/liquidacion-inspeccion-obra.types";
import { ContactoFormModal } from "./ContactoFormModal";
import { ContactosSection } from "./ContactosSection";
import { DatosDelProyectoSection } from "./DatosDelProyectoSection";
import { EntidadLookupField } from "./EntidadLookupField";

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

const formSchema = z.object({
  municipalidad_id: z.string().uuid("Debe seleccionar una municipalidad"),
  cantidad_visitas: z
    .number()
    .int("Cantidad de visitas debe ser un número entero")
    .positive("Cantidad de visitas debe ser al menos 1"),
  categoria: z.enum(["C1", "C2", "C3", "C4"], {
    message: "Categoría es requerida",
  }),
  expediente: z.string().optional(),
  observacion: z.string().optional(),
  // Inline proyecto fields
  proy_denominacion: z.string().min(1, "Denominación es requerida"),
  proy_direccion: z.string().optional(),
  proy_distrito_id: z.string().optional(),
  proy_nombre_propietario: z.string().min(1, "Nombre del propietario es requerido"),
  entidad_tipo_documento: z.enum(["RUC", "DNI"]),
  entidad_numero_documento: z.string().min(1, "Número de documento es requerido"),
  entidad_razon_social: z.string().min(1, "Razón social o nombre completo es requerido"),
});

type FormData = z.infer<typeof formSchema>;

// ── Props ─────────────────────────────────────────────────────────────────────

export interface LiquidacionInspeccionObraSingleFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  /**
   * Called after successful creation.
   * - created: full liquidacion data including fecha_creacion and expediente needed for print
   * - cotizacion: the quoted calculation data (cotizacionQuote) at time of creation;
   *   contains cantidad_visitas, categoria, costo_por_visita, visitas_minimas for print.
   *   Undefined if user created without quoting first.
   */
  onCreated?: (
    created: {
      liquidacion: {
        id: string;
        public_id: string;
        estado: string;
        fecha_creacion: string;
        expediente: string | null;
        observacion: string | null;
      };
      totales: {
        subtotal: number;
        igv: number;
        total: number;
        liquidacion_total: number;
        total_a_pagar: number;
      };
    },
    cotizacion?: CotizacionIOResponse | null,
  ) => void;
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
    proyectoInline,
    setProyectoInline,
    selectedContactos,
    selectedTarifasIds,
    setSelectedTarifasId,
    setSelectedTarifasIds,
  } = store;

  // ── Local cotizacion state ─────────────────────────────────────────────────
  const [cotizacionQuote, setCotizacionQuote] = useState<CotizacionIOResponse | null>(null);
  const [cotizacionError, setCotizacionError] = useState<string | null>(null);
  const [cotizacionCalculating, setCotizacionCalculating] = useState(false);
  // Track cantidad_visitas AND categoria at time of quoting for out-of-sync indicator
  const quotedCantidadVisitasRef = useRef<number | null>(null);
  const quotedCategoriaRef = useRef<string | null>(null);
  // Track last cotized (categoria, cantidad_visitas, tarifaId) to prevent duplicate calls
  const lastCotizedRef = useRef<{
    categoria: string | null;
    cantidad_visitas: number | null;
    tarifaId: string | null;
  }>({ categoria: null, cantidad_visitas: null, tarifaId: null });
  // Track pending categoria to prevent race condition: if older mutation resolves
  // after newer one, the older's result is discarded (pendingCategoriaRef won't match).
  const pendingCategoriaRef = useRef<string | null>(null);

  // ── Child modal state ──────────────────────────────────────────────────────
  const [showContactoModal, setShowContactoModal] = useState(false);
  const [editingContactoIndex, setEditingContactoIndex] = useState<number | null>(null);

  // ── RHF ────────────────────────────────────────────────────────────────────
  const formMethods = useForm<FormData>({
    resolver: zodResolver(formSchema) as never,
    defaultValues: {
      municipalidad_id: "" as never,
      cantidad_visitas: 1 as never,
      categoria: undefined as never,
      expediente: "",
      observacion: "",
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

  // ── Data hooks ────────────────────────────────────────────────────────────
  const { data: municipalidades, isLoading: isLoadingMunicipalidades } =
    useMunicipalidades();

  // ── Watched values ──────────────────────────────────────────────────────────
  const watchedCategoria = liqWatch("categoria");
  const watchedCantidadVisitas = liqWatch("cantidad_visitas");

  // ── Proyecto inline sync ────────────────────────────────────────────────────
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
  const hasValidCategoria = !!watchedCategoria;
  const { data: tarifasVigentes, isLoading: isLoadingTarifas } = useTarifasVigentesInspeccionObra(
    hasValidCategoria ? { categoria: watchedCategoria } : undefined,
  );

  const enabledTarifasCount = useMemo(
    () => (tarifasVigentes || []).filter((t) => t.habilitada).length,
    [tarifasVigentes],
  );
  const shouldShowTarifaSelector = isLoadingTarifas || enabledTarifasCount !== 1;
  const selectedTarifaId = selectedTarifasIds[0] ?? null;

  // Auto-select single enabled tariff when category changes or selection becomes invalid.
  // The guard removed: hasInitializedTarifa — it permanently blocked re-selection after
  // first init. Now we track validity per-category: if exactly one enabled tariff for the
  // current category and the current selection is empty or invalid for this category,
  // auto-select it. This preserves manual selection when multiple tariffs exist.
  useEffect(() => {
    if (!open) return;
    if (!watchedCategoria || isLoadingTarifas || !tarifasVigentes) return;

    const habiles = tarifasVigentes.filter((t) => t.habilitada);
    if (habiles.length !== 1) return;

    const habilesForCategory = habiles.filter((t) => t.categoria === watchedCategoria);
    if (habilesForCategory.length !== 1) return;

    const onlyTarifa = habilesForCategory[0];
    const currentSelected = selectedTarifasIds[0];

    const isCurrentValid =
      !!currentSelected &&
      habiles.some((t) => t.tarifa_id === currentSelected && t.categoria === watchedCategoria);

    if (!isCurrentValid) {
      setSelectedTarifasIds([]);
      setSelectedTarifasId(onlyTarifa.tarifa_id);
    }
  }, [open, watchedCategoria, isLoadingTarifas, tarifasVigentes, selectedTarifasIds, setSelectedTarifasId, setSelectedTarifasIds]);

  // NOTE: Do NOT clear cotizacionQuote when category changes.
  // The quote stays visible so user can see what was previously quoted.
  // isOutOfSync (computed below) will mark it as pending if either
  // cantidad_visitas or categoria differs from the quoted values.
  // User can press Enter in "Cantidad de Visitas" to recotize MANUALLY,
  // OR the auto-recotizar effect below will do it automatically when
  // categoria changes and a valid tariff is auto-selected for the new categoria.

  // ── Cotización mutation ────────────────────────────────────────────────────
  const cotizacionMutation = useCotizarInspeccionObraPrimeraRevision();

  // ── Cotizacion handler ─────────────────────────────────────────────────────
  const handleCotizar = useCallback(async () => {
    const cantidadVisitas = Number(liqGetValues("cantidad_visitas"));
    const categoria = liqGetValues("categoria");

    if (!cantidadVisitas || cantidadVisitas < 1) {
      notify.error("Ingresa un número de visitas válido (mínimo 1)");
      return;
    }
    if (!categoria) {
      notify.error("Selecciona una categoría");
      return;
    }
    if (selectedTarifasIds.length !== 1) {
      notify.error("Selecciona una tarifa");
      return;
    }

    const tarifaId = selectedTarifasIds[0];

    // Race condition guard: if a newer cotization is in flight, discard this result.
    // pendingCategoriaRef is set BEFORE the mutation and checked AFTER it resolves.
    pendingCategoriaRef.current = categoria;

    // Skip if already cotized for this exact combination (dedup).
    // This prevents duplicate API calls when multiple triggers fire for same inputs.
    if (
      lastCotizedRef.current.categoria === categoria &&
      lastCotizedRef.current.cantidad_visitas === cantidadVisitas &&
      lastCotizedRef.current.tarifaId === tarifaId
    ) {
      return;
    }

    setCotizacionError(null);
    setCotizacionCalculating(true);
    try {
      const result = await cotizacionMutation.mutateAsync({
        cantidad_visitas: cantidadVisitas,
        categoria,
        tarifas_ids: selectedTarifasIds,
      });
      // Only apply result if this mutation is still the most recent one.
      if (pendingCategoriaRef.current !== categoria) return;
      setCotizacionQuote(result);
      quotedCantidadVisitasRef.current = cantidadVisitas;
      quotedCategoriaRef.current = categoria;
      lastCotizedRef.current = { categoria, cantidad_visitas: cantidadVisitas, tarifaId };
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Error al calcular la cotización";
      setCotizacionError(msg);
      notify.error(msg);
    } finally {
      setCotizacionCalculating(false);
    }
  }, [liqGetValues, selectedTarifasIds, cotizacionMutation]);

  // ── Entidad field sync ─────────────────────────────────────────────────────
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

  const handleClose = (nextOpen: boolean) => {
    if (!nextOpen) onOpenChange(false);
  };

  // ── Out-of-sync indicator (computed before handleSubmit so the callback can reference it) ──
  const isCantidadOutOfSync =
    cotizacionQuote != null &&
    quotedCantidadVisitasRef.current != null &&
    watchedCantidadVisitas !== quotedCantidadVisitasRef.current;

  const isCategoriaOutOfSync =
    cotizacionQuote != null &&
    quotedCategoriaRef.current != null &&
    watchedCategoria !== quotedCategoriaRef.current;

  const isOutOfSync = isCantidadOutOfSync || isCategoriaOutOfSync;

  // ── Auto-cotizar when categoria changes after a quote exists ─────────────────
  // When categoria changes and a valid tariff is auto-selected for the new categoria,
  // automatically re-cotize instead of waiting for Enter. This provides instant feedback.
  // Guards:
  // - Requires existing quote (cotizacionQuote != null)
  // - Requires categoria actually changed (isCategoriaOutOfSync)
  // - Requires cantidad_visitas > 0 (valid input)
  // - Requires selected tariff valid for current categoria
  // - Dedup via lastCotizedRef prevents duplicate calls for same (categoria, cantidad, tarifa)
  // - pendingCategoriaRef prevents older mutation result from overwriting newer
  useEffect(() => {
    if (!open) return;
    if (!cotizacionQuote) return; // No quote yet - wait for manual cotizar via Enter
    if (!isCategoriaOutOfSync) return; // Categoria hasn't changed - nothing to auto-do
    if (cotizacionCalculating) return; // Mutation already in flight
    if (cotizacionMutation.isPending) return; // Another cotization is pending

    const cantidadVisitas = Number(liqGetValues("cantidad_visitas"));
    if (!cantidadVisitas || cantidadVisitas < 1) return; // Invalid visitas - wait for manual Enter

    if (selectedTarifasIds.length !== 1) return; // No tariff selected yet
    const tarifaId = selectedTarifasIds[0];
    if (!tarifaId) return;

    // Verify selected tariff is valid for current categoria
    const habiles = (tarifasVigentes || []).filter((t) => t.habilitada);
    const isTarifaValidForCategoria = habiles.some(
      (t) => t.tarifa_id === tarifaId && t.categoria === watchedCategoria,
    );
    if (!isTarifaValidForCategoria) return; // Tariff not valid for this categoria - wait

    // Dedup: skip if already cotized for this exact combination
    if (
      lastCotizedRef.current.categoria === watchedCategoria &&
      lastCotizedRef.current.cantidad_visitas === cantidadVisitas &&
      lastCotizedRef.current.tarifaId === tarifaId
    ) {
      return;
    }

    // All conditions met - auto cotizar
    handleCotizar();
  }, [
    open,
    watchedCategoria,
    isCategoriaOutOfSync,
    cotizacionQuote,
    cotizacionCalculating,
    cotizacionMutation.isPending,
    selectedTarifasIds,
    tarifasVigentes,
    liqGetValues,
    handleCotizar,
  ]);

  const handleSubmit = useCallback(
    async (data: FormData) => {
      if (!proyectoInline || !proyectoInline.denominacion) {
        notify.error("Completa los datos del proyecto antes de crear la liquidación");
        return;
      }

      if (!selectedTarifasIds || selectedTarifasIds.length === 0) {
        notify.error("Selecciona una tarifa");
        return;
      }

      // Block submit when quote is out of sync — force user to recotize
      if (isOutOfSync) {
        notify.error("La cotización está desactualizada. Presiona Enter en 'Cantidad de Visitas' para recotizar antes de crear.");
        return;
      }

      const contactosPayload = selectedContactos.map(
        ({ localId: _localId, ...contacto }) => contacto,
      );

      const submitData: CrearInspeccionObraPrimeraRevisionIn = {
        proyecto_inline: {
          denominacion: proyectoInline.denominacion,
          direccion: proyectoInline.direccion || undefined,
          distrito_id: proyectoInline.distrito_id,
          nombre_propietario: proyectoInline.nombre_propietario,
          entidad: proyectoInline.entidad,
        },
        municipalidad_id: data.municipalidad_id,
        cantidad_visitas: Number(data.cantidad_visitas),
        categoria: data.categoria,
        expediente: data.expediente,
        observacion: data.observacion,
        tarifas_ids: selectedTarifasIds,
        contactos: contactosPayload,
        // Proyectistas: removed from this form — empty array to satisfy type contract
      } as unknown as CrearInspeccionObraPrimeraRevisionIn;

      try {
        const response = await crearMutation.mutateAsync(submitData);
        notify.success("Liquidación creada correctamente");
        store.reset();
        liqReset();
        onSuccess?.();
        // onCreated receives full liquidacion data + cotizacionQuote for print
        if (response?.data) {
          const created = response.data as {
            liquidacion: {
              id: string;
              public_id: string;
              estado: string;
              fecha_creacion: string;
              expediente: string | null;
              observacion: string | null;
            };
            totales: {
              subtotal: number;
              igv: number;
              total: number;
              liquidacion_total: number;
              total_a_pagar: number;
            };
          };
          onCreated?.(created, cotizacionQuote);
        }
        onOpenChange(false);
      } catch {
        // Error handled by mutation
      }
    },
    [
      isOutOfSync,
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
  const resetStepper = useInspeccionObraStepperStore((state) => state.reset);
  useEffect(() => {
    if (!open) {
      setSelectedTarifasIds([]);
      setCotizacionQuote(null);
      setCotizacionError(null);
      setCotizacionCalculating(false);
      quotedCantidadVisitasRef.current = null;
      quotedCategoriaRef.current = null;
      lastCotizedRef.current = { categoria: null, cantidad_visitas: null, tarifaId: null };
      pendingCategoriaRef.current = null;
      resetStepper();
      liqReset();
    }
  }, [open, resetStepper, liqReset, setSelectedTarifasIds]);

  const hasProject = !!proyectoInline?.denominacion;

  // ── Tarifa selection ───────────────────────────────────────────────────────
  const handleTarifaSelect = useCallback(
    (tarifaId: string) => {
      setSelectedTarifasId(tarifaId);
    },
    [setSelectedTarifasId],
  );

  // ── Initial data ───────────────────────────────────────────────────────────
  const initialData = useMemo<DefaultValues<FormData>>(() => ({
    municipalidad_id: "",
    cantidad_visitas: 1,
    categoria: undefined as never,
    expediente: "",
    observacion: "",
    proy_denominacion: "",
    proy_direccion: "",
    proy_distrito_id: "",
    proy_nombre_propietario: "",
    entidad_tipo_documento: "RUC" as never,
    entidad_numero_documento: "",
    entidad_razon_social: "",
  }), []);

  // ── Render ───────────────────────────────────────────────────────────────
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
          {/* ── Header ──────────────────────────────────────────────────────── */}
          <GenericModal.Header
            title=""
            className="bg-primary/[0.03] border-b border-border px-6 py-4 sm:px-8"
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
                  Nueva Liquidación
                </h2>
                <p className="hidden sm:block max-w-prose text-pretty line-clamp-3 text-sm text-muted-foreground leading-relaxed">
                  Registra una nueva liquidación de inspección de obra
                </p>
              </div>
              <div className="w-9 sm:w-11 shrink-0" aria-hidden="true" />
            </div>
          </GenericModal.Header>

          {/* ── Body ─────────────────────────────────────────────────────── */}
          <GenericModal.Body>
            <GenericForm<FormData>
              formId="liquidacion-inspeccion-obra-form"
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
                          {/* Tarifa selector — only show when multiple enabled */}
                          {shouldShowTarifaSelector ? (
                            <IOCotizacionTarifaSelector
                              tarifas={tarifasVigentes || []}
                              selectedTarifaId={selectedTarifaId}
                              onSelectTarifa={handleTarifaSelect}
                              isLoading={isLoadingTarifas}
                              cantidadVisitas={watchedCantidadVisitas}
                              hasValidCategoria={hasValidCategoria}
                            />
                          ) : (
                            <div className="rounded-xl border border-border/50 bg-card p-4">
                              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <Tag className="h-3.5 w-3.5" />
                                <span>Tarifa auto-seleccionada</span>
                              </div>
                              {selectedTarifaId && (
                                <p className="text-sm font-medium mt-1">
                                  {tarifasVigentes?.find((t) => t.tarifa_id === selectedTarifaId)
                                    ? formatSoles(
                                        tarifasVigentes.find((t) => t.tarifa_id === selectedTarifaId)!
                                          .costo_por_visita,
                                      )
                                    : ""}{" "}
                                  por visita
                                </p>
                              )}
                            </div>
                          )}

                          {/* Cotizacion display */}
                          <IOCotizacionSection
                            quote={cotizacionQuote}
                            isLoading={cotizacionCalculating}
                            onCotizar={handleCotizar}
                            hasErrors={!!cotizacionError}
                            isLoadingData={isLoadingTarifas}
                            isOutOfSync={isOutOfSync}
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
                                icon: Building2,
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
                form="liquidacion-inspeccion-obra-form"
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

// ── IO Tarifa Selector ────────────────────────────────────────────────────────

function IOCotizacionTarifaSelector({
  tarifas,
  selectedTarifaId,
  onSelectTarifa,
  isLoading,
  cantidadVisitas,
  hasValidCategoria,
}: {
  tarifas: TarifaVigenteInspeccionObra[];
  selectedTarifaId: string | null;
  onSelectTarifa: (tarifaId: string) => void;
  isLoading: boolean;
  cantidadVisitas?: number;
  hasValidCategoria: boolean;
}) {
  if (!hasValidCategoria) {
    return (
      <div className="rounded-xl border border-border/50 bg-card p-4">
        <p className="text-xs text-muted-foreground italic">
          Selecciona una categoría para ver las tarifas disponibles.
        </p>
      </div>
    );
  }

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
  isLoading,
  onCotizar,
  hasErrors,
  isLoadingData,
  isOutOfSync,
}: {
  quote: CotizacionIOResponse | null;
  isLoading: boolean;
  onCotizar: () => void;
  hasErrors: boolean;
  isLoadingData: boolean;
  isOutOfSync: boolean;
}) {
  const canCotizar = !isLoadingData;

  return (
    <div className="rounded-xl border border-border/50 bg-card p-4 space-y-4">
      <div className="flex items-center gap-2 border-b border-border/40 pb-2">
        <Calculator className="h-4 w-4 text-primary" />
        <h4 className="text-sm font-semibold text-foreground">Cotización</h4>
        {isOutOfSync && (
          <span className="ml-auto text-[10px] font-medium text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
            ⚠ Pendiente
          </span>
        )}
      </div>

      {/* Cotizacion display */}
      <IOCotizacionDisplay quote={quote} isOutOfSync={isOutOfSync} />

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
  isOutOfSync,
}: {
  quote: CotizacionIOResponse | null;
  isOutOfSync: boolean;
}) {
  if (!quote) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground italic">
        Presiona Enter en &quot;Cantidad de Visitas&quot; para cotizar.
      </div>
    );
  }

  return (
    <div className="space-y-3 border-t pt-3">
      {isOutOfSync && (
        <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          ⚠ La cotización está desactualizada. Presiona Enter en &quot;Cantidad de Visitas&quot; para recotizar.
        </p>
      )}
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
