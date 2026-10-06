"use client";

import { format } from "date-fns";
import { es } from "date-fns/locale";
/**
 * RhDelegadoMensualModal — Modal de 4 pasos para importar RH Mensual de Delegado.
 *
 * - Paso 1: Ingresar CIP → Buscar Candidatas
 * - Paso 2: Seleccionar candidates (Cards con inputs por-item)
 * - Paso 3: Previsualización de totales
 * - Paso 4: Confirmar → crear
 *
 * Endpoints:
 *   GET  /delegados/candidatas?cip={cip}
 *   POST /finanzas/recibos-delegados/cotizar
 *   POST /finanzas/recibos-delegados/crear
 */
import {
  Calendar as CalendarIcon,
  CheckCircle2,
  Eye,
  FileSpreadsheet,
  Filter,
  ListChecks,
  Loader2,
  Receipt,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import * as XLSX from "xlsx";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { notify } from "@/errors";
import type { DelegadoOperacionSelection } from "@/features/finanzas/components/fields/DelegadoOperacionSmartField";
import { DelegadoOperacionSmartField } from "@/features/finanzas/components/fields/DelegadoOperacionSmartField";
import {
  countActiveFiltros,
  RHActiveFiltersPanel,
  RHCandidatasFiltroModal,
} from "@/features/finanzas/components/filtros";
import type { RHCandidatasFiltroValues } from "@/features/finanzas/components/filtros/RHCandidatasFiltroModal";
import { useCandidatasDelegado } from "@/features/finanzas/hooks/useCandidatasDelegado";
import {
  useCotizarRHDelegado,
  useCrearRHDelegado,
} from "@/features/finanzas/hooks/useRHDelegadoMensual";
import {
  useRHSelectionStore,
  buildDelegadoFlowKey,
  type DelegadoSelectionEntry,
} from "@/features/finanzas/stores/rh-selection.store";
import type {
  CandidataDelegado,
  RHDelegadoCotizar,
  RHDelegadoCotizarIn,
} from "@/features/finanzas/schemas/rh-delegado-mensual.schema";
import {
  composeDetalleSections,
  LiquidacionDetalleModal,
} from "@/features/liquidaciones/components/detail";
import { useLiquidacionGeneralDetalle } from "@/features/liquidaciones/hooks/useLiquidacionGeneralDetalle";
import { getLiquidacionTipoInfo } from "@/features/liquidaciones/utils/liquidacionTipoInfo";
import { formatPublicId } from "@/features/liquidaciones/utils/formatPublicId";

interface RhDelegadoMensualModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

type Step = 1 | 2 | 3;

/** Per-item fields revealed when a Card is checked */
export interface CandidataCardFields {
  numero_rh: string;
  periodo: string;
  mes: string;
  dictamen_revision: string;
  fecha_presentacion: string;
  fecha_revision: string;
}

const DICTAMEN_OPTIONS = [
  { value: "__sin_dictamen__", label: "Seleccionar…" },
  { value: "APROBADO", label: "Aprobado" },
  { value: "OBSERVADO", label: "Observado" },
  { value: "REVISADO", label: "Revisado" },
  { value: "PENDIENTE", label: "Pendiente" },
];

const SENTINEL_NO_DICTAMEN = "__sin_dictamen__";

/** Inline date picker using shadcn Calendar popover — preserves ISO string format */
function InlineDatePicker({
  value,
  onChange,
  id,
  disabled,
}: {
  value: string;
  onChange: (v: string) => void;
  id?: string;
  disabled?: boolean;
}) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          id={id}
          variant="outline"
          disabled={disabled}
          className="w-full h-7 px-1.5 gap-1.5 justify-start text-left font-normal text-xs rounded border border-input bg-background disabled:opacity-40 disabled:cursor-not-allowed overflow-hidden"
        >
          <CalendarIcon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          {value ? (
            <span className="truncate">
              {format(new Date(value), "dd/MM/yyyy")}
            </span>
          ) : (
            <span className="text-muted-foreground">—</span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={value ? new Date(value) : undefined}
          onSelect={(date) => onChange(date ? format(date, "yyyy-MM-dd") : "")}
          locale={es}
          initialFocus
        />
      </PopoverContent>
    </Popover>
  );
}

const getCurrentPeriodParts = () => {
  const now = new Date();
  return {
    periodo: String(now.getFullYear()),
    mes: String(now.getMonth() + 1),
  };
};

const buildRhPeriodo = (periodo: string, mes: string) =>
  `${periodo}-${String(Number(mes)).padStart(2, "0")}`;

const isValidPeriodo = (value: string) => /^\d{4}$/.test(value);

const isValidMes = (value: string) => {
  const mes = Number(value);
  return Number.isInteger(mes) && mes >= 1 && mes <= 12;
};

const formatCurrency = (value?: number | null) =>
  value == null ? "—" : `S/ ${value.toFixed(2)}`;

const safeFilePart = (value: string) => value.replace(/[^a-zA-Z0-9-]/g, "-");

/**
 * Número de columnas previas a "Total" en la tabla de previsualización de Delegado.
 * La tabla tiene 14 columnas; el rótulo "Totales" abarca las primeras 6
 * (Liq, N° Liq., F. Rev., Expediente, Nro Rev, Nro. Comp.) y luego se renderizan
 * los 7 valores totales más 1 celda vacía (Nro Ord).
 */
const TOTALES_LABEL_COL_SPAN = 6;

/**
 * Guía visual por paso del wizard. Define el ícono, etiqueta corta y
 * descripción larga que se muestran en el header y en el indicador de pasos.
 * Los íconos se colorean con `primary` cuando el paso está activo o completado,
 * y con `secondary` cuando está pendiente.
 */
type StepGuideEntry = {
  icon: typeof Search;
  label: string;
  description: string;
};

const STEP_GUIDE: Record<1 | 2 | 3, StepGuideEntry> = {
  1: {
    icon: Search,
    label: "Buscar",
    description:
      "Ingresa el CIP del delegado y selecciona el periodo vigente (municipalidad + tipo) para localizar las liquidaciones candidatas.",
  },
  2: {
    icon: ListChecks,
    label: "Seleccionar",
    description:
      "Marca las candidatas que incluirás en el RH y completa N° RH, periodo, mes, dictamen y fechas por cada item.",
  },
  3: {
    icon: CheckCircle2,
    label: "Confirmar",
    description:
      "Verifica el resumen final, exporta a Excel si lo necesitas, y genera el RH mensual.",
  },
};

export function RhDelegadoMensualModal({
  open,
  onOpenChange,
  onSuccess,
}: RhDelegadoMensualModalProps) {
  const [step, setStep] = useState<Step>(1);
  const [cip, setCip] = useState("");
  const [selectedOperacion, setSelectedOperacion] =
    useState<DelegadoOperacionSelection | null>(null);
  const [fechaInicio, setFechaInicio] = useState("");
  const [fechaFin, setFechaFin] = useState("");
  const [cotizarResult, setCotizarResult] = useState<RHDelegadoCotizar | null>(
    null,
  );

  /**
   * Map of CandidataDelegado.id → per-item fields.
   * Only entries for checked cards are present.
   */

  /** Periodo vigente del delegado seleccionado para este RH mensual (required for cotizar/crear). */
  const [delegadoOperacionId, setDelegadoOperacionId] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filtros, setFiltros] = useState<RHCandidatasFiltroValues>({});
  const [filterModalOpen, setFilterModalOpen] = useState(false);

  // ── Ver detalle state (Module 6) ─────────────────────────────────────
  const [detalleRowId, setDetalleRowId] = useState<string | null>(null);

  // ── Ver detalle hook (after detalleRow so we can derive id + tipoCodigo from it) ──
  const { data: detalleData, isLoading: isLoadingDetalle } =
    useLiquidacionGeneralDetalle({
      id: detalleRowId,
    });

  // ── Selection store (Module 1) — replaces local selectedCardFields state ─────
  const {
    toggleSelection,
    addSelection,
    removeSelection,
    clearSelections,
    isSelected,
    getSelectedItems,
    getSelectedCount,
  } = useRHSelectionStore();

  /** Stable flow key for this delegado session */
  const flowKey = buildDelegadoFlowKey(cip, {
    delegado_operacion_id: selectedOperacion?.id,
    municipalidad_id: selectedOperacion?.municipalidad_id,
    tipo_liquidacion_id: selectedOperacion?.tipo_liquidacion_id ?? undefined,
    tipo_delegado: selectedOperacion?.tipo,
  });

  const cotizarMutation = useCotizarRHDelegado();
  const crearMutation = useCrearRHDelegado();

  const {
    data: candidatasData,
    isLoading: isLoadingCandidatos,
    isError: isErrorCandidatas,
    refetch,
  } = useCandidatasDelegado({
    cip,
    // SmartField path: usa delegado_operacion_id directamente
    delegado_operacion_id: selectedOperacion?.id,
    // Filter-based path legacy (only used if SmartField ID not provided)
    municipalidad_id: selectedOperacion?.municipalidad_id || undefined,
    tipo_liquidacion_id: selectedOperacion?.tipo_liquidacion_id || undefined,
    tipo_delegado: selectedOperacion?.tipo || undefined,
    fecha_inicio: fechaInicio || undefined,
    fecha_fin: fechaFin || undefined,
    page,
    pageSize,
    expediente: filtros.expediente,
    numero: filtros.numero,
    propietario: filtros.propietario,
    direccion: filtros.direccion,
    enabled: step === 2,
  });

  const candidatas: CandidataDelegado[] = candidatasData?.candidatas ?? [];
  const delegado = candidatasData?.delegado;

  // ── Derived from candidatas (after declaration to avoid TDZ) ─────────────────
  const detalleRow = detalleRowId
    ? (candidatas.find((c) => c.id === detalleRowId) ?? null)
    : null;

  // ── Ver detalle hook (after detalleRow so we can derive id + tipoCodigo from it) ──
  // useLiquidacionGeneralDetalle is called above (before Selection store) since it only depends on detalleRowId.
  // Note: tipo dispatch for composeDetalleSections is handled by reading detalleRow.tipo_liquidacion.codigo
  //   in the modal render section below.

  // Sync delegadoOperacionId when selectedOperacion changes
  useEffect(() => {
    if (selectedOperacion) {
      setDelegadoOperacionId(selectedOperacion.id);
    }
  }, [selectedOperacion]);

  const resetForm = useCallback(() => {
    setStep(1);
    setCip("");
    setSelectedOperacion(null);
    setFechaInicio("");
    setFechaFin("");
    setCotizarResult(null);
    clearSelections(flowKey);
    setDelegadoOperacionId("");
    setPage(1);
    setPageSize(20);
    setFiltros({});
  }, [flowKey, clearSelections]);

  const handleClose = useCallback(() => {
    resetForm();
    onOpenChange(false);
  }, [onOpenChange, resetForm]);

  // ── Paso 1 → 2: buscar candidatas ────────────────────────────────────
  const handleBuscar = useCallback(async () => {
    if (!cip.trim()) {
      notify.error("Ingresa el CIP del delegado");
      return;
    }
    if (!selectedOperacion) {
      notify.error("Selecciona un periodo vigente del delegado");
      return;
    }
    if (fechaInicio && fechaFin && fechaInicio > fechaFin) {
      notify.error("La fecha de inicio no puede ser mayor que la fecha fin");
      return;
    }
    setCotizarResult(null);
    setPage(1);
    try {
      await refetch();
      setStep(2);
    } catch {
      notify.error("No se pudieron buscar las candidatas");
    }
  }, [selectedOperacion, fechaInicio, fechaFin, cip, refetch]);

  const getSelectionEntry = useCallback(
    (id: string): DelegadoSelectionEntry | undefined => {
      const items = getSelectedItems(flowKey) as DelegadoSelectionEntry[];
      return items.find((e) => e.candidate.id === id);
    },
    [flowKey, getSelectedItems],
  );

  const toggleCard = useCallback(
    (c: CandidataDelegado, checked: boolean) => {
      if (checked) {
        const current = getCurrentPeriodParts();
        const entry: DelegadoSelectionEntry = {
          cotizarItem: {
            numero_rh: "",
            periodo: Number(current.periodo),
            mes: Number(current.mes),
            dictamen_revision: "",
            fecha_presentacion: "",
            fecha_revision: "",
          },
          candidate: c,
        };
        addSelection(flowKey, c.id, entry);
      } else {
        removeSelection(flowKey, c.id);
      }
    },
    [flowKey, addSelection, removeSelection],
  );

  const updateCardField = useCallback(
    (id: string, field: keyof CandidataCardFields, value: string) => {
      const entry = getSelectionEntry(id);
      if (!entry) return;
      const updated: DelegadoSelectionEntry = {
        ...entry,
        cotizarItem: { ...entry.cotizarItem, [field]: value },
      };
      addSelection(flowKey, id, updated);
    },
    [flowKey, getSelectionEntry, addSelection],
  );

  // ── Paso 2 → 3: cotizar ────────────────────────────────────────────
  const handleCotizar = useCallback(async () => {
    const selectedEntries = getSelectedItems(
      flowKey,
    ) as DelegadoSelectionEntry[];
    if (selectedEntries.length === 0) {
      notify.error("Selecciona al menos una candidata");
      return;
    }

    const invalidPeriodo = selectedEntries.some(
      (e) => !isValidPeriodo(String(e.cotizarItem.periodo ?? "")),
    );
    if (invalidPeriodo) {
      notify.error(
        "Ingresa un periodo válido (YYYY) para cada candidata seleccionada",
      );
      return;
    }

    const invalidMes = selectedEntries.some(
      (e) => !isValidMes(String(e.cotizarItem.mes ?? "")),
    );
    if (invalidMes) {
      notify.error(
        "Ingresa un mes válido (1-12) para cada candidata seleccionada",
      );
      return;
    }

    const firstEntry = selectedEntries[0];
    const rhPeriodo = buildRhPeriodo(
      String(firstEntry.cotizarItem.periodo),
      String(firstEntry.cotizarItem.mes),
    );

    const items: RHDelegadoCotizarIn["items"] = selectedEntries.map((entry) => {
      const {
        numero_rh,
        periodo,
        mes,
        dictamen_revision,
        fecha_presentacion,
        fecha_revision,
      } = entry.cotizarItem;
      return {
        liquidacion_general_id: entry.candidate.id,
        especialidad_revision_id: entry.candidate.especialidad_candidata.id,
        numero_rh: numero_rh || undefined,
        periodo,
        mes,
        dictamen_revision: dictamen_revision || undefined,
        fecha_presentacion: fecha_presentacion || undefined,
        fecha_revision: fecha_revision || undefined,
      };
    });

    try {
      const result = await cotizarMutation.cotizar({
        cip,
        periodo: firstEntry.cotizarItem.periodo!,
        mes: firstEntry.cotizarItem.mes!,
        delegado_operacion_id: delegadoOperacionId,
        items,
      });
      setCotizarResult(result.data);
      setStep(3);
    } catch {
      // Error handled by mutation
    }
  }, [flowKey, getSelectedItems, cip, cotizarMutation, delegadoOperacionId]);

  // ── Paso 3 → crear/exportar (todo en este paso) ────────────────────────
  // Antes había un handleConfirmar que pasaba a step 4, pero step 3 y 4 eran
  // idénticos. Ahora step 3 muestra el preview Y los botones de acción.

  const handleExportExcel = useCallback(() => {
    if (!cotizarResult) return;

    const headerPeriodoStr =
      cotizarResult.periodo != null && cotizarResult.mes != null
        ? `${cotizarResult.periodo}-${String(cotizarResult.mes).padStart(2, "0")}`
        : "—";

    const rows: Array<Record<string, string | number>> =
      cotizarResult.items.map((item, index) => ({
        Item: index + 1,
        Delegado: cotizarResult.delegado.nombre_completo,
        CIP: cotizarResult.delegado.cip,
        Periodo: headerPeriodoStr,
        "Nro Liq.": item.liquidacion_especifica_numero ?? "",
        Expediente: item.exp_liqui,
        "Nro revision": item.numero_revision ?? "",
        "Nro Comp.": item.comprobante_activo
          ? `${item.comprobante_activo.serie ?? ""}-${item.comprobante_activo.numero ?? ""}`
          : "",
        "Fecha revision": item.fecha_revision ?? "",
        "Nro RH": item.numero_rh ?? "",
        "Periodo item": item.periodo ?? "",
        "Mes item": item.mes ?? "",
        Dictamen: item.dictamen_revision ?? "",
        "Fecha presentacion": item.fecha_presentacion ?? "",
        "Total liquidacion": item.total_liquidacion ?? 0,
        "Sub total liquidacion": item.sub_total_liquidacion ?? 0,
        "Importe bruto": item.imp_bruto,
        "Renta CIP": item.renta_cip ?? 0,
        "Aporte Codemu": item.aporte_codemu ?? 0,
        "Fondo comun": item.fondo_comun ?? 0,
        "Neto honorario": item.neto_honorario ?? 0,
      }));

    rows.push({
      Item: "",
      Delegado: "TOTALES",
      CIP: cotizarResult.delegado.cip,
      Periodo: headerPeriodoStr,
      "Nro Liq.": "",
      Expediente: "",
      "Nro revision": "",
      "Nro Comp.": "",
      "Fecha revision": "",
      "Nro RH": "",
      "Periodo item": "",
      "Mes item": "",
      Dictamen: "",
      "Fecha presentacion": "",
      "Total liquidacion": cotizarResult.items.reduce(
        (sum, item) => sum + (item.total_liquidacion ?? 0),
        0,
      ),
      "Sub total liquidacion": cotizarResult.items.reduce(
        (sum, item) => sum + (item.sub_total_liquidacion ?? 0),
        0,
      ),
      "Importe bruto": cotizarResult.totales.sub_total,
      "Renta CIP": cotizarResult.totales.renta_cip,
      "Aporte Codemu": cotizarResult.totales.aporte_codemu,
      "Fondo comun": cotizarResult.totales.fondo_comun,
      "Neto honorario": cotizarResult.totales.neto_honorario,
    });

    const workbook = XLSX.utils.book_new();
    const worksheet = XLSX.utils.json_to_sheet(rows);
    XLSX.utils.book_append_sheet(workbook, worksheet, "Resumen RH");
    XLSX.writeFile(
      workbook,
      `rh-delegado-${safeFilePart(cotizarResult.delegado.cip)}-${safeFilePart(headerPeriodoStr)}.xlsx`,
    );
  }, [cotizarResult]);

  // ── Paso 4: crear ───────────────────────────────────────────────────
  const handleCrear = useCallback(async () => {
    if (!cotizarResult) return;

    const selectedEntries = getSelectedItems(
      flowKey,
    ) as DelegadoSelectionEntry[];
    if (selectedEntries.length === 0) {
      notify.error("No hay candidatas seleccionadas");
      return;
    }

    const invalidPeriodo = selectedEntries.some(
      (e) => !isValidPeriodo(String(e.cotizarItem.periodo ?? "")),
    );
    if (invalidPeriodo) {
      notify.error(
        "Ingresa un periodo válido (YYYY) para cada candidata seleccionada",
      );
      return;
    }

    const invalidMes = selectedEntries.some(
      (e) => !isValidMes(String(e.cotizarItem.mes ?? "")),
    );
    if (invalidMes) {
      notify.error(
        "Ingresa un mes válido (1-12) para cada candidata seleccionada",
      );
      return;
    }

    const firstEntry = selectedEntries[0];
    const rhPeriodo = buildRhPeriodo(
      String(firstEntry.cotizarItem.periodo),
      String(firstEntry.cotizarItem.mes),
    );

    const items: RHDelegadoCotizarIn["items"] = selectedEntries.map((entry) => {
      const {
        numero_rh,
        periodo,
        mes,
        dictamen_revision,
        fecha_presentacion,
        fecha_revision,
      } = entry.cotizarItem;
      return {
        liquidacion_general_id: entry.candidate.id,
        especialidad_revision_id: entry.candidate.especialidad_candidata.id,
        numero_rh: numero_rh || undefined,
        periodo,
        mes,
        dictamen_revision: dictamen_revision || undefined,
        fecha_presentacion: fecha_presentacion || undefined,
        fecha_revision: fecha_revision || undefined,
      };
    });

    try {
      await crearMutation.crear({
        cip,
        periodo: firstEntry.cotizarItem.periodo!,
        mes: firstEntry.cotizarItem.mes!,
        delegado_operacion_id: delegadoOperacionId,
        items,
      });
      notify.success("RH Mensual de delegado creado correctamente");
      handleClose();
      onSuccess?.();
    } catch {
      // Error handled by mutation
    }
  }, [
    cotizarResult,
    flowKey,
    getSelectedItems,
    cip,
    crearMutation,
    handleClose,
    onSuccess,
    delegadoOperacionId,
  ]);

  const isPending = cotizarMutation.isPending || crearMutation.isPending;
  const selectedCount = getSelectedCount(flowKey);

  return (
    <GenericModal open={open} onOpenChange={handleClose} preventClose={false}>
      <GenericModal.Content size="lg">
        <GenericModal.Header
          title=""
          className="bg-primary/[0.03] border-b border-border px-6 py-5"
        >
          <div className="flex items-center gap-3 w-full">
            <div className="p-2 bg-primary/10 rounded-xl border border-primary/20 shadow-sm shrink-0">
              <FileSpreadsheet className="h-5 w-5 text-primary" />
            </div>
            <div className="flex flex-col gap-0.5 min-w-0 flex-1">
              <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                Recibos de Honorario - Delegados
              </span>
              <h2 className="text-2xl font-black tracking-tight text-foreground leading-tight">
                RH Mensual — Importar Candidatas
              </h2>
              <p className="hidden sm:block text-sm text-muted-foreground leading-relaxed">
                {STEP_GUIDE[step].description}
              </p>
            </div>
            <div className="w-9 shrink-0" aria-hidden="true" />
          </div>
        </GenericModal.Header>

        <GenericModal.Body className="space-y-6">
          {/* ── Indicador de pasos con íconos y colores primary/secondary ── */}
          <div className="flex items-center gap-2 justify-center py-1">
            {([1, 2, 3] as const).map((s) => {
              const StepIcon = STEP_GUIDE[s].icon;
              const isActive = step === s;
              const isCompleted = step > s;
              return (
                <div key={s} className="flex items-center gap-2">
                  <div className="flex flex-col items-center gap-1.5 min-w-[5rem]">
                    <div
                      className={`flex h-9 w-9 items-center justify-center rounded-full border-2 transition-all ${
                        isActive
                          ? "bg-primary text-primary-foreground border-primary shadow-md shadow-primary/20"
                          : isCompleted
                            ? "bg-primary/15 text-primary border-primary/40"
                            : "bg-secondary/40 text-secondary-foreground/70 border-secondary/50"
                      }`}
                    >
                      <StepIcon className="h-4 w-4" />
                    </div>
                    <span
                      className={`text-[9px] font-bold uppercase tracking-wider text-center ${
                        isActive
                          ? "text-primary"
                          : isCompleted
                            ? "text-primary/70"
                            : "text-muted-foreground/70"
                      }`}
                    >
                      {s}. {STEP_GUIDE[s].label}
                    </span>
                  </div>
                  {s < 4 && (
                    <div
                      className={`h-0.5 w-10 rounded ${
                        step > s ? "bg-primary/50" : "bg-secondary/40"
                      }`}
                    />
                  )}
                </div>
              );
            })}
          </div>

          {/* ── Paso 1: Buscar — CIP del delegado + rango de fechas ── */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="cip">CIP del Delegado</Label>
                <Input
                  id="cip"
                  value={cip}
                  onChange={(e) => setCip(e.target.value)}
                  placeholder="Ej. 12345"
                  className="h-10 rounded-xl font-semibold"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") void handleBuscar();
                  }}
                />
              </div>
              {/* SmartField: periodos vigentes del delegado por CIP */}
              <DelegadoOperacionSmartField
                cip={cip}
                onSelect={(selection) => setSelectedOperacion(selection)}
                selectedId={selectedOperacion?.id}
              />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="fecha-inicio">Fecha Inicio</Label>
                  <Input
                    id="fecha-inicio"
                    type="date"
                    value={fechaInicio}
                    onChange={(e) => setFechaInicio(e.target.value)}
                    className="h-10 rounded-xl font-semibold"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void handleBuscar();
                    }}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="fecha-fin">Fecha Fin</Label>
                  <Input
                    id="fecha-fin"
                    type="date"
                    value={fechaFin}
                    onChange={(e) => setFechaFin(e.target.value)}
                    className="h-10 rounded-xl font-semibold"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void handleBuscar();
                    }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* ── Paso 2: Seleccionar — listado de candidatas con edición inline por fila ── */}
          {step === 2 && (
            <div className="space-y-4">
              {/* Delegado info bar */}
              {delegado && (
                <div className="rounded-xl border border-border/50 bg-card p-4 space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground font-semibold">
                      Delegado:
                    </span>
                    <span className="font-bold">
                      {delegado.nombre_completo}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground font-semibold">
                      CIP:
                    </span>
                    <span className="font-bold">{delegado.cip}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground font-semibold">
                      Disponibles:
                    </span>
                    <span className="font-bold">
                      {
                        candidatas.filter((c) => !isSelected(flowKey, c.id))
                          .length
                      }
                    </span>
                  </div>
                </div>
              )}

              <div className="flex justify-end">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setFilterModalOpen(true)}
                  className="h-8 px-3 text-xs rounded-lg gap-1.5 border-primary/30 text-primary hover:bg-primary/5"
                >
                  <Filter className="h-3.5 w-3.5" />
                  Filtros
                  {countActiveFiltros(filtros) > 0 && (
                    <span className="inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold rounded-full bg-primary text-primary-foreground">
                      {countActiveFiltros(filtros)}
                    </span>
                  )}
                </Button>
              </div>

              <RHActiveFiltersPanel
                filtros={filtros}
                onClear={() => {
                  setFiltros({});
                  setPage(1);
                }}
              />

              {/* ── Selected items table (editable, above available candidates) ── */}
              {selectedCount > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between px-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-primary">
                        {selectedCount} seleccionado
                        {selectedCount !== 1 ? "s" : ""}
                      </span>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => clearSelections(flowKey)}
                      className="h-6 px-2 text-xs text-muted-foreground hover:text-destructive gap-1"
                    >
                      <Trash2 className="h-3 w-3" />
                      Limpiar todo
                    </Button>
                  </div>
                  {/* Selected items table header */}
                  <div className="flex items-center gap-3 px-3 py-2 bg-primary/5 rounded-t-lg border border-primary/20 text-[10px] font-bold uppercase tracking-wider text-primary">
                    <div className="w-6 shrink-0" />
                    <div className="w-20 shrink-0">Nro Ord</div>
                    <div className="w-24 shrink-0">Expediente</div>
                    <div className="w-20 shrink-0">N° Liq.</div>
                    <div className="flex-1 min-w-0">Especialidad</div>
                    <div className="w-20 shrink-0 text-right">Monto</div>
                    <div className="w-20 shrink-0">Periodo</div>
                    <div className="w-20 shrink-0">Mes</div>
                    <div className="w-24 shrink-0">Dictamen</div>
                    <div className="flex-1 min-w-0">F. Pres.</div>
                    <div className="flex-1 min-w-0">F. Rev.</div>
                    <div className="w-8 shrink-0" />
                  </div>
                  <div className="border border-t-0 border-primary/20 rounded-b-lg overflow-hidden">
                    {(
                      getSelectedItems(flowKey) as DelegadoSelectionEntry[]
                    ).map((entry) => {
                      const { cotizarItem, candidate } = entry;
                      return (
                        <div
                          key={candidate.id}
                          className="flex items-center gap-3 px-3 py-2 border-b border-border/50 last:border-b-0 bg-primary/[0.02] hover:bg-primary/[0.04] transition-all duration-150"
                        >
                          {/* Remove button */}
                          <button
                            type="button"
                            onClick={() =>
                              removeSelection(flowKey, candidate.id)
                            }
                            className="w-6 shrink-0 h-6 flex items-center justify-center rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                            aria-label="Quitar de seleccionados"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>

                          {/* Nro Orden (editable) */}
                          <Input
                            id={`sel-nro-rh-${candidate.id}`}
                            type="text"
                            value={cotizarItem.numero_rh ?? ""}
                            onChange={(e) =>
                              updateCardField(
                                candidate.id,
                                "numero_rh",
                                e.target.value,
                              )
                            }
                            placeholder="N° RH"
                            className="w-20 shrink-0 h-7 text-xs rounded border border-input bg-background"
                          />

                          {/* Expediente (read-only) */}
                          <div className="w-24 shrink-0">
                            <p className="font-mono font-bold text-xs text-foreground truncate">
                              {candidate.expediente ?? "—"}
                            </p>
                          </div>

                          {/* N° Liq. (read-only) */}
                          <div className="w-20 shrink-0 overflow-hidden">
                            <p className="font-mono text-xs font-bold text-foreground truncate">
                              {candidate.liquidacion_especifica_numero ?? "—"}
                            </p>
                          </div>

                          {/* Especialidad (read-only) */}
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium text-foreground truncate">
                              {candidate.especialidad_candidata.nombre}
                            </p>
                            <p className="text-[10px] text-muted-foreground truncate">
                              {candidate.tipo_liquidacion?.nombre ?? "—"}
                            </p>
                          </div>

                          {/* Monto (read-only) */}
                          <div className="w-20 shrink-0 text-right">
                            <p className="text-xs font-black text-primary">
                              {candidate.sub_total != null
                                ? `S/ ${candidate.sub_total.toFixed(2)}`
                                : "—"}
                            </p>
                          </div>

                          {/* Periodo (editable) */}
                          <Input
                            id={`sel-periodo-${candidate.id}`}
                            type="number"
                            value={cotizarItem.periodo ?? ""}
                            onChange={(e) =>
                              updateCardField(
                                candidate.id,
                                "periodo",
                                e.target.value,
                              )
                            }
                            placeholder="Año"
                            className="w-20 shrink-0 h-7 text-xs rounded border border-input bg-background"
                          />

                          {/* Mes (editable) */}
                          <Input
                            id={`sel-mes-${candidate.id}`}
                            type="number"
                            min={1}
                            max={12}
                            value={cotizarItem.mes ?? ""}
                            onChange={(e) =>
                              updateCardField(
                                candidate.id,
                                "mes",
                                e.target.value,
                              )
                            }
                            placeholder="Mes"
                            className="w-20 shrink-0 h-7 text-xs rounded border border-input bg-background"
                          />

                          {/* Dictamen (editable select) */}
                          <Select
                            value={
                              cotizarItem.dictamen_revision ||
                              SENTINEL_NO_DICTAMEN
                            }
                            onValueChange={(v) =>
                              updateCardField(
                                candidate.id,
                                "dictamen_revision",
                                v === SENTINEL_NO_DICTAMEN ? "" : v,
                              )
                            }
                          >
                            <SelectTrigger
                              id={`sel-dictamen-${candidate.id}`}
                              className="w-24 shrink-0 h-7 px-1.5 text-xs rounded border border-input bg-background"
                            >
                              <SelectValue placeholder="—" />
                            </SelectTrigger>
                            <SelectContent>
                              {DICTAMEN_OPTIONS.map((opt) => (
                                <SelectItem
                                  key={opt.value}
                                  value={opt.value}
                                  className="text-xs"
                                >
                                  {opt.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>

                          {/* Fecha Presentación (editable) */}
                          <div className="flex-1 min-w-0">
                            <InlineDatePicker
                              id={`sel-fec-pres-${candidate.id}`}
                              value={cotizarItem.fecha_presentacion ?? ""}
                              onChange={(v) =>
                                updateCardField(
                                  candidate.id,
                                  "fecha_presentacion",
                                  v,
                                )
                              }
                            />
                          </div>

                          {/* Fecha Revisión (editable) */}
                          <div className="flex-1 min-w-0">
                            <InlineDatePicker
                              id={`sel-fec-rev-${candidate.id}`}
                              value={cotizarItem.fecha_revision ?? ""}
                              onChange={(v) =>
                                updateCardField(
                                  candidate.id,
                                  "fecha_revision",
                                  v,
                                )
                              }
                            />
                          </div>

                          {/* Ver detalle button */}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setDetalleRowId(candidate.id);
                            }}
                            className="w-8 shrink-0 h-7 flex items-center justify-center rounded border border-transparent hover:border-primary/30 hover:bg-primary/5 text-muted-foreground hover:text-primary transition-colors"
                            aria-label="Ver detalle"
                            title="Ver detalle"
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Row-based grid (compact, horizontal, spreadsheet-like) */}
              {isLoadingCandidatos ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : isErrorCandidatas ? (
                <div className="flex flex-col items-center justify-center p-8 text-destructive text-sm">
                  Error al cargar las candidatas
                </div>
              ) : (
                <div className="rounded-xl border border-border bg-card overflow-hidden">
                  {/* Header row — always visible above rows */}
                  <div className="flex items-center gap-3 px-3 py-2 bg-muted/40 border-b border-border text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    <div className="w-6 shrink-0" />
                    <div className="w-24 shrink-0">Expediente</div>
                    <div className="w-20 shrink-0">N° Liq.</div>
                    <div className="flex-1 min-w-0">Comprobante</div>
                    <div className="flex-1 min-w-0">Especialidad</div>
                    <div className="w-20 shrink-0 text-right">Monto</div>
                    <div className="w-8 shrink-0" />
                  </div>
                  <ScrollArea>
                    {candidatas
                      .filter((c) => !isSelected(flowKey, c.id))
                      .map((c) => (
                        <div
                          key={c.id}
                          className="flex items-center gap-3 px-3 py-2 border-b border-border/50 last:border-b-0 hover:bg-muted/30 transition-all duration-150"
                        >
                          <Checkbox
                            id={`card-${c.id}`}
                            checked={false}
                            onCheckedChange={(v) => toggleCard(c, !!v)}
                            className="shrink-0"
                          />

                          <div
                            className="w-24 shrink-0 cursor-pointer"
                            onClick={() => toggleCard(c, true)}
                          >
                            <p className="font-mono font-bold text-xs text-foreground truncate">
                              {c.expediente ?? "—"}
                            </p>
                          </div>

                          <div
                            className="w-20 shrink-0 cursor-pointer overflow-hidden"
                            onClick={() => toggleCard(c, true)}
                          >
                            <p className="font-mono text-xs font-bold text-foreground truncate">
                              {c.liquidacion_especifica_numero ?? "—"}
                            </p>
                          </div>

                          <div
                            className="flex-1 min-w-0 cursor-pointer overflow-hidden"
                            onClick={() => toggleCard(c, true)}
                          >
                            {c.comprobante_activo ? (
                              <>
                                <p className="font-mono text-xs text-foreground truncate leading-tight">
                                  {`${c.comprobante_activo.serie ?? ""}-${c.comprobante_activo.numero ?? ""}`}
                                </p>
                                <p className="text-[10px] text-muted-foreground truncate leading-tight">
                                  {c.comprobante_activo.tipo_comprobante ?? ""}
                                  {c.comprobante_activo.fecha_emision
                                    ? ` · ${c.comprobante_activo.fecha_emision}`
                                    : ""}
                                </p>
                              </>
                            ) : (
                              <p className="text-[10px] text-muted-foreground italic leading-tight">
                                Sin comprobante
                              </p>
                            )}
                          </div>

                          <div
                            className="flex-1 min-w-0 cursor-pointer"
                            onClick={() => toggleCard(c, true)}
                          >
                            <p className="text-xs font-medium text-foreground truncate">
                              {c.especialidad_candidata.nombre}
                            </p>
                            <p className="text-[10px] text-muted-foreground truncate">
                              {c.tipo_liquidacion?.nombre ?? "—"}
                              {c.municipalidad_nombre &&
                                ` · ${c.municipalidad_nombre}`}
                            </p>
                          </div>

                          <div
                            className="w-20 shrink-0 text-right cursor-pointer"
                            onClick={() => toggleCard(c, true)}
                          >
                            <p className="text-xs font-black text-primary">
                              {c.sub_total != null
                                ? `S/ ${c.sub_total.toFixed(2)}`
                                : "—"}
                            </p>
                          </div>

                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setDetalleRowId(c.id);
                            }}
                            className="w-8 shrink-0 h-7 flex items-center justify-center rounded border border-transparent hover:border-primary/30 hover:bg-primary/5 text-muted-foreground hover:text-primary transition-colors"
                            aria-label="Ver detalle"
                            title="Ver detalle"
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ))}
                    {candidatas.filter((c) => !isSelected(flowKey, c.id))
                      .length === 0 && (
                      <div className="py-12 text-center text-muted-foreground text-sm border-t border-border">
                        {candidatas.length === 0
                          ? "No hay liquidaciones candidatas para este delegado"
                          : "Todas las candidatas han sido seleccionadas"}
                      </div>
                    )}
                  </ScrollArea>
                  {candidatasData && (
                    <div className="border-t border-border bg-background/95 px-3">
                      <Pagination
                        currentPage={candidatasData.page ?? 1}
                        totalPages={candidatasData.totalPages ?? 1}
                        onPageChange={(p) => setPage(p)}
                        onPageSizeChange={(size) => {
                          setPageSize(size);
                          setPage(1);
                        }}
                        totalItems={candidatasData.total ?? 0}
                        pageSize={candidatasData.pageSize ?? 20}
                        className="py-3"
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── Paso 3: Revisar y Confirmar — previsualización + resumen final ── */}
          {step === 3 && cotizarResult && (
            <div className="space-y-4">
              <div className="rounded-xl border border-primary/30 bg-primary/5 p-4 space-y-3">
                <div>
                  <h3 className="text-sm font-black uppercase tracking-wide text-primary">
                    Resumen de confirmación
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Verifica estos datos antes de crear el RH mensual.
                  </p>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                  <div>
                    <p className="text-[10px] font-bold uppercase text-muted-foreground">
                      Delegado
                    </p>
                    <p className="font-semibold truncate">
                      {cotizarResult.delegado.nombre_completo}
                    </p>
                  </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase text-muted-foreground">
                        CIP
                      </p>
                      <p className="font-semibold">
                        {cotizarResult.delegado.cip}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase text-muted-foreground">
                        Periodo
                      </p>
                      <p className="font-semibold">
                        {cotizarResult.periodo != null &&
                        cotizarResult.mes != null
                          ? `${cotizarResult.periodo}-${String(cotizarResult.mes).padStart(2, "0")}`
                          : "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase text-muted-foreground">
                        Items
                      </p>
                      <p className="font-semibold">
                        {cotizarResult.items.length}
                      </p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm border-t border-primary/20 pt-3">
                    <div>
                      <p className="text-[10px] font-bold uppercase text-muted-foreground">
                        Importe bruto
                      </p>
                      <p className="font-semibold">
                        {formatCurrency(cotizarResult.totales.sub_total)}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase text-muted-foreground">
                        Renta CIP
                      </p>
                      <p className="font-semibold text-destructive">
                        - {formatCurrency(cotizarResult.totales.renta_cip)}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase text-muted-foreground">
                        Aporte Codemu
                      </p>
                      <p className="font-semibold text-destructive">
                        - {formatCurrency(cotizarResult.totales.aporte_codemu)}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase text-muted-foreground">
                        Neto honorario
                      </p>
                      <p className="font-black text-primary">
                        {formatCurrency(cotizarResult.totales.neto_honorario)}
                      </p>
                    </div>
                  </div>
                </div>
              {/* Header info */}
              <div className="rounded-xl border border-border/50 bg-card p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-semibold">
                    Delegado:
                  </span>
                  <span className="font-bold">
                    {cotizarResult.delegado.nombre_completo}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-semibold">
                    CIP:
                  </span>
                  <span className="font-bold">
                    {cotizarResult.delegado.cip}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-semibold">
                    Periodo:
                  </span>
                  <span className="font-bold">
                    {cotizarResult.periodo != null && cotizarResult.mes != null
                      ? `${cotizarResult.periodo}-${String(cotizarResult.mes).padStart(2, "0")}`
                      : "—"}
                  </span>
                </div>
              </div>

              {/* Tabla de Liquidación — replica de la hoja física */}
              <div className="rounded-xl border border-border overflow-hidden">
                <div className="bg-yellow-100 px-4 py-2 border-b border-border text-center">
                  <span className="text-sm font-bold uppercase tracking-wide">
                    Liquidación de Honorarios a Delegados
                  </span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs border-collapse">
                    <thead>
                      <tr className="bg-muted/50">
                        <th className="border border-border px-1 py-1.5 text-left font-bold uppercase tracking-wide text-[10px]">
                          Liq
                        </th>
                        <th className="border border-border px-1 py-1.5 text-left font-bold uppercase tracking-wide text-[10px]">
                          N° Liq.
                        </th>
                        <th className="border border-border px-1 py-1.5 text-left font-bold uppercase tracking-wide text-[10px]">
                          F. Rev.
                        </th>
                        <th className="border border-border px-1 py-1.5 text-left font-bold uppercase tracking-wide text-[10px]">
                          Expediente
                        </th>
                        <th className="border border-border px-1 py-1.5 text-center font-bold uppercase tracking-wide text-[10px]">
                          Nro Rev
                        </th>
                        <th className="border border-border px-1 py-1.5 text-left font-bold uppercase tracking-wide text-[10px]">
                          Nro. Comp.
                        </th>
                        <th className="border border-border px-1 py-1.5 text-right font-bold uppercase tracking-wide text-[10px]">
                          Total
                        </th>
                        <th className="border border-border px-1 py-1.5 text-right font-bold uppercase tracking-wide text-[10px]">
                          Sub Total
                        </th>
                        <th className="border border-border px-1 py-1.5 text-right font-bold uppercase tracking-wide text-[10px]">
                          Imp. Bruto
                        </th>
                        <th className="border border-border px-1 py-1.5 text-right font-bold uppercase tracking-wide text-[10px]">
                          Renta CIP
                        </th>
                        <th className="border border-border px-1 py-1.5 text-right font-bold uppercase tracking-wide text-[10px]">
                          Aporte Codemu
                        </th>
                        <th className="border border-border px-1 py-1.5 text-right font-bold uppercase tracking-wide text-[10px]">
                          Fondo Común
                        </th>
                        <th className="border border-border px-1 py-1.5 text-right font-bold uppercase tracking-wide text-[10px]">
                          Neto Honorario
                        </th>
                        <th className="border border-border px-1 py-1.5 text-center font-bold uppercase tracking-wide text-[10px]">
                          Nro Ord
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {cotizarResult.items.map((item, index) => (
                        <tr
                          key={item.liquidacion_delegado_id ?? index}
                          className="hover:bg-muted/30"
                        >
                          <td className="border border-border px-1 py-1.5 text-center">
                            {index + 1}
                          </td>
                          <td className="border border-border px-1 py-1.5 text-center">
                            {item.liquidacion_especifica_numero ?? "—"}
                          </td>
                          <td className="border border-border px-1 py-1.5">
                            {item.fecha_revision ?? "—"}
                          </td>
                          <td className="border border-border px-1 py-1.5 font-mono font-medium">
                            {item.exp_liqui ?? "—"}
                          </td>
                          <td className="border border-border px-1 py-1.5 text-center">
                            {item.numero_revision ?? "—"}
                          </td>
                          <td className="border border-border px-1 py-1.5 font-mono text-center">
                            {item.comprobante_activo
                              ? `${item.comprobante_activo.serie ?? ""}-${item.comprobante_activo.numero ?? ""}`
                              : "—"}
                          </td>
                          <td className="border border-border px-1 py-1.5 text-right">
                            {item.total_liquidacion != null
                              ? `S/ ${item.total_liquidacion.toFixed(2)}`
                              : "—"}
                          </td>
                          <td className="border border-border px-1 py-1.5 text-right">
                            {item.sub_total_liquidacion != null
                              ? `S/ ${item.sub_total_liquidacion.toFixed(2)}`
                              : "—"}
                          </td>
                          <td className="border border-border px-1 py-1.5 text-right">
                            {item.imp_bruto != null
                              ? `S/ ${item.imp_bruto.toFixed(2)}`
                              : "—"}
                          </td>
                          <td className="border border-border px-1 py-1.5 text-right text-destructive">
                            {item.renta_cip != null
                              ? `- S/ ${item.renta_cip.toFixed(2)}`
                              : "—"}
                          </td>
                          <td className="border border-border px-1 py-1.5 text-right text-destructive">
                            {item.aporte_codemu != null
                              ? `- S/ ${item.aporte_codemu.toFixed(2)}`
                              : "—"}
                          </td>
                          <td className="border border-border px-1 py-1.5 text-right text-destructive">
                            {item.fondo_comun != null
                              ? `- S/ ${item.fondo_comun.toFixed(2)}`
                              : "—"}
                          </td>
                          <td className="border border-border px-1 py-1.5 text-right font-bold">
                            {item.neto_honorario != null
                              ? `S/ ${item.neto_honorario.toFixed(2)}`
                              : "—"}
                          </td>
                          <td className="border border-border px-1 py-1.5 text-center">
                            {item.numero_rh ?? "—"}
                          </td>
                        </tr>
                      ))}
                      {/* Fila de Totales */}
                      <tr className="bg-muted/70 font-bold">
                        <td
                          colSpan={TOTALES_LABEL_COL_SPAN}
                          className="border border-border px-1 py-1.5 text-center uppercase tracking-wide"
                        >
                          Totales
                        </td>
                        <td className="border border-border px-1 py-1.5 text-right">
                          {cotizarResult.items
                            .reduce(
                              (sum, i) => sum + (i.total_liquidacion ?? 0),
                              0,
                            )
                            .toFixed(2)}
                        </td>
                        <td className="border border-border px-1 py-1.5 text-right">
                          {cotizarResult.items
                            .reduce(
                              (sum, i) => sum + (i.sub_total_liquidacion ?? 0),
                              0,
                            )
                            .toFixed(2)}
                        </td>
                        <td className="border border-border px-1 py-1.5 text-right">
                          {cotizarResult.totales.sub_total.toFixed(2)}
                        </td>
                        <td className="border border-border px-1 py-1.5 text-right text-destructive">
                          -{cotizarResult.totales.renta_cip.toFixed(2)}
                        </td>
                        <td className="border border-border px-1 py-1.5 text-right text-destructive">
                          -{cotizarResult.totales.aporte_codemu.toFixed(2)}
                        </td>
                        <td className="border border-border px-1 py-1.5 text-right text-destructive">
                          -{cotizarResult.totales.fondo_comun.toFixed(2)}
                        </td>
                        <td className="border border-border px-1 py-1.5 text-right font-black text-primary">
                          {cotizarResult.totales.neto_honorario.toFixed(2)}
                        </td>
                        <td className="border border-border px-1 py-1.5" />
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </GenericModal.Body>

        <GenericModal.Footer className="px-6 py-4 bg-muted/30 border-t border-border">
          <div className="flex items-center justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={
                step === 1
                  ? handleClose
                  : () =>
                      setStep((s) => (s === 3 ? 2 : 1) as Step)
              }
              disabled={isPending}
              className="h-10 rounded-xl font-semibold"
            >
              {step === 1 ? "Cancelar" : "Atrás"}
            </Button>

            {step === 1 && (
              <Button
                type="button"
                onClick={handleBuscar}
                className="h-10 rounded-xl font-bold gap-1.5"
              >
                <Search className="h-4 w-4" />
                Buscar Candidatas
              </Button>
            )}

            {step === 2 && (
              <Button
                type="button"
                onClick={handleCotizar}
                disabled={cotizarMutation.isPending || selectedCount === 0}
                className="h-10 rounded-xl font-bold gap-1.5"
              >
                {cotizarMutation.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
                Cotizar ({selectedCount})
              </Button>
            )}

            {step === 3 && (
              <>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleExportExcel}
                  disabled={!cotizarResult || crearMutation.isPending}
                  className="h-10 rounded-xl font-semibold gap-1.5"
                >
                  <FileSpreadsheet className="h-4 w-4" />
                  Exportar Excel
                </Button>
                <Button
                  type="button"
                  onClick={handleCrear}
                  disabled={crearMutation.isPending}
                  className="h-10 rounded-xl font-bold gap-1.5"
                >
                  {crearMutation.isPending && (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  )}
                  <Receipt className="h-4 w-4" />
                  Crear RH
                </Button>
              </>
            )}
          </div>
        </GenericModal.Footer>

        <RHCandidatasFiltroModal
          open={filterModalOpen}
          onOpenChange={setFilterModalOpen}
          initialFiltros={filtros}
          onApply={(newFiltros) => {
            setFiltros(newFiltros);
            setPage(1);
            setFilterModalOpen(false);
          }}
        />

        <GenericModal.CloseX />

        {/* ── Ver detalle modal (Module 6) ── */}
        {detalleRow && (
          <LiquidacionDetalleModal
            open={detalleRowId !== null}
            onOpenChange={(open) => {
              if (!open) setDetalleRowId(null);
            }}
            kindBadge={
              getLiquidacionTipoInfo(detalleRow.tipo_liquidacion?.codigo).label
            }
            publicId={
              detalleData
                ? formatPublicId(
                    detalleRow.tipo_liquidacion?.codigo ?? "",
                    detalleData.liquidacion_general.fecha_registro,
                    detalleData.liquidacion_especifica.numero,
                  )
                : (detalleRow.expediente ?? "—")
            }
            estado={detalleData?.liquidacion_general.estado}
            kindIcon={
              getLiquidacionTipoInfo(detalleRow.tipo_liquidacion?.codigo).icon
            }
          >
            {isLoadingDetalle ? (
              <div className="flex items-center justify-center p-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : detalleData ? (
              (() => {
                const codigo = detalleRow.tipo_liquidacion?.codigo;
                if (
                  codigo === "EDIFICACION" ||
                  codigo === "TALUDES" ||
                  codigo === "IMPACTO_VIAL"
                ) {
                  return composeDetalleSections({
                    lg: detalleData.liquidacion_general,
                    lt: detalleData.liquidacion_tipo as Parameters<
                      typeof composeDetalleSections
                    >[0]["lt"],
                  });
                }
                if (
                  codigo === "HABILITACION_URBANA" ||
                  codigo === "MECANICA_SUELOS"
                ) {
                  return composeDetalleSections({
                    lg: detalleData.liquidacion_general,
                    m2: detalleData.liquidacion_tipo as Parameters<
                      typeof composeDetalleSections
                    >[0]["m2"],
                  });
                }
                // INSPECCION_OBRA or unknown
                return composeDetalleSections({
                  lg: detalleData.liquidacion_general,
                  visitas: detalleData.liquidacion_tipo as Parameters<
                    typeof composeDetalleSections
                  >[0]["visitas"],
                });
              })()
            ) : (
              <div className="p-4 text-sm text-muted-foreground">
                No se pudo cargar el detalle
              </div>
            )}
          </LiquidacionDetalleModal>
        )}
      </GenericModal.Content>
    </GenericModal>
  );
}
