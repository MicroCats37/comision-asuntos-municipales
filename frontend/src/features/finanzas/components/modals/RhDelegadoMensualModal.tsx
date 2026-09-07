"use client";

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
import { FileSpreadsheet, Loader2, Receipt, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import * as XLSX from "xlsx";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { GenericModal } from "@/components/genericModal/GenericModal";
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
import { useCandidatasDelegado } from "@/features/finanzas/hooks/useCandidatasDelegado";
import {
  useCotizarRHDelegado,
  useCrearRHDelegado,
} from "@/features/finanzas/hooks/useRHDelegadoMensual";
import type {
  CandidataDelegado,
  RHDelegadoCotizar,
  RHDelegadoCotizarIn,
} from "@/features/finanzas/schemas/rh-delegado-mensual.schema";
import { DelegadoOperacionSmartField } from "@/features/finanzas/components/fields/DelegadoOperacionSmartField";
import type { DelegadoOperacionSelection } from "@/features/finanzas/components/fields/DelegadoOperacionSmartField";

interface RhDelegadoMensualModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

type Step = 1 | 2 | 3 | 4;

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
          className="w-full h-7 px-2 justify-start text-left font-normal text-xs rounded border border-input bg-background disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <span className="text-muted-foreground mr-1">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="10"
              height="10"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="inline-block"
            >
              <rect width="18" height="18" x="3" y="4" rx="2" ry="2" />
              <line x1="16" x2="16" y1="2" y2="6" />
              <line x1="8" x2="8" y1="2" y2="6" />
              <line x1="3" x2="21" y1="10" y2="10" />
            </svg>
          </span>
          {value ? (
            format(new Date(value), "dd/MM/yyyy")
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

export function RhDelegadoMensualModal({
  open,
  onOpenChange,
  onSuccess,
}: RhDelegadoMensualModalProps) {
  const [step, setStep] = useState<Step>(1);
  const [cip, setCip] = useState("");
  const [selectedOperacion, setSelectedOperacion] = useState<
    DelegadoOperacionSelection | null
  >(null);
  const [fechaInicio, setFechaInicio] = useState("");
  const [fechaFin, setFechaFin] = useState("");
  const [cotizarResult, setCotizarResult] = useState<RHDelegadoCotizar | null>(
    null,
  );

  /**
   * Map of CandidataDelegado.id → per-item fields.
   * Only entries for checked cards are present.
   */
  const [selectedCardFields, setSelectedCardFields] = useState<
    Record<string, CandidataCardFields>
  >({});

  /** Delegado operatividad selected for this RH mensual (required for cotizar/crear). */
  const [delegadoOperacionId, setDelegadoOperacionId] = useState("");

  const cotizarMutation = useCotizarRHDelegado();
  const crearMutation = useCrearRHDelegado();

  const {
    data: candidatasData,
    isLoading: isLoadingCandidatas,
    isError: isErrorCandidatas,
    refetch: refetchCandidatas,
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
    enabled: false,
  });

  const candidatas: CandidataDelegado[] = candidatasData?.candidatas ?? [];
  const delegado = candidatasData?.delegado;

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
    setSelectedCardFields({});
    setDelegadoOperacionId("");
  }, []);

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
      notify.error("Selecciona una operatividad del delegado");
      return;
    }
    if (
      fechaInicio && fechaFin && fechaInicio > fechaFin
    ) {
      notify.error("La fecha de inicio no puede ser mayor que la fecha fin");
      return;
    }
    setSelectedCardFields({});
    setCotizarResult(null);
    try {
      await refetchCandidatas();
      setStep(2);
    } catch {
      notify.error("No se pudieron buscar las candidatas");
    }
  }, [selectedOperacion, fechaInicio, fechaFin, cip, refetchCandidatas]);
  const isSelected = useCallback(
    (id: string) => id in selectedCardFields,
    [selectedCardFields],
  );

  const toggleCard = useCallback(
    (c: CandidataDelegado, checked: boolean) => {
      setSelectedCardFields((prev) => {
        if (checked) {
          const current = getCurrentPeriodParts();
          return {
            ...prev,
            [c.id]: {
              numero_rh: "",
              periodo: current.periodo,
              mes: current.mes,
              dictamen_revision: "",
              fecha_presentacion: "",
              fecha_revision: "",
            },
          };
        } else {
          const next = { ...prev };
          delete next[c.id];
          return next;
        }
      });
    },
    [],
  );

  const updateCardField = useCallback(
    (id: string, field: keyof CandidataCardFields, value: string) => {
      setSelectedCardFields((prev) => {
        return { ...prev, [id]: { ...prev[id], [field]: value } };
      });
    },
    [],
  );

  // ── Paso 2 → 3: cotizar ────────────────────────────────────────────
  const handleCotizar = useCallback(async () => {
    const selectedIds = Object.keys(selectedCardFields);
    if (selectedIds.length === 0) {
      notify.error("Selecciona al menos una candidata");
      return;
    }

    const invalidPeriodo = selectedIds.some(
      (id) => !isValidPeriodo(selectedCardFields[id]?.periodo ?? ""),
    );
    if (invalidPeriodo) {
      notify.error("Ingresa un periodo válido (YYYY) para cada candidata seleccionada");
      return;
    }

    const invalidMes = selectedIds.some(
      (id) => !isValidMes(selectedCardFields[id]?.mes ?? ""),
    );
    if (invalidMes) {
      notify.error("Ingresa un mes válido (1-12) para cada candidata seleccionada");
      return;
    }

    const firstFields = selectedCardFields[selectedIds[0]];
    const rhPeriodo = buildRhPeriodo(firstFields.periodo, firstFields.mes);

    const items: RHDelegadoCotizarIn["items"] = candidatas
      .filter((c) => selectedIds.includes(c.id))
      .map((c) => {
        const fields = selectedCardFields[c.id];
        return {
          liquidacion_general_id: c.id,
          especialidad_revision_id: c.especialidad_candidata.id,
          numero_rh: fields.numero_rh || undefined,
          periodo: Number(fields.periodo),
          mes: Number(fields.mes),
          dictamen_revision: fields.dictamen_revision || undefined,
          fecha_presentacion: fields.fecha_presentacion || undefined,
          fecha_revision: fields.fecha_revision || undefined,
        };
      });

    try {
      const result = await cotizarMutation.cotizar({
        cip,
        periodo: Number(firstFields.periodo),
        mes: Number(firstFields.mes),
        delegado_operacion_id: delegadoOperacionId,
        items,
      });
      setCotizarResult(result.data);
      setStep(3);
    } catch {
      // Error handled by mutation
    }
  }, [selectedCardFields, candidatas, cip, cotizarMutation, delegadoOperacionId]);

  // ── Paso 3 → 4: confirmar ───────────────────────────────────────────
  const handleConfirmar = useCallback(() => {
    setStep(4);
  }, []);

  const handleExportExcel = useCallback(() => {
    if (!cotizarResult) return;

    const headerPeriodoStr =
      cotizarResult.periodo != null && cotizarResult.mes != null
        ? `${cotizarResult.periodo}-${String(cotizarResult.mes).padStart(2, "0")}`
        : "—";

    const rows: Array<Record<string, string | number>> = cotizarResult.items.map((item, index) => ({
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

    const selectedIds = Object.keys(selectedCardFields);
    const invalidPeriodo = selectedIds.some(
      (id) => !isValidPeriodo(selectedCardFields[id]?.periodo ?? ""),
    );
    if (invalidPeriodo) {
      notify.error("Ingresa un periodo válido (YYYY) para cada candidata seleccionada");
      return;
    }

    const invalidMes = selectedIds.some(
      (id) => !isValidMes(selectedCardFields[id]?.mes ?? ""),
    );
    if (invalidMes) {
      notify.error("Ingresa un mes válido (1-12) para cada candidata seleccionada");
      return;
    }

    const firstFields = selectedCardFields[selectedIds[0]];
    const rhPeriodo = buildRhPeriodo(firstFields.periodo, firstFields.mes);

    const items: RHDelegadoCotizarIn["items"] = candidatas
      .filter((c) => selectedIds.includes(c.id))
      .map((c) => {
        const fields = selectedCardFields[c.id];
        return {
          liquidacion_general_id: c.id,
          especialidad_revision_id: c.especialidad_candidata.id,
          numero_rh: fields.numero_rh || undefined,
          periodo: Number(fields.periodo),
          mes: Number(fields.mes),
          dictamen_revision: fields.dictamen_revision || undefined,
          fecha_presentacion: fields.fecha_presentacion || undefined,
          fecha_revision: fields.fecha_revision || undefined,
        };
      });

    try {
      await crearMutation.crear({
        cip,
        periodo: Number(firstFields.periodo),
        mes: Number(firstFields.mes),
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
    selectedCardFields,
    candidatas,
    cip,
    crearMutation,
    handleClose,
    onSuccess,
    delegadoOperacionId,
  ]);

  const isPending = cotizarMutation.isPending || crearMutation.isPending;
  const selectedCount = Object.keys(selectedCardFields).length;

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
                {step === 1 &&
                  "Ingresa el CIP del delegado para buscar candidatas"}
                {step === 2 &&
                  "Selecciona las liquidaciones candidatas e ingresa los datos por item"}
                {step === 3 && "Revisa la previsualización antes de confirmar"}
                {step === 4 && "Confirma los datos y genera el RH mensual"}
              </p>
            </div>
            <div className="w-9 shrink-0" aria-hidden="true" />
          </div>
        </GenericModal.Header>

        <GenericModal.Body className="space-y-6">
          {/* Step indicator */}
          <div className="flex items-center gap-2">
            {[1, 2, 3, 4].map((s) => (
              <div key={s} className="flex items-center gap-2">
                <div
                  className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold border-2 ${
                    step === s
                      ? "bg-primary text-primary-foreground border-primary"
                      : step > s
                        ? "bg-primary/20 text-primary border-primary/40"
                        : "bg-muted text-muted-foreground border-muted"
                  }`}
                >
                  {s}
                </div>
                {s < 4 && (
                  <div
                    className={`h-0.5 w-8 rounded ${
                      step > s ? "bg-primary/40" : "bg-muted"
                    }`}
                  />
                )}
              </div>
            ))}
          </div>

          {/* ── Paso 1: CIP ── */}
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
              {/* SmartField: operatividades delgadas por CIP */}
              <DelegadoOperacionSmartField
                cip={cip}
                onSelect={(selection) => setSelectedOperacion(selection)}
                selectedId={selectedOperacion?.id}
              />
              <div className="grid grid-cols-2 gap-3">
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

          {/* ── Paso 2: Cards ── */}
          {step === 2 && (
            <div className="space-y-4">
              {/* Delegado info bar */}
              {delegado && (
                <div className="rounded-xl border border-border/60 bg-muted/10 p-4 space-y-1">
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
                      Candidatas encontradas:
                    </span>
                    <span className="font-bold">{candidatas.length}</span>
                  </div>
                  <div className="flex justify-end text-sm border-t border-border/40 pt-2 mt-1">
                    <span className="font-bold text-primary">
                      {selectedCount} de {candidatas.length} seleccionada(s)
                    </span>
                  </div>
                </div>
              )}

              {/* Row-based grid (compact, horizontal, spreadsheet-like) */}
              {isLoadingCandidatas ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : isErrorCandidatas ? (
                <div className="flex flex-col items-center justify-center p-8 text-destructive text-sm">
                  Error al cargar las candidatas
                </div>
              ) : (
                <ScrollArea className="max-h-[520px] pr-1">
                  {/* Header row */}
                  <div className="flex items-center gap-3 px-3 py-2 bg-muted/40 rounded-t-lg border border-b-0 border-border text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    <div className="w-6 shrink-0" />
                    <div className="w-20 shrink-0">Nro Ord</div>
                    <div className="w-24 shrink-0">Expediente</div>
                    <div className="w-20 shrink-0">N° Liq.</div>
                    <div className="w-28 shrink-0">Comprobante</div>
                    <div className="flex-1 min-w-0">Especialidad</div>
                    <div className="w-20 shrink-0 text-right">Monto</div>
                    <div className="w-20 shrink-0">Periodo</div>
                    <div className="w-20 shrink-0">Mes</div>
                    <div className="w-24 shrink-0">Dictamen</div>
                    <div className="w-24 shrink-0">F. Pres.</div>
                    <div className="w-24 shrink-0">F. Rev.</div>
                  </div>
                  <div className="border border-t-0 border-border rounded-b-lg overflow-hidden">
                    {candidatas.map((c) => {
                      const selected = isSelected(c.id);
                      return (
                        <div
                          key={c.id}
                          className={`flex items-center gap-3 px-3 py-2 border-b border-border/50 last:border-b-0 transition-all duration-150 ${
                            selected ? "bg-primary/[0.04]" : "hover:bg-muted/30"
                          }`}
                        >
                          {/* Checkbox */}
                          <Checkbox
                            id={`card-${c.id}`}
                            checked={selected}
                            onCheckedChange={(v) => toggleCard(c, !!v)}
                            className="shrink-0"
                          />

                          {/* Nro Orden (inline input) */}
                          <Input
                            id={`nro-rh-${c.id}`}
                            type="text"
                            value={selectedCardFields[c.id]?.numero_rh ?? ""}
                            onChange={(e) =>
                              updateCardField(c.id, "numero_rh", e.target.value)
                            }
                            placeholder="N° RH"
                            disabled={!selected}
                            className="w-20 shrink-0 h-7 px-2 text-xs rounded border border-input bg-background disabled:opacity-40 disabled:cursor-not-allowed"
                          />

                          {/* Expediente (read-only) */}
                          <div
                            className="w-24 shrink-0 cursor-pointer"
                            onClick={() => toggleCard(c, !selected)}
                          >
                            <p className="font-mono font-bold text-xs text-foreground truncate">
                              {c.expediente ?? "—"}
                            </p>
                          </div>

                          {/* N° Liq. (liquidacion_especifica_numero — wider for visibility) */}
                          <div
                            className="w-20 shrink-0 cursor-pointer overflow-hidden"
                            onClick={() => toggleCard(c, !selected)}
                          >
                            <p className="font-mono text-xs font-bold text-foreground truncate">
                              {c.liquidacion_especifica_numero ?? "—"}
                            </p>
                          </div>

                          {/* Comprobante (comprobante_activo multi-line: serie-numero + tipo [+ fecha]) */}
                          <div
                            className="w-28 shrink-0 cursor-pointer overflow-hidden"
                            onClick={() => toggleCard(c, !selected)}
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

                          {/* Especialidad + tipo (read-only) */}
                          <div
                            className="flex-1 min-w-0 cursor-pointer"
                            onClick={() => toggleCard(c, !selected)}
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

                          {/* Monto (read-only) */}
                          <div
                            className="w-20 shrink-0 text-right cursor-pointer"
                            onClick={() => toggleCard(c, !selected)}
                          >
                            <p className="text-xs font-black text-primary">
                              {c.sub_total != null
                                ? `S/ ${c.sub_total.toFixed(2)}`
                                : "—"}
                            </p>
                          </div>

                          {/* Periodo / Año (inline input) */}
                          <Input
                            id={`periodo-${c.id}`}
                            type="number"
                            value={selectedCardFields[c.id]?.periodo ?? ""}
                            onChange={(e) =>
                              updateCardField(c.id, "periodo", e.target.value)
                            }
                            placeholder="Año"
                            disabled={!selected}
                            className="w-20 shrink-0 h-7 px-2 text-xs rounded border border-input bg-background disabled:opacity-40 disabled:cursor-not-allowed"
                          />

                          {/* Mes (inline input) */}
                          <Input
                            id={`mes-${c.id}`}
                            type="number"
                            min={1}
                            max={12}
                            value={selectedCardFields[c.id]?.mes ?? ""}
                            onChange={(e) =>
                              updateCardField(c.id, "mes", e.target.value)
                            }
                            placeholder="Mes"
                            disabled={!selected}
                            className="w-20 shrink-0 h-7 px-2 text-xs rounded border border-input bg-background disabled:opacity-40 disabled:cursor-not-allowed"
                          />

                          {/* Dictamen (inline select) */}
                          <Select
                            value={
                              selectedCardFields[c.id]?.dictamen_revision ||
                              SENTINEL_NO_DICTAMEN
                            }
                            onValueChange={(v) =>
                              updateCardField(
                                c.id,
                                "dictamen_revision",
                                v === SENTINEL_NO_DICTAMEN ? "" : v,
                              )
                            }
                            disabled={!selected}
                          >
                            <SelectTrigger
                              id={`dictamen-${c.id}`}
                              className="w-24 shrink-0 h-7 px-1.5 text-xs rounded border border-input bg-background disabled:opacity-40 disabled:cursor-not-allowed"
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

                          {/* Fecha Presentación (inline date) */}
                          <div className="w-24 shrink-0">
                            <InlineDatePicker
                              id={`fec-pres-${c.id}`}
                              value={
                                selectedCardFields[c.id]?.fecha_presentacion ?? ""
                              }
                              onChange={(v) =>
                                updateCardField(c.id, "fecha_presentacion", v)
                              }
                              disabled={!selected}
                            />
                          </div>

                          {/* Fecha Revisión (inline date) */}
                          <div className="w-24 shrink-0">
                            <InlineDatePicker
                              id={`fec-rev-${c.id}`}
                              value={
                                selectedCardFields[c.id]?.fecha_revision ?? ""
                              }
                              onChange={(v) =>
                                updateCardField(c.id, "fecha_revision", v)
                              }
                              disabled={!selected}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  {candidatas.length === 0 && (
                    <div className="py-12 text-center text-muted-foreground text-sm border border-t-0 border-border rounded-b-lg">
                      No hay liquidaciones candidatas para este delegado
                    </div>
                  )}
                </ScrollArea>
              )}
            </div>
          )}

          {/* ── Paso 3/4: Previsualización y confirmación ── */}
          {(step === 3 || step === 4) && cotizarResult && (
            <div className="space-y-4">
              {step === 4 && (
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
                      <p className="font-semibold">{cotizarResult.delegado.cip}</p>
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
              )}
              {/* Header info */}
              <div className="rounded-xl border border-border/60 bg-muted/10 p-4 space-y-2">
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
                          colSpan={6}
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
                      setStep((s) => (s === 4 ? 3 : s === 3 ? 2 : 1) as Step)
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
              <Button
                type="button"
                onClick={handleConfirmar}
                className="h-10 rounded-xl font-bold gap-1.5"
              >
                Confirmar
              </Button>
            )}

            {step === 4 && (
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

        <GenericModal.CloseX />
      </GenericModal.Content>
    </GenericModal>
  );
}
