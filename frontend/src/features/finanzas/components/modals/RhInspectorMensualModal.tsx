"use client";

/**
 * RhInspectorMensualModal — Modal de 4 pasos para RH Mensual de Inspector.
 *
 * - Paso 1: Ingresar CIP + Periodo
 * - Paso 2: Listado de candidatas con selección por checkbox + cantidad_visitas
 * - Paso 3: Previsualización de totales
 * - Paso 4: Confirmar → crear
 *
 * Endpoints:
 *   GET  /finanzas/recibos-inspectores/candidatos?cip={cip}&periodo={periodo}
 *   POST /finanzas/recibos-inspectores/cotizar
 *   POST /finanzas/recibos-inspectores/crear
 */
import {
  AlertTriangle,
  CheckCircle2,
  Eye,
  FileSpreadsheet,
  Filter,
  ListChecks,
  Loader2,
  type LucideIcon,
  Receipt,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as XLSX from "xlsx";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { notify } from "@/errors";
import { InspectorOperacionSmartField } from "@/features/finanzas/components/fields/InspectorOperacionSmartField";
import {
  isValidRhCip,
  RhCipField,
} from "@/features/finanzas/components/fields/RhCipField";
import { RhDatePickerField } from "@/features/finanzas/components/fields/RhDatePickerField";
import {
  countActiveFiltros,
  RHActiveFiltersPanel,
  RHCandidatasFiltroModal,
} from "@/features/finanzas/components/filtros";
import type { RHCandidatasFiltroValues } from "@/features/finanzas/components/filtros/RHCandidatasFiltroModal";
import {
  RhMensualModalShell,
  type RhModalStep,
} from "@/features/finanzas/components/modals/RhMensualModalShell";
import { RhInspectorVariablesCalculo } from "@/features/finanzas/components/RhInspectorVariablesCalculo";
import { useCandidatasInspector } from "@/features/finanzas/hooks/useCandidatasInspector";
import {
  useActualizarRHInspector,
  useCotizarEdicionRHInspector,
  useCotizarRHInspector,
  useCrearRHInspector,
} from "@/features/finanzas/hooks/useRHInspectorMensual";
import type { ReciboHonorarioInspectorMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";
import type {
  InspectorCandidataItem,
  InspectorOperacion,
  RHInspectorActualizarIn,
  RHInspectorCotizar,
  RHInspectorCotizarIn,
} from "@/features/finanzas/schemas/rh-inspector-mensual.schema";
import {
  buildInspectorFlowKey,
  type InspectorSelectionEntry,
  useRHSelectionStore,
} from "@/features/finanzas/stores/rh-selection.store";
import {
  buildInspectorEditSelection,
  collectInspectorUnresolvedDetails,
} from "@/features/finanzas/utils/rh-mensual-edicion";
import {
  etiquetaConPorcentaje,
  formatPorcentaje,
} from "@/features/finanzas/utils/rh-porcentaje";
import {
  composeDetalleSections,
  getTipoDetalleSection,
  LiquidacionDetalleModal,
} from "@/features/liquidaciones/components/detail";
import { useLiquidacionGeneralDetalle } from "@/features/liquidaciones/hooks/useLiquidacionGeneralDetalle";
import type { PorcentajeObraDatosOut } from "@/features/liquidaciones/schemas/liquidacion-porcentaje.schema";
import { formatPublicId } from "@/features/liquidaciones/utils/formatPublicId";
import { getLiquidacionTipoInfo } from "@/features/liquidaciones/utils/liquidacionTipoInfo";

interface RhInspectorMensualModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  /**
   * Contexto de edición: cuando viene informado, el modal reabre el wizard
   * existente en modo edición (selección pre-cargada con los detalles
   * persistidos del RH) y confirma con PATCH en lugar de POST /crear.
   */
  editContext?: RhInspectorMensualEditContext | null;
}

/**
 * Contexto de edición del RH mensual de inspector.
 *
 * `rh` es el item del listado (GET /finanzas/recibos-inspectores): de él salen
 * el CIP, el periodo y los detalles persistidos con su `detalle_id`, su
 * expediente y la cantidad de inspecciones liquidadas.
 */
export interface RhInspectorMensualEditContext {
  rh: ReciboHonorarioInspectorMensual;
}

type Step = 1 | 2 | 3;

const getCurrentPeriodParts = () => {
  const today = new Date();
  const year = String(today.getFullYear());
  const month = String(today.getMonth() + 1).padStart(2, "0");
  return { year, month, rhPeriod: `${year}-${month}` };
};

const isValidPeriodo = (value: string) => /^\d{4}$/.test(value);
const isValidMes = (value: string) => {
  const month = Number(value);
  return /^\d{1,2}$/.test(value) && month >= 1 && month <= 12;
};

export const isFutureInspectorPeriod = (
  year: number,
  month: number,
  now = new Date(),
) =>
  year > now.getFullYear() ||
  (year === now.getFullYear() && month > now.getMonth() + 1);

const formatCurrency = (value?: number | null) =>
  value == null ? "—" : `S/ ${value.toFixed(2)}`;

const safeFilePart = (value: string) => value.replace(/[^a-zA-Z0-9-]/g, "-");

/**
 * Número de columnas previas al valor en la tabla de previsualización de Inspector.
 * La tabla tiene 16 columnas; el rótulo de cada total (Sub Total, Descuento, Honorarios)
 * abarca las primeras 13, y cada valor se alinea con su columna
 * (Sub Total, Descuento y Honorarios son las 3 últimas).
 */
const TOTAL_LABEL_COL_SPAN = 13;

/**
 * Guía visual por paso del wizard. Define el ícono, etiqueta corta y
 * descripción larga que se muestran en el header y en el indicador de pasos.
 * Los íconos se colorean con `primary` cuando el paso está activo o completado,
 * y con `secondary` cuando está pendiente.
 */
type StepGuideEntry = {
  icon: LucideIcon;
  label: string;
  description: string;
};

const STEP_GUIDE: Record<1 | 2 | 3, StepGuideEntry> = {
  1: {
    icon: Search,
    label: "Buscar",
    description:
      "Ingresa el CIP del inspector y, opcionalmente, periodo y rango de fechas para localizar liquidaciones candidatas.",
  },
  2: {
    icon: ListChecks,
    label: "Seleccionar",
    description:
      "Selecciona las liquidaciones que incluirás y define la cantidad de visitas a liquidar por cada una.",
  },
  3: {
    icon: CheckCircle2,
    label: "Confirmar",
    description:
      "Verifica el resumen final, exporta a Excel si lo necesitas, y genera el RH mensual.",
  },
};

/**
 * Pasos del wizard — se handed al shell común (`RhMensualModalShell`), que
 * dibuja el indicador. La descripción de cada paso sigue en `STEP_GUIDE`
 * (se muestra bajo el título del modal).
 */
const RH_MODAL_STEPS: RhModalStep[] = ([1, 2, 3] as const).map((s) => ({
  icon: STEP_GUIDE[s].icon,
  label: STEP_GUIDE[s].label,
}));

const RH_EDIT_MODAL_STEPS: RhModalStep[] = [
  { icon: ListChecks, label: "Seleccionar" },
  { icon: CheckCircle2, label: "Cotizar" },
];

/** Per-candidate selection: cantidad_visitas and period chosen by the user */
export interface InspectorCandidateSelection {
  cantidad_visitas: number;
  periodo: string;
  mes: string;
}

type BuildItemsResult = {
  headerPeriodo: string;
  items: RHInspectorCotizarIn["items"];
};

export function RhInspectorMensualModal({
  open,
  onOpenChange,
  onSuccess,
  editContext = null,
}: RhInspectorMensualModalProps) {
  /** Modo edición: el wizard se reabre con la selección persistida del RH. */
  const isEdit = Boolean(editContext);
  const editRh = editContext?.rh ?? null;

  const currentPeriod = getCurrentPeriodParts();
  const [step, setStep] = useState<Step>(1);
  const [cip, setCip] = useState("");
  const [vigente, setVigente] = useState<boolean | undefined>(true);
  const [selectedOperacion, setSelectedOperacion] =
    useState<InspectorOperacion | null>(null);
  const [periodo, setPeriodo] = useState(currentPeriod.rhPeriod);
  const [fechaInicio, setFechaInicio] = useState("");
  const [fechaFin, setFechaFin] = useState("");
  const [cotizarResult, setCotizarResult] = useState<RHInspectorCotizar | null>(
    null,
  );
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filtros, setFiltros] = useState<RHCandidatasFiltroValues>({});
  const [filterModalOpen, setFilterModalOpen] = useState(false);

  /**
   * Error bloqueante del wizard — se muestra en el ÁREA DE ERROR del shell
   * común (no en un toast) para que el mensaje quede visible junto a los
   * pasos que bloquean el guardado.
   */
  const [wizardError, setWizardError] = useState<string | null>(null);

  /**
   * Id del RH ya precargado en el store. La hidratación ocurre UNA sola vez
   * por objetivo de edición: si el listado se refresca y llega un objeto
   * nuevo del mismo RH, NO se vuelve a sembrar el store (eso borraría lo que
   * el usuario ya editó).
   */
  const hydratedRhIdRef = useRef<string | null>(null);

  // ── Ver detalle state (Module 6) ─────────────────────────────────────
  const [detalleLiquidacionGeneralId, setDetalleLiquidacionGeneralId] =
    useState<string | null>(null);
  const { data: detalleData, isLoading: isLoadingDetalle } =
    useLiquidacionGeneralDetalle({
      id: detalleLiquidacionGeneralId,
    });

  /** Tipo código of the liquidación previewed in the "Ver detalle" modal —
   *  drives which tipo-specific detail section is rendered. */
  const detalleTipoCodigo =
    detalleData?.liquidacion_general.tipo_liquidacion?.codigo ?? null;

  // ── Selection store (Module 1) — replaces local selectedRows state ──────────
  const {
    addSelection,
    removeSelection,
    clearSelections,
    isSelected,
    getSelectedItems,
    getSelectedCount,
  } = useRHSelectionStore();

  /** Stable flow key for this inspector session */
  const flowKey = isEdit
    ? `inspector-edicion-${editRh?.id ?? ""}`
    : buildInspectorFlowKey(cip);

  const cotizarMutation = useCotizarRHInspector();
  const cotizarEdicionMutation = useCotizarEdicionRHInspector(editRh?.id ?? "");
  const crearMutation = useCrearRHInspector();
  const actualizarMutation = useActualizarRHInspector(editRh?.id ?? "");

  const {
    data: candidatosData,
    isLoading: isLoadingCandidatos,
    isError: isErrorCandidatos,
    refetch: refetchCandidatos,
  } = useCandidatasInspector({
    cip,
    periodo,
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

  const candidatos: InspectorCandidataItem[] = candidatosData?.candidatos ?? [];

  // ── Derived from candidatos (after declaration to avoid TDZ) ─────────────────
  const detalleRow = detalleLiquidacionGeneralId
    ? (candidatos.find(
        (c) => c.liquidacion_general_id === detalleLiquidacionGeneralId,
      ) ?? null)
    : null;

  const inspectorInfo = candidatosData
    ? {
        id: candidatosData.inspector_id,
        nombre: candidatosData.inspector_nombre,
        cip: candidatosData.inspector_cip,
        dni: candidatosData.inspector_dni,
      }
    : null;

  const resetForm = useCallback(() => {
    setStep(1);
    setCip("");
    setVigente(true);
    setSelectedOperacion(null);
    setPeriodo(getCurrentPeriodParts().rhPeriod);
    setFechaInicio("");
    setFechaFin("");
    setCotizarResult(null);
    clearSelections(flowKey);
    setPage(1);
    setPageSize(20);
    setFiltros({});
    setWizardError(null);
    hydratedRhIdRef.current = null;
  }, [flowKey, clearSelections]);

  const handleClose = useCallback(() => {
    resetForm();
    onOpenChange(false);
  }, [onOpenChange, resetForm]);

  // ── Modo edición: el wizard arranca con la identidad del RH ────────────────
  useEffect(() => {
    if (!editRh) return;
    setCip(editRh.inspector?.cip ?? "");
    setPeriodo(
      editRh.periodo != null && editRh.mes != null
        ? `${editRh.periodo}-${String(editRh.mes).padStart(2, "0")}`
        : getCurrentPeriodParts().rhPeriod,
    );
    setCotizarResult(null);
    setPage(1);
    setPageSize(100);
    setWizardError(null);
    setStep(2);
  }, [editRh]);

  /**
   * Precarga la selección del modo edición con los detalles persistidos.
   *
   * Se siembra UNA sola vez por RH (guardado en `hydratedRhIdRef`): volver a
   * sembrar el store borraría lo que el usuario ya editó (cantidades,
   * periodo/mes) sin avisar.
   */
  useEffect(() => {
    if (!isEdit || !editRh) return;
    if (hydratedRhIdRef.current === editRh.id) return;

    clearSelections(flowKey);
    for (const entry of buildInspectorEditSelection(editRh)) {
      addSelection(
        flowKey,
        entry.candidate.liquidacion_categoria_visitas_id,
        entry,
      );
    }
    hydratedRhIdRef.current = editRh.id;
  }, [isEdit, editRh, flowKey, clearSelections, addSelection]);

  /**
   * En edición, enlaza las filas persistidas con su candidata real cuando la
   * consulta termina. Así la UI no muestra la misma liquidación dos veces y la
   * fila recupera su número específico, especialidad e identificadores.
   */
  useEffect(() => {
    if (!isEdit || candidatos.length === 0) return;

    const selectedEntries = getSelectedItems(
      flowKey,
    ) as InspectorSelectionEntry[];
    for (const entry of selectedEntries) {
      if (!entry.cotizarItem.detalle_id) continue;
      if (
        !entry.candidate.liquidacion_categoria_visitas_id.startsWith("detalle:")
      )
        continue;

      const numero = entry.candidate.liquidacion_especifica_numero;
      const match = candidatos.find(
        (candidate) =>
          (numero != null &&
            candidate.liquidacion_especifica_numero === numero) ||
          candidate.expediente === entry.candidate.expediente,
      );
      if (!match) continue;

      removeSelection(
        flowKey,
        entry.candidate.liquidacion_categoria_visitas_id,
      );
      addSelection(flowKey, match.liquidacion_categoria_visitas_id, {
        ...entry,
        candidate: match,
      });
    }
  }, [
    isEdit,
    candidatos,
    flowKey,
    getSelectedItems,
    removeSelection,
    addSelection,
  ]);

  const isCandidateSelected = useCallback(
    (candidate: InspectorCandidataItem) => {
      if (isSelected(flowKey, candidate.liquidacion_categoria_visitas_id))
        return true;

      return (getSelectedItems(flowKey) as InspectorSelectionEntry[]).some(
        (entry) =>
          Boolean(entry.cotizarItem.detalle_id) &&
          ((entry.candidate.liquidacion_especifica_numero != null &&
            entry.candidate.liquidacion_especifica_numero ===
              candidate.liquidacion_especifica_numero) ||
            entry.candidate.expediente === candidate.expediente),
      );
    },
    [flowKey, isSelected, getSelectedItems],
  );

  /** Periodo de cabecera del RH (YYYY-MM) parseado desde el estado del wizard. */
  const headerPeriodo = useMemo(() => {
    const match = /^(\d{4})-(\d{2})$/.exec(periodo.trim());
    if (!match) return null;
    return { periodo: Number(match[1]), mes: Number(match[2]) };
  }, [periodo]);

  /**
   * Cambio del periodo de cabecera: se propaga a las filas que todavía
   * tenían el periodo anterior. Editar es el mismo flujo que crear, así que
   * el periodo del RH se puede corregir; las filas con periodo propio ya
   * editado se respetan.
   */
  const handlePeriodoChange = useCallback(
    (value: string) => {
      const anterior = headerPeriodo;
      const siguiente = /^(\d{4})-(\d{2})$/.exec(value.trim());
      setPeriodo(value);
      if (!anterior || !siguiente) return;

      const nuevoPeriodo = Number(siguiente[1]);
      const nuevoMes = Number(siguiente[2]);
      const entries = getSelectedItems(flowKey) as InspectorSelectionEntry[];
      for (const entry of entries) {
        if (
          entry.cotizarItem.periodo !== anterior.periodo ||
          entry.cotizarItem.mes !== anterior.mes
        )
          continue;
        addSelection(
          flowKey,
          entry.candidate.liquidacion_categoria_visitas_id,
          {
            ...entry,
            cotizarItem: {
              ...entry.cotizarItem,
              periodo: nuevoPeriodo,
              mes: nuevoMes,
            },
          },
        );
      }
    },
    [headerPeriodo, flowKey, getSelectedItems, addSelection],
  );

  /**
   * Detalles persistidos que no se pueden conservar (sin `detalle_id`): el
   * PATCH los retiraría del recibo, así que se muestran y bloquean el
   * guardado en vez de descartarse en silencio.
   */
  const unresolvedDetails = useMemo(
    () => (isEdit && editRh ? collectInspectorUnresolvedDetails(editRh) : []),
    [isEdit, editRh],
  );

  /**
   * Botón de retroceso del footer. En modo edición el wizard arranca en el
   * paso de selección, así que el primer retroceso cierra el modal.
   */
  const handleBack = useCallback(() => {
    if (step === 1) return handleClose();
    if (isEdit && step === 2) return handleClose();
    setStep((s) => (s === 3 ? 2 : 1) as Step);
  }, [step, isEdit, handleClose]);

  // ── Paso 1 → 2: buscar candidatas ────────────────────────────────────
  const handleBuscar = useCallback(async () => {
    if (!isValidRhCip(cip)) {
      notify.error("El CIP del inspector debe tener exactamente 6 dígitos");
      return;
    }
    if (!selectedOperacion) {
      notify.error("Selecciona una operatividad del inspector");
      return;
    }
    // Periodo es opcional para buscar candidatas (puede ingresarse luego)
    if (periodo.trim() && !/^\d{4}-\d{2}$/.test(periodo.trim())) {
      notify.error("El periodo debe tener formato YYYY-MM");
      return;
    }
    if (periodo.trim()) {
      const periodoYear = Number(periodo.substring(0, 4));
      const periodoMonth = Number(periodo.substring(5, 7));
      if (isFutureInspectorPeriod(periodoYear, periodoMonth)) {
        notify.error("El periodo no puede ser posterior al mes actual");
        return;
      }
    }
    // Validar rango de fechas si ambas están presentes
    if (fechaInicio && fechaFin && fechaInicio > fechaFin) {
      notify.error("La fecha de inicio no puede ser mayor que la fecha fin");
      return;
    }
    setCotizarResult(null);
    setPage(1);
    try {
      await refetchCandidatos();
      setStep(2);
    } catch {
      notify.error("No se pudieron buscar las candidatas");
    }
  }, [
    cip,
    selectedOperacion,
    periodo,
    fechaInicio,
    fechaFin,
    refetchCandidatos,
  ]);

  // ── Toggle row selection (store-backed) ─────────────────────────────────
  const toggleRow = useCallback(
    (c: InspectorCandidataItem, checked: boolean) => {
      const id = c.liquidacion_categoria_visitas_id;
      if (checked) {
        const rowPeriod = getCurrentPeriodParts();
        const entry: InspectorSelectionEntry = {
          cotizarItem: {
            cantidad_visitas: Math.min(1, c.saldo_disponible),
            periodo: Number(rowPeriod.year),
            mes: Number(rowPeriod.month),
          },
          candidate: c,
        };
        addSelection(flowKey, id, entry);
      } else {
        removeSelection(flowKey, id);
      }
    },
    [flowKey, addSelection, removeSelection],
  );

  /** Get the full selection entry for a given candidate id */
  const getSelectionEntry = useCallback(
    (id: string): InspectorSelectionEntry | undefined => {
      const items = getSelectedItems(flowKey) as InspectorSelectionEntry[];
      return items.find(
        (e) => e.candidate.liquidacion_categoria_visitas_id === id,
      );
    },
    [flowKey, getSelectedItems],
  );

  /** Update cantidad_visitas on an existing store entry */
  const updateCantidadVisitas = useCallback(
    (id: string, value: number) => {
      const entry = getSelectionEntry(id);
      if (!entry) return;
      const updated: InspectorSelectionEntry = {
        ...entry,
        cotizarItem: { ...entry.cotizarItem, cantidad_visitas: value },
      };
      addSelection(flowKey, id, updated);
    },
    [flowKey, getSelectionEntry, addSelection],
  );

  /** Update periodo on an existing store entry */
  const updatePeriodo = useCallback(
    (id: string, value: string) => {
      const entry = getSelectionEntry(id);
      if (!entry) return;
      const updated: InspectorSelectionEntry = {
        ...entry,
        cotizarItem: { ...entry.cotizarItem, periodo: Number(value) },
      };
      addSelection(flowKey, id, updated);
    },
    [flowKey, getSelectionEntry, addSelection],
  );

  /** Update mes on an existing store entry */
  const updateMes = useCallback(
    (id: string, value: string) => {
      const entry = getSelectionEntry(id);
      if (!entry) return;
      const updated: InspectorSelectionEntry = {
        ...entry,
        cotizarItem: { ...entry.cotizarItem, mes: Number(value) },
      };
      addSelection(flowKey, id, updated);
    },
    [flowKey, getSelectionEntry, addSelection],
  );

  const buildActualizarPayload =
    useCallback((): RHInspectorActualizarIn | null => {
      if (!headerPeriodo) {
        setWizardError(
          "El periodo del RH debe tener formato YYYY-MM para poder editar.",
        );
        return null;
      }
      if (isFutureInspectorPeriod(headerPeriodo.periodo, headerPeriodo.mes)) {
        setWizardError("El periodo no puede ser posterior al mes actual");
        return null;
      }
      if (unresolvedDetails.length > 0) {
        setWizardError(
          "Hay detalles del RH que no se pudieron identificar. Recarga la página e inténtalo de nuevo.",
        );
        return null;
      }

      const selectedEntries = getSelectedItems(
        flowKey,
      ) as InspectorSelectionEntry[];
      if (selectedEntries.length === 0) {
        notify.error("Selecciona al menos una candidata");
        return null;
      }

      for (const entry of selectedEntries) {
        const { cantidad_visitas } = entry.cotizarItem;
        if (cantidad_visitas <= 0) {
          notify.error(
            `Cantidad visitas debe ser mayor a 0 para expediente ${entry.candidate.expediente}`,
          );
          return null;
        }
        if (cantidad_visitas > entry.candidate.saldo_disponible) {
          notify.error(
            `Cantidad visitas excede saldo disponible (${entry.candidate.saldo_disponible}) para expediente ${entry.candidate.expediente}`,
          );
          return null;
        }
      }

      return {
        cip: editRh?.inspector?.cip ?? cip,
        periodo: headerPeriodo.periodo,
        mes: headerPeriodo.mes,
        items: selectedEntries.map((entry) => {
          const { cantidad_visitas, periodo, mes, detalle_id } =
            entry.cotizarItem;
          if (detalle_id) {
            return {
              exp_liqui: entry.candidate.expediente,
              cantidad_visitas,
              periodo,
              mes,
              detalle_id,
            };
          }
          return {
            liquidacion_categoria_visitas_id:
              entry.candidate.liquidacion_categoria_visitas_id,
            cantidad_visitas,
            periodo,
            mes,
          };
        }),
      };
    }, [
      editRh,
      headerPeriodo,
      unresolvedDetails.length,
      getSelectedItems,
      flowKey,
      cip,
    ]);

  const buildItems = useCallback((): BuildItemsResult | null => {
    const selectedEntries = getSelectedItems(
      flowKey,
    ) as InspectorSelectionEntry[];
    if (selectedEntries.length === 0) {
      notify.error("Selecciona al menos una candidata");
      return null;
    }

    const firstEntry = selectedEntries[0];
    const headerPeriodo = /^\d{4}-\d{2}$/.test(periodo.trim())
      ? periodo.trim()
      : `${firstEntry.cotizarItem.periodo}-${String(firstEntry.cotizarItem.mes).padStart(2, "0")}`;
    if (!/^\d{4}-\d{2}$/.test(headerPeriodo)) {
      notify.error("El periodo de cabecera debe tener formato YYYY-MM");
      return null;
    }
    setPeriodo(headerPeriodo);

    for (const entry of selectedEntries) {
      const c = entry.candidate;
      const {
        cantidad_visitas,
        periodo: itemPeriodo,
        mes: itemMes,
      } = entry.cotizarItem;
      if (cantidad_visitas <= 0) {
        notify.error(
          `Cantidad visitas debe ser mayor a 0 para expediente ${c.expediente}`,
        );
        return null;
      }
      if (cantidad_visitas > c.saldo_disponible) {
        notify.error(
          `Cantidad visitas excede saldo disponible (${c.saldo_disponible}) para expediente ${c.expediente}`,
        );
        return null;
      }
      if (!isValidPeriodo(String(itemPeriodo))) {
        notify.error(
          `Periodo debe tener formato YYYY para expediente ${c.expediente}`,
        );
        return null;
      }
      if (!isValidMes(String(itemMes))) {
        notify.error(
          `Mes debe estar entre 1 y 12 para expediente ${c.expediente}`,
        );
        return null;
      }
      if (isFutureInspectorPeriod(Number(itemPeriodo), Number(itemMes))) {
        notify.error(
          `El periodo no puede ser futuro para expediente ${c.expediente}`,
        );
        return null;
      }
    }

    const items: RHInspectorCotizarIn["items"] = selectedEntries.map(
      (entry) => {
        const {
          cantidad_visitas,
          periodo: itemPeriodo,
          mes: itemMes,
        } = entry.cotizarItem;
        return {
          liquidacion_categoria_visitas_id:
            entry.candidate.liquidacion_categoria_visitas_id,
          cantidad_visitas,
          periodo: itemPeriodo,
          mes: itemMes,
        };
      },
    );

    return { headerPeriodo, items };
  }, [flowKey, getSelectedItems, periodo]);

  // ── Paso 2 → 3: cotizar ──────────────────────────────────────────────
  const handleCotizar = useCallback(async () => {
    setWizardError(null);

    if (isEdit) {
      const payload = buildActualizarPayload();
      if (!payload) return;
      try {
        const cotizacion = await cotizarEdicionMutation.cotizar(payload);
        setCotizarResult(cotizacion.data);
        setStep(3);
      } catch {
        // Error handled by mutation
      }
      return;
    }

    const result = buildItems();
    if (!result) return;

    try {
      const cotizacion = await cotizarMutation.cotizar({
        cip,
        periodo: parseInt(result.headerPeriodo.substring(0, 4), 10),
        mes: parseInt(result.headerPeriodo.substring(5, 7), 10),
        items: result.items,
      });
      setCotizarResult(cotizacion.data);
      setStep(3);
    } catch {
      // Error handled by mutation
    }
  }, [
    isEdit,
    buildActualizarPayload,
    cotizarEdicionMutation,
    buildItems,
    cip,
    cotizarMutation,
  ]);

  // ── Paso 3: confirmar + crear (todo en este paso) ────────────────────────
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
        Inspector: cotizarResult.inspector.nombre_completo,
        CIP: cotizarResult.inspector.cip,
        DNI: cotizarResult.inspector.dni ?? "—",
        Periodo: headerPeriodoStr,
        Expediente: item.exp_liqui,
        Administrado: item.nombre_propietario,
        "Inspecciones programadas": item.inspecciones_programadas,
        "Pagadas hasta mes anterior":
          item.inspecciones_pagadas_hasta_mes_anterior,
        "Inspecciones liquidadas": item.inspecciones_liquidadas,
        "Periodo item": item.periodo ?? "",
        "Mes item": item.mes ?? "",
        "Saldo restante": item.saldo_restante,
        "Importe bruto": item.importe_bruto,
        "Costo por inspeccion": item.costo_por_inspeccion,
        "Monto contribuido": item.monto_contribuido,
      }));

    rows.push({
      Item: "",
      Inspector: "TOTALES",
      CIP: cotizarResult.inspector.cip,
      DNI: cotizarResult.inspector.dni ?? "—",
      Periodo: headerPeriodoStr,
      Expediente: "",
      Administrado: "",
      "Inspecciones programadas": cotizarResult.items.reduce(
        (sum, item) => sum + item.inspecciones_programadas,
        0,
      ),
      "Pagadas hasta mes anterior": cotizarResult.items.reduce(
        (sum, item) => sum + item.inspecciones_pagadas_hasta_mes_anterior,
        0,
      ),
      "Inspecciones liquidadas": cotizarResult.items.reduce(
        (sum, item) => sum + item.inspecciones_liquidadas,
        0,
      ),
      "Periodo item": "",
      "Mes item": "",
      "Saldo restante": cotizarResult.items.reduce(
        (sum, item) => sum + item.saldo_restante,
        0,
      ),
      "Importe bruto": cotizarResult.items.reduce(
        (sum, item) => sum + item.importe_bruto,
        0,
      ),
      "Costo por inspeccion": "",
      "Monto contribuido": cotizarResult.totales.sub_total,
    });

    const workbook = XLSX.utils.book_new();
    const worksheet = XLSX.utils.json_to_sheet(rows);
    XLSX.utils.book_append_sheet(workbook, worksheet, "Resumen RH");
    XLSX.writeFile(
      workbook,
      `rh-inspector-${safeFilePart(cotizarResult.inspector.cip)}-${safeFilePart(headerPeriodoStr)}.xlsx`,
    );
  }, [cotizarResult]);

  // ── Paso 4: crear ───────────────────────────────────────────────────
  const handleCrear = useCallback(async () => {
    if (!cotizarResult) return;

    const result = buildItems();
    if (!result) return;

    try {
      await crearMutation.crear({
        cip,
        periodo: parseInt(result.headerPeriodo.substring(0, 4), 10),
        mes: parseInt(result.headerPeriodo.substring(5, 7), 10),
        items: result.items,
      });
      // The success toast comes from the mutation hook (server message).
      handleClose();
      onSuccess?.();
    } catch {
      // Error handled by mutation
    }
  }, [cotizarResult, buildItems, cip, crearMutation, handleClose, onSuccess]);

  // ── Modo edición: sincroniza el conjunto final con PATCH ─────────────────
  const handleActualizar = useCallback(async () => {
    setWizardError(null);
    const payload = buildActualizarPayload();
    if (!payload) return;

    try {
      await actualizarMutation.actualizar(payload);
      // The success toast comes from the mutation hook (server message).
      handleClose();
      onSuccess?.();
    } catch {
      // Error handled by mutation
    }
  }, [buildActualizarPayload, actualizarMutation, handleClose, onSuccess]);

  const isPending =
    cotizarMutation.isPending ||
    cotizarEdicionMutation.isPending ||
    crearMutation.isPending ||
    actualizarMutation.isPending;
  const selectedCount = getSelectedCount(flowKey);

  /** Título del wizard — cambia entre creación y edición. */
  const modalTitle = isEdit
    ? "RH Mensual — Editar Selección"
    : "RH Mensual — Inspectores";

  return (
    <RhMensualModalShell
      open={open}
      onClose={handleClose}
      eyebrow="Recibos de Honorario - Inspectores"
      title={modalTitle}
      description={
        isEdit && step === 3
          ? "Revisa la cotización actualizada antes de guardar los cambios."
          : STEP_GUIDE[step].description
      }
      steps={isEdit ? RH_EDIT_MODAL_STEPS : RH_MODAL_STEPS}
      currentStep={isEdit ? step - 1 : step}
      isPending={isPending}
      error={wizardError}
      backLabel={step === 1 || (isEdit && step === 2) ? "Cancelar" : "Atrás"}
      onBack={handleBack}
      actions={
        <>
          {step === 1 && (
            <Button
              type="button"
              onClick={handleBuscar}
              disabled={!isValidRhCip(cip)}
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
              disabled={
                cotizarMutation.isPending ||
                cotizarEdicionMutation.isPending ||
                selectedCount === 0
              }
              className="h-10 rounded-xl font-bold gap-1.5"
            >
              {(cotizarMutation.isPending ||
                cotizarEdicionMutation.isPending) && (
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
              {isEdit ? (
                <Button
                  type="button"
                  onClick={handleActualizar}
                  disabled={actualizarMutation.isPending}
                  className="h-10 rounded-xl font-bold gap-1.5"
                >
                  {actualizarMutation.isPending && (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  )}
                  <Receipt className="h-4 w-4" />
                  Guardar cambios
                </Button>
              ) : (
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
              )}
            </>
          )}
        </>
      }
      extraContent={
        <>
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

          {/* ── Ver detalle modal (Module 6) ── */}
          {detalleRow && (
            <LiquidacionDetalleModal
              open={detalleLiquidacionGeneralId !== null}
              onOpenChange={(open) => {
                if (!open) setDetalleLiquidacionGeneralId(null);
              }}
              kindBadge={
                getLiquidacionTipoInfo(
                  detalleData?.liquidacion_general.tipo_liquidacion?.codigo,
                ).label
              }
              publicId={
                detalleData
                  ? formatPublicId(
                      detalleData.liquidacion_general.tipo_liquidacion
                        ?.codigo ?? "",
                      detalleData.liquidacion_general.fecha_registro,
                      detalleData.liquidacion_especifica.numero,
                    )
                  : (detalleRow.expediente ?? "—")
              }
              estado={detalleData?.liquidacion_general.estado}
              kindIcon={
                getLiquidacionTipoInfo(
                  detalleData?.liquidacion_general.tipo_liquidacion?.codigo,
                ).icon
              }
            >
              {isLoadingDetalle ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : detalleData ? (
                composeDetalleSections({
                  lg: detalleData.liquidacion_general,
                  lt:
                    detalleTipoCodigo === "EDIFICACION" ||
                    detalleTipoCodigo === "TALUDES" ||
                    detalleTipoCodigo === "IMPACTO_VIAL"
                      ? (detalleData.liquidacion_tipo as PorcentajeObraDatosOut)
                      : null,
                  tipoSection: getTipoDetalleSection(
                    detalleTipoCodigo,
                    detalleData.liquidacion_tipo,
                    detalleData.liquidacion_general.uit?.valor,
                  ),
                  showDelegados: detalleTipoCodigo !== "INSPECCION_OBRA",
                })
              ) : (
                <div className="p-4 text-sm text-muted-foreground">
                  No se pudo cargar el detalle
                </div>
              )}
            </LiquidacionDetalleModal>
          )}
        </>
      }
    >
      {/* ── Detalles persistidos que no se pudieron identificar ── */}
      {isEdit && unresolvedDetails.length > 0 && (
        <div className="rounded-xl border border-warning/40 bg-warning/10 px-4 py-3 space-y-2">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-warning" />
            <span className="text-xs font-bold uppercase tracking-wider text-warning">
              {unresolvedDetails.length} detalle(s) sin identificar
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            Estas filas del RH no se pudieron identificar. No se descartan en
            silencio: el guardado queda bloqueado mientras exista alguna sin
            identificar.
          </p>
          <ul className="space-y-1">
            {unresolvedDetails.map((detalle, index) => (
              <li
                key={detalle.detalle_id ?? `unresolved-${index}`}
                className="text-xs text-foreground"
              >
                <span className="font-mono font-bold">
                  {detalle.expediente ?? "Sin expediente"}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Paso 1: Buscar — CIP del inspector + rango de fechas opcional ── */}
      {step === 1 && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_220px]">
            <RhCipField
              id="cip-inspector"
              label="CIP del Inspector"
              value={cip}
              onChange={(value) => {
                setCip(value);
                setSelectedOperacion(null);
              }}
              onEnter={() => void handleBuscar()}
            />
            <div className="space-y-2">
              <Label htmlFor="vigencia-inspector">
                Vigencia de la operatividad
              </Label>
              <Select
                value={vigente === undefined ? "todas" : String(vigente)}
                onValueChange={(value) => {
                  setVigente(value === "todas" ? undefined : value === "true");
                  setSelectedOperacion(null);
                }}
              >
                <SelectTrigger
                  id="vigencia-inspector"
                  className="h-10 rounded-xl font-semibold"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="true">Vigentes</SelectItem>
                  <SelectItem value="false">
                    Históricas / no vigentes
                  </SelectItem>
                  <SelectItem value="todas">Todas</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <InspectorOperacionSmartField
            cip={cip}
            vigente={vigente}
            selectedId={selectedOperacion?.inspector_operacion_id}
            onSelect={setSelectedOperacion}
          />
          <div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-2">
            <RhDatePickerField
              label="Fecha Inicio"
              value={fechaInicio}
              onChange={setFechaInicio}
              id="fecha-inicio"
            />
            <RhDatePickerField
              label="Fecha Fin"
              value={fechaFin}
              onChange={setFechaFin}
              id="fecha-fin"
            />
          </div>
        </div>
      )}

      {/* ── Paso 2: Seleccionar — listado de candidatas con cantidad_visitas inline por fila ── */}
      {step === 2 && (
        <div className="space-y-4">
          {/* Inspector info bar */}
          {inspectorInfo && (
            <div className="rounded-xl border border-border/50 bg-card p-4 space-y-1">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground font-semibold">
                  Inspector:
                </span>
                <span className="font-bold">{inspectorInfo.nombre}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground font-semibold">
                  CIP:
                </span>
                <span className="font-bold">{inspectorInfo.cip}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground font-semibold">
                  DNI:
                </span>
                <span className="font-bold">{inspectorInfo.dni}</span>
              </div>
              <div className="flex justify-between items-center text-sm gap-2">
                <span className="text-muted-foreground font-semibold shrink-0">
                  Periodo:
                </span>
                <Input
                  id="periodo-step2"
                  type="month"
                  value={periodo}
                  max={currentPeriod.rhPeriod}
                  onChange={(e) => handlePeriodoChange(e.target.value)}
                  placeholder="YYYY-MM"
                  className="h-7 w-28 text-xs rounded border border-input bg-background font-semibold text-right"
                />
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground font-semibold">
                  Disponibles:
                </span>
                <span className="font-bold">
                  {candidatos.filter((c) => !isCandidateSelected(c)).length}
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
                <div className="flex-1 min-w-0">Expediente</div>
                <div className="w-14 shrink-0 text-center">N° Liq.</div>
                <div className="flex-1 min-w-0">Especialidad</div>
                <div className="w-16 shrink-0 text-right">Prog.</div>
                <div className="w-16 shrink-0 text-right">Pagadas</div>
                <div className="w-16 shrink-0 text-right">Saldo</div>
                <div className="w-20 shrink-0 text-right">Costo/Und.</div>
                <div className="w-20 shrink-0">Periodo</div>
                <div className="w-16 shrink-0">Mes</div>
                <div className="w-20 shrink-0">Cant. Visitas</div>
                <div className="w-8 shrink-0" />
              </div>
              <div className="border border-t-0 border-primary/20 rounded-b-lg overflow-hidden">
                {(getSelectedItems(flowKey) as InspectorSelectionEntry[]).map(
                  (entry) => {
                    const { cotizarItem, candidate } = entry;
                    /**
                     * Inspecciones liquidadas de la fila.
                     *
                     * - Fila nueva: pagadas + visitas de esta selección.
                     * - Fila ya persistida (`detalle_id`): el valor del
                     *   propio RH. Sumar las pagadas del candidato lo
                     *   contaminaría con pagos ajenos a este recibo.
                     */
                    const inspeccionesLiquidadas = cotizarItem.detalle_id
                      ? cotizarItem.cantidad_visitas
                      : candidate.inspecciones_pagadas +
                        cotizarItem.cantidad_visitas;
                    const saldoRestante =
                      candidate.saldo_disponible - cotizarItem.cantidad_visitas;
                    return (
                      <div
                        key={candidate.liquidacion_categoria_visitas_id}
                        className="flex items-center gap-3 px-3 py-2 border-b border-border/50 last:border-b-0 bg-primary/[0.02] hover:bg-primary/[0.04] transition-all duration-150"
                      >
                        {/* Remove button */}
                        <button
                          type="button"
                          onClick={() =>
                            removeSelection(
                              flowKey,
                              candidate.liquidacion_categoria_visitas_id,
                            )
                          }
                          className="w-6 shrink-0 h-6 flex items-center justify-center rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                          aria-label="Quitar de seleccionados"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>

                        {/* Expediente (read-only) */}
                        <div className="flex-1 min-w-0">
                          <p className="font-mono font-bold text-xs text-foreground truncate">
                            {candidate.expediente ?? "—"}
                          </p>
                        </div>

                        <div className="w-14 shrink-0 text-center text-xs font-semibold">
                          {candidate.liquidacion_especifica_numero ?? "—"}
                        </div>

                        {/* Especialidad (read-only) */}
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-foreground truncate">
                            {candidate.especialidad_nombre}
                          </p>
                        </div>

                        {/* Inspecciones programadas (read-only) */}
                        <div className="w-16 shrink-0 text-right">
                          <p className="text-xs font-semibold text-foreground">
                            {candidate.cantidad_visitas}
                          </p>
                        </div>

                        {/* Inspecciones liquidadas (read-only) */}
                        <div className="w-16 shrink-0 text-right">
                          <p
                            className="text-xs text-muted-foreground"
                            data-testid={`selected-liquidated-${candidate.liquidacion_categoria_visitas_id}`}
                          >
                            {inspeccionesLiquidadas}
                          </p>
                        </div>

                        {/* Saldo restante después de la selección (read-only) */}
                        <div className="w-16 shrink-0 text-right">
                          <p
                            className={`text-xs font-semibold ${
                              saldoRestante === 0
                                ? "text-muted-foreground"
                                : "text-foreground"
                            }`}
                            data-testid={`selected-balance-${candidate.liquidacion_categoria_visitas_id}`}
                          >
                            {saldoRestante}
                          </p>
                        </div>

                        {/* Costo por inspección (read-only) */}
                        <div className="w-20 shrink-0 text-right">
                          <p className="text-xs font-black text-primary">
                            {candidate.costo_por_inspeccion != null
                              ? `S/ ${candidate.costo_por_inspeccion.toFixed(2)}`
                              : "—"}
                          </p>
                        </div>

                        {/* Periodo (editable) */}
                        <Input
                          id={`sel-periodo-${candidate.liquidacion_categoria_visitas_id}`}
                          type="number"
                          min={1900}
                          max={Number(currentPeriod.year)}
                          value={cotizarItem.periodo ?? ""}
                          onChange={(e) =>
                            updatePeriodo(
                              candidate.liquidacion_categoria_visitas_id,
                              e.target.value,
                            )
                          }
                          placeholder="YYYY"
                          className="w-20 shrink-0 h-7 text-xs rounded border border-input bg-background"
                        />

                        {/* Mes (editable) */}
                        <Input
                          id={`sel-mes-${candidate.liquidacion_categoria_visitas_id}`}
                          type="number"
                          min={1}
                          max={
                            (cotizarItem.periodo ??
                              Number(currentPeriod.year)) >=
                            Number(currentPeriod.year)
                              ? Number(currentPeriod.month)
                              : 12
                          }
                          value={cotizarItem.mes ?? ""}
                          onChange={(e) =>
                            updateMes(
                              candidate.liquidacion_categoria_visitas_id,
                              e.target.value,
                            )
                          }
                          placeholder="1-12"
                          className="w-16 shrink-0 h-7 text-xs rounded border border-input bg-background"
                        />

                        {/* Cantidad visitas (editable) */}
                        <Input
                          id={`sel-cant-${candidate.liquidacion_categoria_visitas_id}`}
                          type="number"
                          min={1}
                          max={candidate.saldo_disponible}
                          value={cotizarItem.cantidad_visitas || ""}
                          onChange={(e) =>
                            updateCantidadVisitas(
                              candidate.liquidacion_categoria_visitas_id,
                              Number(e.target.value),
                            )
                          }
                          placeholder="0"
                          className="w-20 shrink-0 h-7 text-xs rounded border border-input bg-background"
                        />

                        {/* Ver detalle button */}
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setDetalleLiquidacionGeneralId(
                              candidate.liquidacion_general_id,
                            );
                          }}
                          className="w-8 shrink-0 h-7 flex items-center justify-center rounded border border-transparent hover:border-primary/30 hover:bg-primary/5 text-muted-foreground hover:text-primary transition-colors"
                          aria-label="Ver detalle"
                          title="Ver detalle"
                        >
                          <Eye className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    );
                  },
                )}
              </div>
            </div>
          )}

          {/* Row-based grid (compact, horizontal, spreadsheet-like) — available candidates only */}
          {isLoadingCandidatos ? (
            <div className="flex items-center justify-center p-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : isErrorCandidatos ? (
            <div className="flex flex-col items-center justify-center p-8 text-destructive text-sm">
              Error al cargar las candidatas
            </div>
          ) : (
            <div className="rounded-xl border border-border bg-card overflow-hidden">
              {/* Header row — always visible above rows */}
              <div className="flex items-center gap-3 px-3 py-2 bg-muted/40 border-b border-border text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                <div className="w-6 shrink-0" />
                <div className="flex-1 min-w-0">Expediente</div>
                <div className="w-14 shrink-0 text-center">N° Liq.</div>
                <div className="flex-1 min-w-0">Especialidad</div>
                <div className="w-16 shrink-0 text-right">Prog.</div>
                <div className="w-16 shrink-0 text-right">Pagadas</div>
                <div className="w-16 shrink-0 text-right">Saldo</div>
                <div className="w-20 shrink-0 text-right">Costo/Und.</div>
                <div className="w-8 shrink-0" />
              </div>
              <ScrollArea>
                {candidatos
                  .filter((c) => !isCandidateSelected(c))
                  .map((c) => {
                    const id = c.liquidacion_categoria_visitas_id;
                    return (
                      <div
                        key={id}
                        className="flex items-center gap-3 px-3 py-2 border-b border-border/50 last:border-b-0 hover:bg-muted/30 transition-all duration-150"
                      >
                        {/* Checkbox to select */}
                        <Checkbox
                          id={`row-${id}`}
                          checked={false}
                          onCheckedChange={(v) => toggleRow(c, !!v)}
                          className="shrink-0"
                        />

                        {/* Expediente (read-only) */}
                        <div className="flex-1 min-w-0">
                          <p className="font-mono font-bold text-xs text-foreground truncate">
                            {c.expediente ?? "—"}
                          </p>
                        </div>

                        <div className="w-14 shrink-0 text-center text-xs font-semibold">
                          {c.liquidacion_especifica_numero ?? "—"}
                        </div>

                        {/* Especialidad (read-only) */}
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-foreground truncate">
                            {c.especialidad_nombre}
                          </p>
                        </div>

                        {/* Inspecciones programadas (read-only) */}
                        <div className="w-16 shrink-0 text-right">
                          <p className="text-xs font-semibold text-foreground">
                            {c.cantidad_visitas}
                          </p>
                        </div>

                        {/* Inspecciones pagadas (read-only) */}
                        <div className="w-16 shrink-0 text-right">
                          <p className="text-xs text-muted-foreground">
                            {c.inspecciones_pagadas}
                          </p>
                        </div>

                        {/* Saldo disponible (read-only) */}
                        <div className="w-16 shrink-0 text-right">
                          <p
                            className={`text-xs font-semibold ${
                              c.saldo_disponible === 0
                                ? "text-muted-foreground"
                                : "text-foreground"
                            }`}
                          >
                            {c.saldo_disponible}
                          </p>
                        </div>

                        {/* Costo por inspección (read-only) */}
                        <div className="w-20 shrink-0 text-right">
                          <p className="text-xs font-black text-primary">
                            {c.costo_por_inspeccion != null
                              ? `S/ ${c.costo_por_inspeccion.toFixed(2)}`
                              : "—"}
                          </p>
                        </div>

                        {/* Ver detalle button */}
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setDetalleLiquidacionGeneralId(
                              c.liquidacion_general_id,
                            );
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
                {candidatos.filter((c) => !isCandidateSelected(c)).length ===
                  0 && (
                  <div className="py-12 text-center text-muted-foreground text-sm border-t border-border">
                    {candidatos.length === 0
                      ? "No hay liquidaciones candidatas para este inspector"
                      : "Todas las candidatas han sido seleccionadas"}
                  </div>
                )}
              </ScrollArea>
              {candidatosData && (
                <div className="border-t border-border bg-background/95 px-3">
                  <Pagination
                    currentPage={candidatosData.page ?? 1}
                    totalPages={candidatosData.totalPages ?? 1}
                    onPageChange={(p) => setPage(p)}
                    onPageSizeChange={(size) => {
                      setPageSize(size);
                      setPage(1);
                    }}
                    totalItems={candidatosData.total ?? 0}
                    pageSize={candidatosData.pageSize ?? 20}
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
                  Inspector
                </p>
                <p className="font-semibold truncate">
                  {cotizarResult.inspector.nombre_completo}
                </p>
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase text-muted-foreground">
                  CIP
                </p>
                <p className="font-semibold">{cotizarResult.inspector.cip}</p>
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase text-muted-foreground">
                  Periodo
                </p>
                <p className="font-semibold">
                  {cotizarResult.periodo != null && cotizarResult.mes != null
                    ? `${cotizarResult.periodo}-${String(cotizarResult.mes).padStart(2, "0")}`
                    : "—"}
                </p>
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase text-muted-foreground">
                  Items
                </p>
                <p className="font-semibold">{cotizarResult.items.length}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm border-t border-primary/20 pt-3">
              <div>
                <p className="text-[10px] font-bold uppercase text-muted-foreground">
                  Sub total
                </p>
                <p className="font-semibold">
                  {formatCurrency(cotizarResult.totales.sub_total)}
                </p>
              </div>
              {(() => {
                const pct = formatPorcentaje(
                  cotizarResult.totales.tasa_descuento_aplicada,
                );
                return (
                  <div>
                    <p className="text-[10px] font-bold uppercase text-muted-foreground">
                      Descuento{pct != null ? ` (${pct})` : ""}
                    </p>
                    <p className="font-semibold text-destructive">
                      - {formatCurrency(cotizarResult.totales.descuento)}
                    </p>
                  </div>
                );
              })()}
              <div>
                <p className="text-[10px] font-bold uppercase text-muted-foreground">
                  Tasa descuento
                </p>
                <p className="font-semibold">
                  {formatPorcentaje(
                    cotizarResult.totales.tasa_descuento_aplicada,
                    2,
                  ) ?? "—"}
                </p>
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase text-muted-foreground">
                  Honorarios
                </p>
                <p className="font-black text-primary">
                  {formatCurrency(cotizarResult.totales.honorarios)}
                </p>
              </div>
            </div>
            {/* Escala de descuento aplicada */}
            <RhInspectorVariablesCalculo
              escala_nombre={cotizarResult.variables_calculo.escala_nombre}
              porcentaje_descuento={
                cotizarResult.variables_calculo.rango_aplicado
                  .porcentaje_descuento
              }
              monto_minimo={
                cotizarResult.variables_calculo.rango_aplicado.monto_minimo ??
                undefined
              }
              monto_maximo={
                cotizarResult.variables_calculo.rango_aplicado.monto_maximo ??
                undefined
              }
            />
          </div>
          {/* Header info */}
          <div className="rounded-xl border border-border/50 bg-card p-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground font-semibold">
                Inspector:
              </span>
              <span className="font-bold">
                {cotizarResult.inspector.nombre_completo}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground font-semibold">CIP:</span>
              <span className="font-bold">{cotizarResult.inspector.cip}</span>
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

          {/* Tabla de items con pie de totales —对齐 like delegado */}
          <div className="rounded-xl border border-border overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-muted/50">
                <tr>
                  <th className="text-left px-3 py-2 font-semibold text-muted-foreground">
                    Expediente
                  </th>
                  <th className="text-center px-3 py-2 font-semibold text-muted-foreground">
                    N° Liq.
                  </th>
                  <th className="text-left px-3 py-2 font-semibold text-muted-foreground">
                    Comprobante
                  </th>
                  <th className="text-left px-3 py-2 font-semibold text-muted-foreground">
                    Administrado
                  </th>
                  <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                    Prog.
                  </th>
                  <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                    Pag. Mes Ant.
                  </th>
                  <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                    Liq.
                  </th>
                  <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                    Periodo
                  </th>
                  <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                    Mes
                  </th>
                  <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                    Saldo
                  </th>
                  <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                    Importe Ref.
                  </th>
                  <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                    Costo/Unidad
                  </th>
                  <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                    Monto Contrib.
                  </th>
                  <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                    Sub Total
                  </th>
                  <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                    {etiquetaConPorcentaje(
                      "Descuento",
                      cotizarResult.totales.tasa_descuento_aplicada,
                    )}
                  </th>
                  <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                    Honorarios
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {cotizarResult.items.map((item) => (
                  <tr key={item.exp_liqui} className="hover:bg-muted/30">
                    <td className="px-3 py-2 font-mono font-semibold">
                      {item.exp_liqui}
                    </td>
                    <td className="px-3 py-2 text-center">
                      {item.liquidacion_especifica_numero ?? "—"}
                    </td>
                    <td className="px-3 py-2">
                      {item.comprobante_activo ? (
                        <div className="text-xs">
                          <div className="font-medium">
                            {item.comprobante_activo.serie &&
                            item.comprobante_activo.numero
                              ? `${item.comprobante_activo.serie}-${item.comprobante_activo.numero}`
                              : "—"}
                          </div>
                          {(item.comprobante_activo.tipo_comprobante ||
                            item.comprobante_activo.fecha_emision) && (
                            <div className="text-muted-foreground text-[10px]">
                              {[
                                item.comprobante_activo.tipo_comprobante,
                                item.comprobante_activo.fecha_emision,
                              ]
                                .filter(Boolean)
                                .join(" · ") || "—"}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="text-muted-foreground text-xs">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-muted-foreground max-w-[160px] truncate">
                      {item.nombre_propietario || "—"}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {item.inspecciones_programadas}
                    </td>
                    <td className="px-3 py-2 text-right text-muted-foreground">
                      {item.inspecciones_pagadas_hasta_mes_anterior}
                    </td>
                    <td className="px-3 py-2 text-right font-semibold">
                      {item.inspecciones_liquidadas}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {item.periodo ?? "—"}
                    </td>
                    <td className="px-3 py-2 text-right">{item.mes ?? "—"}</td>
                    <td className="px-3 py-2 text-right">
                      {item.saldo_restante}
                    </td>
                    <td className="px-3 py-2 text-right">
                      S/ {item.importe_bruto.toFixed(2)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      S/ {item.costo_por_inspeccion.toFixed(2)}
                    </td>
                    <td className="px-3 py-2 text-right font-semibold">
                      S/ {item.monto_contribuido.toFixed(2)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      S/ {item.sub_total.toFixed(2)}
                    </td>
                    <td className="px-3 py-2 text-right text-destructive">
                      - S/ {item.descuento.toFixed(2)}
                    </td>
                    <td className="px-3 py-2 text-right font-semibold text-primary">
                      S/ {item.honorarios.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
              {/* Footer con totales — alineado con las columnas de la tabla */}
              <tfoot className="bg-muted/30 border-t-2 border-border">
                <tr>
                  <td
                    colSpan={TOTAL_LABEL_COL_SPAN}
                    className="px-3 py-2 text-right font-semibold text-muted-foreground"
                  >
                    Sub Total:
                  </td>
                  <td className="px-3 py-2 text-right font-bold">
                    S/ {cotizarResult.totales.sub_total.toFixed(2)}
                  </td>
                  <td />
                  <td />
                </tr>
                <tr>
                  <td
                    colSpan={TOTAL_LABEL_COL_SPAN}
                    className="px-3 py-1.5 text-right text-muted-foreground"
                  >
                    Descuento (
                    {formatPorcentaje(
                      cotizarResult.totales.tasa_descuento_aplicada,
                      2,
                    ) ?? "—"}
                    ):
                  </td>
                  <td />
                  <td className="px-3 py-1.5 text-right font-bold text-destructive">
                    - S/ {cotizarResult.totales.descuento.toFixed(2)}
                  </td>
                  <td />
                </tr>
                <tr className="border-t border-border">
                  <td
                    colSpan={TOTAL_LABEL_COL_SPAN}
                    className="px-3 py-2 text-right font-bold text-foreground"
                  >
                    Honorarios:
                  </td>
                  <td />
                  <td />
                  <td className="px-3 py-2 text-right font-black text-primary text-sm">
                    S/ {cotizarResult.totales.honorarios.toFixed(2)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}
    </RhMensualModalShell>
  );
}
