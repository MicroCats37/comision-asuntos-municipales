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
import { FileSpreadsheet, Loader2, Receipt, Search, X } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { notify } from "@/errors";
import {
  useCotizarRHDelegado,
  useCrearRHDelegado,
} from "@/features/finanzas/hooks/useRHDelegadoMensual";
import { useCandidatasDelegado } from "@/features/finanzas/hooks/useCandidatasDelegado";
import type {
  CandidataDelegado,
  RHDelegadoCotizarIn,
  RHDelegadoCotizar,
} from "@/features/finanzas/schemas/rh-delegado-mensual.schema";

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
  dictamen_revision: string;
  fecha_presentacion: string;
  fecha_revision: string;
}

const DICTAMEN_OPTIONS = [
  { value: "", label: "Seleccionar…" },
  { value: "APROBADO", label: "Aprobado" },
  { value: "OBSERVADO", label: "Observado" },
  { value: "REVISADO", label: "Revisado" },
  { value: "PENDIENTE", label: "Pendiente" },
];

export function RhDelegadoMensualModal({
  open,
  onOpenChange,
  onSuccess,
}: RhDelegadoMensualModalProps) {
  const [step, setStep] = useState<Step>(1);
  const [cip, setCip] = useState("");
  const [periodo, setPeriodo] = useState("");
  const [cotizarResult, setCotizarResult] = useState<RHDelegadoCotizar | null>(null);

  /**
   * Map of CandidataDelegado.id → per-item fields.
   * Only entries for checked cards are present.
   */
  const [selectedCardFields, setSelectedCardFields] = useState<
    Record<string, CandidataCardFields>
  >({});

  const cotizarMutation = useCotizarRHDelegado();
  const crearMutation = useCrearRHDelegado();

  const {
    data: candidatasData,
    isLoading: isLoadingCandidatas,
    isError: isErrorCandidatas,
    refetch: refetchCandidatas,
  } = useCandidatasDelegado({
    cip,
    enabled: false,
  });

  const candidatas: CandidataDelegado[] = candidatasData?.candidatas ?? [];
  const delegado = candidatasData?.delegado;

  const resetForm = useCallback(() => {
    setStep(1);
    setCip("");
    setPeriodo("");
    setCotizarResult(null);
    setSelectedCardFields({});
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
    setSelectedCardFields({});
    setCotizarResult(null);
    try {
      await refetchCandidatas();
      setStep(2);
    } catch {
      notify.error("No se pudieron buscar las candidatas");
    }
  }, [cip, refetchCandidatas]);

  // ── Toggle card selection ──────────────────────────────────────────────
  const isSelected = useCallback(
    (id: string) => id in selectedCardFields,
    [selectedCardFields],
  );

  const toggleCard = useCallback(
    (c: CandidataDelegado, checked: boolean) => {
      setSelectedCardFields((prev) => {
        if (checked) {
          return {
            ...prev,
            [c.id]: {
              numero_rh: "",
              periodo: periodo || "",
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
    [periodo],
  );

  const updateCardField = useCallback(
    (id: string, field: keyof CandidataCardFields, value: string) => {
      setSelectedCardFields((prev) => ({
        ...prev,
        [id]: { ...prev[id], [field]: value },
      }));
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

    const items: RHDelegadoCotizarIn["items"] = candidatas
      .filter((c) => selectedIds.includes(c.id))
      .map((c) => {
        const fields = selectedCardFields[c.id];
        return {
          liquidacion_general_id: c.id,
          especialidad_revision_id: c.especialidad_candidata.id,
          numero_rh: fields.numero_rh || undefined,
          periodo: fields.periodo || periodo,
          dictamen_revision: fields.dictamen_revision || undefined,
          fecha_presentacion: fields.fecha_presentacion || undefined,
          fecha_revision: fields.fecha_revision || undefined,
        };
      });

    try {
      const result = await cotizarMutation.cotizar({
        cip,
        periodo,
        items,
      });
      setCotizarResult(result.data);
      setStep(3);
    } catch {
      // Error handled by mutation
    }
  }, [selectedCardFields, candidatas, cip, periodo, cotizarMutation]);

  // ── Paso 3 → 4: confirmar ───────────────────────────────────────────
  const handleConfirmar = useCallback(() => {
    setStep(4);
  }, []);

  // ── Paso 4: crear ───────────────────────────────────────────────────
  const handleCrear = useCallback(async () => {
    if (!cotizarResult) return;

    const selectedIds = Object.keys(selectedCardFields);
    const items: RHDelegadoCotizarIn["items"] = candidatas
      .filter((c) => selectedIds.includes(c.id))
      .map((c) => {
        const fields = selectedCardFields[c.id];
        return {
          liquidacion_general_id: c.id,
          especialidad_revision_id: c.especialidad_candidata.id,
          numero_rh: fields.numero_rh || undefined,
          periodo: fields.periodo || periodo,
          dictamen_revision: fields.dictamen_revision || undefined,
          fecha_presentacion: fields.fecha_presentacion || undefined,
          fecha_revision: fields.fecha_revision || undefined,
        };
      });

    try {
      await crearMutation.crear({ cip, periodo, items });
      notify.success("RH Mensual de delegado creado correctamente");
      handleClose();
      onSuccess?.();
    } catch {
      // Error handled by mutation
    }
  }, [cotizarResult, selectedCardFields, candidatas, cip, periodo, crearMutation, handleClose, onSuccess]);

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
                {step === 1 && "Ingresa el CIP del delegado para buscar candidatas"}
                {step === 2 && "Selecciona las liquidaciones candidatas e ingresa los datos por item"}
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
              <div className="space-y-2">
                <Label htmlFor="periodo">Periodo (YYYY-MM)</Label>
                <Input
                  id="periodo"
                  value={periodo}
                  onChange={(e) => setPeriodo(e.target.value)}
                  placeholder="Ej. 2025-06"
                  className="h-10 rounded-xl font-semibold"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") void handleBuscar();
                  }}
                />
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
                    <span className="font-bold">{delegado.nombre_completo}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground font-semibold">
                      CIP:
                    </span>
                    <span className="font-bold">{delegado.cip}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground font-semibold">
                      Periodo:
                    </span>
                    <span className="font-bold">{periodo}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground font-semibold">
                      Candidatas encontradas:
                    </span>
                    <span className="font-bold">{candidatas.length}</span>
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
                    <div className="flex-1 min-w-0">Especialidad</div>
                    <div className="w-20 shrink-0 text-right">Monto</div>
                    <div className="w-24 shrink-0">Periodo</div>
                    <div className="w-28 shrink-0">Dictamen</div>
                    <div className="w-28 shrink-0">F. Pres.</div>
                    <div className="w-28 shrink-0">F. Rev.</div>
                  </div>
                  <div className="border border-t-0 border-border rounded-b-lg overflow-hidden">
                    {candidatas.map((c) => {
                      const selected = isSelected(c.id);
                      return (
                        <div
                          key={c.id}
                          className={`flex items-center gap-3 px-3 py-2 border-b border-border/50 last:border-b-0 transition-all duration-150 ${
                            selected
                              ? "bg-primary/[0.04]"
                              : "hover:bg-muted/30"
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
                          <input
                            id={`nro-rh-${c.id}`}
                            type="text"
                            value={selectedCardFields[c.id]?.numero_rh ?? ""}
                            onChange={(e) =>
                              updateCardField(c.id, "numero_rh", e.target.value)
                            }
                            placeholder="N° RH"
                            disabled={!selected}
                            className="w-20 shrink-0 h-7 px-2 rounded border border-input bg-background text-xs disabled:opacity-40 disabled:cursor-not-allowed ring-offset-background focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
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
                              {c.municipalidad_nombre && ` · ${c.municipalidad_nombre}`}
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

                          {/* Periodo (inline input) */}
                          <input
                            id={`periodo-${c.id}`}
                            type="text"
                            value={selectedCardFields[c.id]?.periodo ?? ""}
                            onChange={(e) =>
                              updateCardField(c.id, "periodo", e.target.value)
                            }
                            placeholder={periodo || "YYYY-MM"}
                            disabled={!selected}
                            className="w-24 shrink-0 h-7 px-2 rounded border border-input bg-background text-xs disabled:opacity-40 disabled:cursor-not-allowed ring-offset-background focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                          />

                          {/* Dictamen (inline select) */}
                          <select
                            id={`dictamen-${c.id}`}
                            value={
                              selectedCardFields[c.id]?.dictamen_revision ?? ""
                            }
                            onChange={(e) =>
                              updateCardField(
                                c.id,
                                "dictamen_revision",
                                e.target.value,
                              )
                            }
                            disabled={!selected}
                            className="w-28 shrink-0 h-7 px-2 rounded border border-input bg-background text-xs disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                          >
                            {DICTAMEN_OPTIONS.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </select>

                          {/* Fecha Presentación (inline date) */}
                          <input
                            id={`fec-pres-${c.id}`}
                            type="date"
                            value={
                              selectedCardFields[c.id]?.fecha_presentacion ?? ""
                            }
                            onChange={(e) =>
                              updateCardField(
                                c.id,
                                "fecha_presentacion",
                                e.target.value,
                              )
                            }
                            disabled={!selected}
                            className="w-28 shrink-0 h-7 px-2 rounded border border-input bg-background text-xs disabled:opacity-40 disabled:cursor-not-allowed ring-offset-background focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                          />

                          {/* Fecha Revisión (inline date) */}
                          <input
                            id={`fec-rev-${c.id}`}
                            type="date"
                            value={
                              selectedCardFields[c.id]?.fecha_revision ?? ""
                            }
                            onChange={(e) =>
                              updateCardField(
                                c.id,
                                "fecha_revision",
                                e.target.value,
                              )
                            }
                            disabled={!selected}
                            className="w-28 shrink-0 h-7 px-2 rounded border border-input bg-background text-xs disabled:opacity-40 disabled:cursor-not-allowed ring-offset-background focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                          />
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

              <p className="text-xs text-muted-foreground text-right">
                {selectedCount} de {candidatas.length} seleccionada(s)
              </p>
            </div>
          )}

          {/* ── Paso 3: Previsualización — Tabla de Liquidación ── */}
          {step === 3 && cotizarResult && (
            <div className="space-y-4">
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
                  <span className="font-bold">{cotizarResult.delegado.cip}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-semibold">
                    Periodo:
                  </span>
                  <span className="font-bold">{cotizarResult.periodo}</span>
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
                          F. Rev.
                        </th>
                        <th className="border border-border px-1 py-1.5 text-left font-bold uppercase tracking-wide text-[10px]">
                          Expediente
                        </th>
                        <th className="border border-border px-1 py-1.5 text-center font-bold uppercase tracking-wide text-[10px]">
                          Nro Rev
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
                        <tr key={item.liquidacion_delegado_id ?? index} className="hover:bg-muted/30">
                          <td className="border border-border px-1 py-1.5 text-center">
                            {index + 1}
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
                          colSpan={4}
                          className="border border-border px-1 py-1.5 text-center uppercase tracking-wide"
                        >
                          Totales
                        </td>
                        <td className="border border-border px-1 py-1.5 text-right">
                          {cotizarResult.items.reduce(
                            (sum, i) => sum + (i.total_liquidacion ?? 0),
                            0,
                          ).toFixed(2)}
                        </td>
                        <td className="border border-border px-1 py-1.5 text-right">
                          {cotizarResult.items.reduce(
                            (sum, i) => sum + (i.sub_total_liquidacion ?? 0),
                            0,
                          ).toFixed(2)}
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
          </div>
        </GenericModal.Footer>

        <GenericModal.CloseX />
      </GenericModal.Content>
    </GenericModal>
  );
}
